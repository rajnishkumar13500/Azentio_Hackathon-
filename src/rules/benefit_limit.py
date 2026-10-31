from typing import Optional
from src.rules.base import BasePolicyRule
from src.schemas import Claim, Policy, RuleResult, RuleStatus

class BenefitLimitRule(BasePolicyRule):
    rule_id = "POL-LIMIT-001"
    rule_name = "Overall Benefit Limit & Balance Sum Insured Verification"
    description = "Enforces the remaining balance sum insured ceiling across the policy year."

    def evaluate_benefit_limit(
        self, current_admissible: float, policy: Policy
    ) -> RuleResult:
        balance = policy.balance_sum_insured

        if current_admissible <= balance:
            return RuleResult(
                rule_id="POL-LIMIT-WITHIN-00",
                rule_name="Balance Sum Insured Verified",
                status=RuleStatus.PASSED,
                claimed_amount=current_admissible,
                admissible_amount=current_admissible,
                discrepancy_amount=0.0,
                reason=f"Admissible amount of ₹{current_admissible:,.2f} is within available balance of ₹{balance:,.2f}."
            )

        excess = round(current_admissible - balance, 2)
        return RuleResult(
            rule_id="POL-LIMIT-SUMINSURED-01",
            rule_name="Balance Sum Insured Ceiling Breached",
            status=RuleStatus.BREACHED,
            claimed_amount=current_admissible,
            admissible_amount=balance,
            discrepancy_amount=excess,
            formula_applied=f"min(Admissible [{current_admissible:,.2f}], Balance [{balance:,.2f}])",
            reason=(
                f"Admissible claim amount (₹{current_admissible:,.2f}) exceeds the remaining balance sum insured "
                f"(₹{balance:,.2f}). Settlement capped at balance ceiling; excess of ₹{excess:,.2f} disallowed."
            ),
            metadata={"balance_sum_insured": balance, "excess": excess}
        )

    def evaluate(self, claim: Claim, policy: Policy, context: Optional[dict] = None) -> list:
        return []
