import logging
from typing import List, Dict, Any, Optional
from src.schemas import (
    Claim,
    Policy,
    RuleResult,
    RuleStatus,
    LineItemValidation,
    ClaimValidationSummary,
    ValidationReport,
)
from src.rules import (
    CoverageRule,
    ClinicalExclusionRule,
    SubLimitRule,
    ProportionateDeductionRule,
    DeductibleRule,
    CoPaymentRule,
    BenefitLimitRule,
    BenchmarkAnomalyRule,
)
from src.duplicate_detector.engine import DuplicateDetectionEngine
from src.duplicate_detector.models import (
    Claim as DetectorClaim,
    LineItem as DetectorLineItem,
    DuplicateScenarioType,
    Severity,
    LeakageClassification
)

logger = logging.getLogger(__name__)

class PolicyValidationEngine:
    """
    Core Insurance Settlement & Policy Validation Orchestrator.
    Executes rules in strict insurance financial waterfall sequence:
    0. Duplicate Claims & Repeated Line Items Detection (Step 3 & Step 4)
    1. Coverage & Eligibility Gatekeeper
    2. Line-Item Exclusions & Sub-limits
    3. Proportionate Deductions
    4. Disease / Procedure Capping
    5. Deductible Application
    6. Co-Payment Deduction
    7. Balance Sum Insured & Overall Benefit Capping
    8. Discrepancy & Leakage Reconciliation
    """

    def __init__(self):
        self.coverage_rule = CoverageRule()
        self.exclusion_rule = ClinicalExclusionRule()
        self.sublimit_rule = SubLimitRule()
        self.proportionate_rule = ProportionateDeductionRule()
        self.deductible_rule = DeductibleRule()
        self.copay_rule = CoPaymentRule()
        self.benefit_limit_rule = BenefitLimitRule()
        self.anomaly_rule = BenchmarkAnomalyRule()
        self.duplicate_engine = DuplicateDetectionEngine()

    def _convert_to_detector_claim(self, claim: Claim, policy: Policy) -> DetectorClaim:
        total_amt = sum(item.total_amount for item in claim.line_items)
        adm_date = (claim.incident_details.admission_date or "2026-01-01")[:10]
        hosp_name = claim.incident_details.hospital_name or claim.incident_details.hospital_id
        inv_num = getattr(claim.incident_details, "invoice_number", None) or f"INV-{claim.claim_id}"
        inv_date = getattr(claim.incident_details, "invoice_date", None) or adm_date

        detector_lines = []
        for i in claim.line_items:
            cat_upper = i.category.upper()
            is_recurring = cat_upper in [
                "THERAPY_REHAB", "DIALYSIS", "CHEMOTHERAPY", "PHYSIOTHERAPY", "WOUND_DRESSING"
            ]
            detector_lines.append(
                DetectorLineItem(
                    line_id=i.line_id,
                    claim_id=claim.claim_id,
                    invoice_number=inv_num,
                    service_date=i.service_date or adm_date,
                    service_code=i.item_code,
                    service_category=i.category,
                    service_description=i.description,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    total_amount=i.total_amount,
                    is_recurring_treatment=is_recurring
                )
            )

        return DetectorClaim(
            claim_id=claim.claim_id,
            policy_number=policy.policy_id,
            claimant_id=claim.claimant.claimant_id,
            claimant_name=claim.claimant.name,
            incident_date=adm_date,
            claim_submission_date=adm_date,
            claim_type="HEALTH",
            claim_status="SUBMITTED",
            provider_id=claim.incident_details.hospital_id,
            provider_name=hosp_name,
            invoice_number=inv_num,
            invoice_date=inv_date,
            total_claimed_amount=total_amt,
            line_items=detector_lines
        )

    def validate_claim(
        self,
        claim: Claim,
        policy: Policy,
        portfolio_history: Optional[List[Claim]] = None
    ) -> ValidationReport:
        total_claimed = sum(item.total_amount for item in claim.line_items)
        claim_level_rules: List[RuleResult] = []
        recommendations: List[str] = []
        duplicate_findings_out: List[Dict[str, Any]] = []

        # ==============================================================================
        # STAGE 0: Duplicate Detection Engine (Step 3 & Step 4)
        # ==============================================================================
        detector_curr = self._convert_to_detector_claim(claim, policy)
        
        # Build historical baseline from prior claims & portfolio claims
        historical_detector_claims: List[DetectorClaim] = []
        if portfolio_history:
            for past_c in portfolio_history:
                if past_c.claim_id != claim.claim_id:
                    historical_detector_claims.append(self._convert_to_detector_claim(past_c, policy))

        for prior_rec in claim.claim_history:
            prior_inv = getattr(prior_rec, "invoice_number", None) or f"INV-{prior_rec.previous_claim_id}"
            prior_date = getattr(prior_rec, "invoice_date", None) or prior_rec.admission_date[:10]
            historical_detector_claims.append(
                DetectorClaim(
                    claim_id=prior_rec.previous_claim_id,
                    policy_number=policy.policy_id,
                    claimant_id=claim.claimant.claimant_id,
                    claimant_name=claim.claimant.name,
                    incident_date=prior_rec.admission_date[:10],
                    claim_submission_date=prior_date,
                    claim_type="HEALTH",
                    claim_status="SETTLED",
                    provider_id=claim.incident_details.hospital_id,
                    provider_name=prior_rec.hospital_name or claim.incident_details.hospital_name or "Prior Hospital",
                    invoice_number=prior_inv,
                    invoice_date=prior_date,
                    total_claimed_amount=prior_rec.paid_amount,
                    line_items=[]
                )
            )

        policy_dict = policy.model_dump()
        dup_result = self.duplicate_engine.evaluate(
            detector_curr,
            historical_detector_claims,
            policy_data=policy_dict.get("sub_limits")
        )

        duplicate_findings_out = [f.to_dict() for f in dup_result.findings]

        # Check for Critical Exact Duplicate Claim
        exact_claim_finding = next(
            (f for f in dup_result.findings if f.scenario_type == DuplicateScenarioType.EXACT_DUPLICATE_CLAIM),
            None
        )

        if exact_claim_finding:
            reason_msg = f"EXACT DUPLICATE CLAIM: {exact_claim_finding.explanation}"
            recommendations.append(reason_msg)
            proof_dict = exact_claim_finding.arithmetic_proof.to_dict() if exact_claim_finding.arithmetic_proof else {}

            claim_level_rules.append(
                RuleResult(
                    rule_id=exact_claim_finding.rule_code,
                    rule_name="Exact Duplicate Claim Submission",
                    status=RuleStatus.FAILED,
                    claimed_amount=total_claimed,
                    admissible_amount=0.0,
                    discrepancy_amount=total_claimed,
                    suspected_leakage_amount=0.0,
                    formula_applied=proof_dict.get("formula", "1.0 * total_claimed"),
                    reason=exact_claim_finding.explanation,
                    metadata={"arithmetic_proof": proof_dict, "confidence": exact_claim_finding.confidence_score}
                )
            )

            summary = ClaimValidationSummary(
                total_claimed=total_claimed,
                total_excluded=0.0,
                total_sublimit_deduction=0.0,
                total_proportionate_deduction=0.0,
                procedure_cap_deduction=0.0,
                deductible_applied=0.0,
                copay_applied=0.0,
                balance_sum_insured_cap_deduction=0.0,
                total_calculated_admissible=0.0,
                proposed_settlement=claim.incident_details.proposed_settlement_amount,
                calculated_settlement=0.0,
                calculated_leakage_prevented=total_claimed,
                suspected_leakage_total=0.0,
                overall_status="REJECTED",
            )
            return ValidationReport(
                claim_id=claim.claim_id,
                case_title=claim.case_title,
                policy_id=policy.policy_id,
                summary=summary,
                line_items=[],
                claim_level_rules=claim_level_rules,
                recommendations=recommendations,
                duplicate_findings=duplicate_findings_out
            )

        # Check for Near-Duplicate Claim Warning
        near_claim_finding = next(
            (f for f in dup_result.findings if f.scenario_type == DuplicateScenarioType.NEAR_DUPLICATE_CLAIM),
            None
        )
        if near_claim_finding:
            claim_level_rules.append(
                RuleResult(
                    rule_id=near_claim_finding.rule_code,
                    rule_name="Near-Duplicate Claim Alert",
                    status=RuleStatus.ANOMALY_SUSPECTED,
                    claimed_amount=total_claimed,
                    admissible_amount=total_claimed,
                    discrepancy_amount=0.0,
                    suspected_leakage_amount=near_claim_finding.leakage_amount,
                    formula_applied="suspected_leakage = total_claimed_amount",
                    reason=near_claim_finding.explanation,
                    metadata={"confidence": near_claim_finding.confidence_score}
                )
            )
            recommendations.append(f"INVESTIGATE CLAIM: {near_claim_finding.explanation}")

        # Map Line-Level Duplicate Findings
        dup_line_findings_by_id = {
            f.current_line_id: f for f in dup_result.findings if f.current_line_id
        }

        # ==============================================================================
        # STAGE 1: Policy Coverage & Eligibility Gatekeeper
        # ==============================================================================
        cov_results = self.coverage_rule.evaluate(claim, policy)
        claim_level_rules.extend(cov_results)
        
        has_cov_failure = any(r.status == RuleStatus.FAILED for r in cov_results)
        if has_cov_failure:
            failed_rule = next(r for r in cov_results if r.status == RuleStatus.FAILED)
            recommendations.append(f"REJECT CLAIM: {failed_rule.reason}")
            
            summary = ClaimValidationSummary(
                total_claimed=total_claimed,
                total_excluded=0.0,
                total_sublimit_deduction=0.0,
                total_proportionate_deduction=0.0,
                procedure_cap_deduction=0.0,
                deductible_applied=0.0,
                copay_applied=0.0,
                balance_sum_insured_cap_deduction=0.0,
                total_calculated_admissible=0.0,
                proposed_settlement=claim.incident_details.proposed_settlement_amount,
                calculated_settlement=0.0,
                calculated_leakage_prevented=claim.incident_details.proposed_settlement_amount,
                suspected_leakage_total=0.0,
                overall_status="REJECTED",
            )
            return ValidationReport(
                claim_id=claim.claim_id,
                case_title=claim.case_title,
                policy_id=policy.policy_id,
                summary=summary,
                line_items=[],
                claim_level_rules=claim_level_rules,
                recommendations=recommendations,
                duplicate_findings=duplicate_findings_out
            )

        # ==============================================================================
        # STAGE 2: Room Rent Breach & Proportion Ratio Pre-Calculation
        # ==============================================================================
        room_proportion_ratio: Optional[float] = None
        for item in claim.line_items:
            if item.category.upper() == "ROOM_RENT":
                allowed = policy.sub_limits.daily_room_rent
                billed = item.unit_price
                if billed > allowed and allowed > 0:
                    room_proportion_ratio = round(allowed / billed, 4)
                    break

        # ==============================================================================
        # STAGE 3: Line-Item Level Evaluation
        # ==============================================================================
        line_item_validations: List[LineItemValidation] = []
        total_excluded = 0.0
        total_sublimit_deduction = 0.0
        total_proportionate_deduction = 0.0
        suspected_leakage_total = 0.0
        admissible_line_items_sum = 0.0

        for item in claim.line_items:
            item_rules: List[RuleResult] = []
            item_claimed = item.total_amount
            item_admissible = item_claimed
            item_status = RuleStatus.PASSED

            # Step 3.0: Duplicate Line Item Detection (Step 3 & 4)
            dup_item_finding = dup_line_findings_by_id.get(item.line_id)
            if dup_item_finding:
                proof_dict = dup_item_finding.arithmetic_proof.to_dict() if dup_item_finding.arithmetic_proof else {}
                is_calc = dup_item_finding.leakage_classification == LeakageClassification.CALCULATED_EXACT
                discrepancy_val = dup_item_finding.leakage_amount if is_calc else 0.0
                suspected_val = 0.0 if is_calc else dup_item_finding.leakage_amount

                dup_rule_result = RuleResult(
                    rule_id=dup_item_finding.rule_code,
                    rule_name="Duplicate Line Item Detected",
                    status=RuleStatus.EXCLUDED,
                    claimed_amount=item_claimed,
                    admissible_amount=0.0,
                    discrepancy_amount=discrepancy_val or item_claimed,
                    suspected_leakage_amount=suspected_val,
                    formula_applied=proof_dict.get("formula", "1.0 * claimed_amount"),
                    reason=dup_item_finding.explanation,
                    metadata={"arithmetic_proof": proof_dict, "confidence": dup_item_finding.confidence_score}
                )
                item_rules.append(dup_rule_result)
                item_admissible = 0.0
                item_status = RuleStatus.EXCLUDED
                total_excluded += item_claimed
                recommendations.append(f"EXCLUDE LINE '{item.description}': {dup_item_finding.explanation}")
            else:
                # Step 3A: Exclusions Check
                excl_result = self.exclusion_rule.evaluate_line_item(item, claim, policy)
                if excl_result:
                    item_rules.append(excl_result)
                    item_admissible = 0.0
                    item_status = RuleStatus.EXCLUDED
                    total_excluded += item_claimed
                else:
                    # Step 3B: Room Rent / ICU Sub-Limits Check
                    sublim_result = self.sublimit_rule.evaluate_line_item(item, claim, policy)
                    if sublim_result:
                        item_rules.append(sublim_result)
                        item_admissible = sublim_result.admissible_amount
                        item_status = RuleStatus.BREACHED
                        total_sublimit_deduction += sublim_result.discrepancy_amount

                    # Step 3C: Proportionate Deduction (Associated surgical/doc fees)
                    prop_result = self.proportionate_rule.evaluate_line_item(
                        item, room_proportion_ratio, policy
                    )
                    if prop_result:
                        item_rules.append(prop_result)
                        item_admissible = prop_result.admissible_amount
                        item_status = RuleStatus.BREACHED
                        total_proportionate_deduction += prop_result.discrepancy_amount

                    # Step 3D: Benchmark Anomaly (Statistical Pricing Outlier)
                    anomaly_result = self.anomaly_rule.evaluate_line_item(item, claim, policy)
                    if anomaly_result:
                        item_rules.append(anomaly_result)
                        suspected_leakage_total += anomaly_result.suspected_leakage_amount
                        recommendations.append(
                            f"INVESTIGATE LINE '{item.description}': Pricing exceeds regional benchmark. {anomaly_result.reason}"
                        )

            item_discrepancy = round(item_claimed - item_admissible, 2)
            admissible_line_items_sum += item_admissible

            line_item_validations.append(
                LineItemValidation(
                    line_id=item.line_id,
                    description=item.description,
                    category=item.category,
                    claimed_amount=item_claimed,
                    admissible_amount=item_admissible,
                    discrepancy_amount=item_discrepancy,
                    suspected_leakage_amount=sum(r.suspected_leakage_amount for r in item_rules),
                    status=item_status,
                    rules_applied=item_rules,
                )
            )

        # ==============================================================================
        # STAGE 4: Procedure / Disease Specific Cap
        # ==============================================================================
        procedure_cap_deduction = 0.0
        proc_cap_result = self.sublimit_rule.evaluate_procedure_cap(
            admissible_line_items_sum, claim, policy
        )
        current_waterfall_amount = admissible_line_items_sum

        if proc_cap_result:
            claim_level_rules.append(proc_cap_result)
            procedure_cap_deduction = proc_cap_result.discrepancy_amount
            current_waterfall_amount = proc_cap_result.admissible_amount

        # ==============================================================================
        # STAGE 5: Deductible Application
        # ==============================================================================
        deduct_result = self.deductible_rule.evaluate_deductible(
            current_waterfall_amount, policy
        )
        claim_level_rules.append(deduct_result)
        deductible_applied = deduct_result.discrepancy_amount
        current_waterfall_amount = deduct_result.admissible_amount

        # ==============================================================================
        # STAGE 6: Co-Payment Application
        # ==============================================================================
        copay_result = self.copay_rule.evaluate_copay(
            current_waterfall_amount, policy
        )
        claim_level_rules.append(copay_result)
        copay_applied = copay_result.discrepancy_amount
        current_waterfall_amount = copay_result.admissible_amount

        # ==============================================================================
        # STAGE 7: Balance Sum Insured & Overall Benefit Capping
        # ==============================================================================
        benefit_result = self.benefit_limit_rule.evaluate_benefit_limit(
            current_waterfall_amount, policy
        )
        claim_level_rules.append(benefit_result)
        balance_sum_insured_cap_deduction = benefit_result.discrepancy_amount
        final_calculated_settlement = benefit_result.admissible_amount

        # ==============================================================================
        # STAGE 8: Discrepancy & Financial Leakage Reconciliation
        # ==============================================================================
        proposed = claim.incident_details.proposed_settlement_amount
        calculated_leakage = round(max(0.0, proposed - final_calculated_settlement), 2)

        if calculated_leakage > 0.0:
            overall_status = "FLAGGED_LEAKAGE"
            recommendations.append(
                f"CORRECT SETTLEMENT: Proposed settlement (₹{proposed:,.2f}) exceeds policy calculated entitlement (₹{final_calculated_settlement:,.2f}) by ₹{calculated_leakage:,.2f}."
            )
        elif suspected_leakage_total > 0.0:
            overall_status = "FLAGGED_LEAKAGE"
            recommendations.append(
                f"AUDIT REQUIRED: Suspected provider pricing anomaly of ₹{suspected_leakage_total:,.2f} detected."
            )
        else:
            overall_status = "APPROVED"
            recommendations.append(
                f"APPROVE SETTLEMENT: Claim strictly satisfies all policy limits and co-payments. Admissible: ₹{final_calculated_settlement:,.2f}."
            )

        summary = ClaimValidationSummary(
            total_claimed=total_claimed,
            total_excluded=round(total_excluded, 2),
            total_sublimit_deduction=round(total_sublimit_deduction, 2),
            total_proportionate_deduction=round(total_proportionate_deduction, 2),
            procedure_cap_deduction=round(procedure_cap_deduction, 2),
            deductible_applied=round(deductible_applied, 2),
            copay_applied=round(copay_applied, 2),
            balance_sum_insured_cap_deduction=round(balance_sum_insured_cap_deduction, 2),
            total_calculated_admissible=round(final_calculated_settlement, 2),
            proposed_settlement=round(proposed, 2),
            calculated_settlement=round(final_calculated_settlement, 2),
            calculated_leakage_prevented=calculated_leakage,
            suspected_leakage_total=round(suspected_leakage_total, 2),
            overall_status=overall_status,
        )

        return ValidationReport(
            claim_id=claim.claim_id,
            case_title=claim.case_title,
            policy_id=policy.policy_id,
            summary=summary,
            line_items=line_item_validations,
            claim_level_rules=claim_level_rules,
            recommendations=recommendations,
            duplicate_findings=duplicate_findings_out
        )

validation_engine = PolicyValidationEngine()

