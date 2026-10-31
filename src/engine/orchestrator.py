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

logger = logging.getLogger(__name__)

class PolicyValidationEngine:
    """
    Core Insurance Settlement & Policy Validation Orchestrator.
    Executes rules in strict insurance financial waterfall sequence:
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

    def validate_claim(self, claim: Claim, policy: Policy) -> ValidationReport:
        total_claimed = sum(item.total_amount for item in claim.line_items)
        claim_level_rules: List[RuleResult] = []
        recommendations: List[str] = []

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
        )

validation_engine = PolicyValidationEngine()

