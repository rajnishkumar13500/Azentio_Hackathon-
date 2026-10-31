"""
Level 2 Step 4 & Step 5: Recommended Settlement Corrections & Analyst Review and Escalation Engine.
Manages granular analyst decisions on findings, computes adjusted settlements,
and generates structured Analyst Review & Escalation Reports.
"""

from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from src.schemas import Claim, Policy, ValidationReport
from src.investigation.models import (
    AnalystDecisionType,
    EscalationTarget,
    FindingType,
    FindingDecision,
    FindingDecisionRequest,
    SettlementCorrection,
    AnalystInvestigationReport,
)


class AnalystReviewService:
    """
    Manages in-memory decisions on claim findings and computes
    audit trails, escalation states, and adjusted settlements.
    """

    def __init__(self):
        # Key: claim_id -> { finding_id: FindingDecision }
        self._store: Dict[str, Dict[str, FindingDecision]] = {}
        # Key: claim_id -> List[str]
        self._audit_logs: Dict[str, List[str]] = {}

    def get_decisions(self, claim_id: str) -> Dict[str, FindingDecision]:
        return self._store.get(claim_id, {})

    def record_decision(
        self,
        claim_id: str,
        req: FindingDecisionRequest,
        finding_metadata: Optional[Dict[str, Any]] = None,
    ) -> FindingDecision:
        """
        Records a decision on a finding adhering to business validation rules:
        - MARK_FALSE_POSITIVE requires a mandatory reason.
        - ESCALATE requires escalation target.
        """
        if req.decision == AnalystDecisionType.MARK_FALSE_POSITIVE:
            if not req.reason or not req.reason.strip():
                raise ValueError("Marking a finding as False Positive requires a mandatory justification reason.")

        metadata = finding_metadata or {}
        orig_leakage = float(metadata.get("discrepancy_amount", 0.0))

        # If False Positive, adjusted leakage becomes 0.0 (claimant is reimbursed)
        if req.decision == AnalystDecisionType.MARK_FALSE_POSITIVE:
            adj_leakage = 0.0
        else:
            adj_leakage = orig_leakage

        now_str = datetime.now(UTC).isoformat()
        decision_record = FindingDecision(
            finding_id=req.finding_id,
            finding_type=req.finding_type,
            decision=req.decision,
            reason=req.reason.strip() if req.reason else None,
            escalation_target=req.escalation_target,
            analyst_id=req.analyst_id or "Senior Claims Auditor",
            timestamp=now_str,
            original_leakage=orig_leakage,
            adjusted_leakage=adj_leakage,
        )

        if claim_id not in self._store:
            self._store[claim_id] = {}
        self._store[claim_id][req.finding_id] = decision_record

        # Append to audit log
        if claim_id not in self._audit_logs:
            self._audit_logs[claim_id] = []
        log_entry = (
            f"[{now_str}] {decision_record.analyst_id} set decision on '{req.finding_id}' "
            f"to {req.decision.value}"
        )
        if req.reason:
            log_entry += f" (Reason: {req.reason})"
        if req.escalation_target:
            log_entry += f" [Escalated to: {req.escalation_target.value}]"
        self._audit_logs[claim_id].append(log_entry)

        return decision_record

    def generate_corrections(
        self,
        report: ValidationReport,
    ) -> List[SettlementCorrection]:
        """
        Generates specific, non-generic settlement corrections showing:
        - original amount
        - corrected amount
        - calculation formula
        - policy rule / evidence citation
        """
        corrections: List[SettlementCorrection] = []

        # 1. Line-item corrections (exclusions, unit rate inflations, unsubstantiated lines)
        for item in report.line_items:
            if item.discrepancy_amount > 0 or item.status in ["EXCLUDED", "FLAGGED", "SUSPECTED"]:
                formula = f"Admissible = Claimed (₹{item.claimed_amount:,.2f}) - Discrepancy (₹{item.discrepancy_amount:,.2f}) = ₹{item.admissible_amount:,.2f}"
                rule_name = item.rules_applied[0].rule_name if item.rules_applied else "Section 2.1 Admissibility"
                corrections.append(
                    SettlementCorrection(
                        correction_id=f"CORR-{item.line_id}",
                        finding_id=item.line_id,
                        finding_type=FindingType.LINE_ITEM,
                        category=item.category,
                        description=f"Disallow non-admissible charges for '{item.description}'",
                        original_amount=item.claimed_amount,
                        corrected_amount=item.admissible_amount,
                        adjustment_amount=item.discrepancy_amount,
                        calculation_formula=formula,
                        policy_rule_or_evidence=rule_name,
                        status="RECOMMENDED",
                    )
                )

        # 2. Daily Room / ICU rent capping corrections
        s = report.summary
        if s.total_sublimit_deduction > 0:
            corrections.append(
                SettlementCorrection(
                    correction_id="CORR-SUBLIMIT-ROOM",
                    finding_id="rule_SEC_2_1_ROOM_CAP",
                    finding_type=FindingType.RULE_VIOLATION,
                    category="ROOM_RENT_CAPPING",
                    description="Cap Room / ICU charges at policy threshold",
                    original_amount=s.total_claimed,
                    corrected_amount=s.total_claimed - s.total_sublimit_deduction,
                    adjustment_amount=s.total_sublimit_deduction,
                    calculation_formula=f"Excess room rent = Claimed Room Rent - (Allowed Daily Rate × Length of Stay) = ₹{s.total_sublimit_deduction:,.2f}",
                    policy_rule_or_evidence="Policy Section 2.1: Daily Room Rent Cap",
                    status="RECOMMENDED",
                )
            )

        # 3. Proportionate deduction cascade correction
        if s.total_proportionate_deduction > 0:
            corrections.append(
                SettlementCorrection(
                    correction_id="CORR-PROP-DEDUCT",
                    finding_id="rule_SEC_2_2_PROPORTIONATE",
                    finding_type=FindingType.RULE_VIOLATION,
                    category="PROPORTIONATE_DEDUCTION",
                    description="Apply proportionate deduction cascade to associate medical fees",
                    original_amount=s.total_claimed,
                    corrected_amount=s.total_claimed - s.total_proportionate_deduction,
                    adjustment_amount=s.total_proportionate_deduction,
                    calculation_formula=f"Associate fees scaled by ratio of (Allowed Room Cap / Actual Room Charge). Deducted: ₹{s.total_proportionate_deduction:,.2f}",
                    policy_rule_or_evidence="Policy Section 2.2: Proportionate Deduction Clause",
                    status="RECOMMENDED",
                )
            )

        # 4. Procedure sub-limit cap
        if s.procedure_cap_deduction > 0:
            corrections.append(
                SettlementCorrection(
                    correction_id="CORR-PROCEDURE-CAP",
                    finding_id="rule_SEC_2_3_PROCEDURE_CAP",
                    finding_type=FindingType.RULE_VIOLATION,
                    category="PROCEDURE_CAP",
                    description="Cap procedure charges at specified policy limit",
                    original_amount=s.total_claimed,
                    corrected_amount=s.total_claimed - s.procedure_cap_deduction,
                    adjustment_amount=s.procedure_cap_deduction,
                    calculation_formula=f"Deducted procedure excess over schedule cap = ₹{s.procedure_cap_deduction:,.2f}",
                    policy_rule_or_evidence="Policy Section 2.3: Specific Procedure Sub-Limits",
                    status="RECOMMENDED",
                )
            )

        # 5. Policy deductible
        if s.deductible_applied > 0:
            corrections.append(
                SettlementCorrection(
                    correction_id="CORR-DEDUCTIBLE",
                    finding_id="rule_SEC_3_1_DEDUCTIBLE",
                    finding_type=FindingType.RULE_VIOLATION,
                    category="POLICY_DEDUCTIBLE",
                    description="Apply standard claim deductible before payout",
                    original_amount=s.total_claimed,
                    corrected_amount=s.total_claimed - s.deductible_applied,
                    adjustment_amount=s.deductible_applied,
                    calculation_formula=f"Net Settlement = Admissible Amount - Deductible (₹{s.deductible_applied:,.2f})",
                    policy_rule_or_evidence="Policy Section 3.1: Annual Deductible",
                    status="RECOMMENDED",
                )
            )

        # 6. Co-Payment
        if s.copay_applied > 0:
            corrections.append(
                SettlementCorrection(
                    correction_id="CORR-COPAY",
                    finding_id="rule_SEC_3_2_COPAY",
                    finding_type=FindingType.RULE_VIOLATION,
                    category="CO_PAYMENT",
                    description="Apply policy mandatory co-payment percentage",
                    original_amount=s.total_claimed,
                    corrected_amount=s.total_claimed - s.copay_applied,
                    adjustment_amount=s.copay_applied,
                    calculation_formula=f"Insured Co-Payment Contribution applied = ₹{s.copay_applied:,.2f}",
                    policy_rule_or_evidence="Policy Section 3.2: Co-Payment Clause",
                    status="RECOMMENDED",
                )
            )

        return corrections

    def build_analyst_report(
        self,
        claim: Claim,
        policy: Policy,
        report: ValidationReport,
    ) -> AnalystInvestigationReport:
        """
        Constructs a complete structured Analyst Investigation Report incorporating
        all recorded decisions, recalculating net financial adjustments,
        and determining overall escalation status.
        """
        claim_id = claim.claim_id
        decisions_map = self._store.get(claim_id, {})
        corrections = self.generate_corrections(report)

        # Prepare line item findings
        line_item_findings: List[Dict[str, Any]] = []
        for li in report.line_items:
            dec = decisions_map.get(li.line_id)
            status_desc = dec.decision.value if dec else "PENDING_REVIEW"
            line_item_findings.append({
                "line_id": li.line_id,
                "category": li.category,
                "description": li.description,
                "claimed_amount": li.claimed_amount,
                "admissible_amount": li.admissible_amount,
                "discrepancy_amount": li.discrepancy_amount,
                "rule_status": li.status,
                "analyst_decision": status_desc,
                "decision_details": dec.model_dump() if dec else None,
            })

        # Prepare rule findings
        rule_findings: List[Dict[str, Any]] = []
        all_rules = report.claim_level_rules + [r for li in report.line_items for r in li.rules_applied]
        seen_rules = set()
        for r in all_rules:
            if r.rule_id not in seen_rules and (r.status != "PASSED" or r.discrepancy_amount > 0):
                seen_rules.add(r.rule_id)
                dec = decisions_map.get(r.rule_id)
                rule_findings.append({
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "status": r.status,
                    "discrepancy_amount": r.discrepancy_amount,
                    "reason": r.reason,
                    "analyst_decision": dec.decision.value if dec else "PENDING_REVIEW",
                    "decision_details": dec.model_dump() if dec else None,
                })

        total_findings = len([f for f in line_item_findings if f["discrepancy_amount"] > 0]) + len(rule_findings)
        total_reviewed = len(decisions_map)
        pending_review = max(0, total_findings - total_reviewed)

        # Decisions breakdown counts
        breakdown: Dict[str, int] = {
            AnalystDecisionType.CONFIRM_DISCREPANCY.value: 0,
            AnalystDecisionType.MARK_FALSE_POSITIVE.value: 0,
            AnalystDecisionType.REQUEST_ADDITIONAL_EVIDENCE.value: 0,
            AnalystDecisionType.ESCALATE.value: 0,
            AnalystDecisionType.ACCEPT_CORRECTION.value: 0,
        }
        for d in decisions_map.values():
            if d.decision.value in breakdown:
                breakdown[d.decision.value] += 1

        # Check escalation status
        escalation_status = "NORMAL"
        for d in decisions_map.values():
            if d.decision == AnalystDecisionType.ESCALATE:
                if d.escalation_target == EscalationTarget.SPECIAL_INVESTIGATION_UNIT:
                    escalation_status = "SIU_ESCALATED"
                    break
                else:
                    escalation_status = "SENIOR_REVIEW_REQUESTED"

        # Calculate Net Adjusted Settlement
        # If an item was marked False Positive, claimant is credited back the discrepancy
        false_positive_reimbursements = 0.0
        for li in report.line_items:
            dec = decisions_map.get(li.line_id)
            if dec and dec.decision == AnalystDecisionType.MARK_FALSE_POSITIVE:
                false_positive_reimbursements += li.discrepancy_amount

        original_leakage = report.summary.calculated_leakage_prevented
        net_adjusted_leakage = max(0.0, original_leakage - false_positive_reimbursements)
        net_adjusted_settlement = report.summary.calculated_settlement + false_positive_reimbursements

        return AnalystInvestigationReport(
            claim_id=claim_id,
            case_title=report.case_title,
            total_findings=total_findings,
            total_reviewed=total_reviewed,
            pending_review=pending_review,
            decisions_breakdown=breakdown,
            escalation_status=escalation_status,
            original_claimed_amount=report.summary.total_claimed,
            original_admissible_amount=report.summary.calculated_settlement,
            original_leakage_prevented=original_leakage,
            net_adjusted_settlement=net_adjusted_settlement,
            net_adjusted_leakage=net_adjusted_leakage,
            line_item_findings=line_item_findings,
            rule_findings=rule_findings,
            recommended_corrections=corrections,
            decisions=list(decisions_map.values()),
            audit_notes=self._audit_logs.get(claim_id, []),
        )


# Global singleton instance
analyst_service = AnalystReviewService()

