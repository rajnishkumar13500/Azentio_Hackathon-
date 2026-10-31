from typing import Optional
from src.rules.base import BasePolicyRule
from src.schemas import Claim, Policy, RuleResult, RuleStatus

class DeductibleRule(BasePolicyRule):
    rule_id = "POL-DEDUCT-001"
    rule_name = "Policy Deductible Waterfall"
    description = "Subtracts per-claim or remaining annual deductible from the admissible claim base."

    def evaluate_deductible(
        self, current_admissible: float, policy: Policy
    ) -> RuleResult:
        deductible_target = max(policy.deductible_per_claim, policy.deductible_annual_remaining)

        if deductible_target <= 0 or current_admissible <= 0:
            return RuleResult(
                rule_id="POL-DEDUCT-NONE-00",
                rule_name="Deductible Assessment",
                status=RuleStatus.PASSED,
                claimed_amount=current_admissible,
                admissible_amount=current_admissible,
                discrepancy_amount=0.0,
                reason="No active deductible required under this policy."
            )

        applied = min(deductible_target, current_admissible)
        new_admissible = current_admissible - applied

        return RuleResult(
            rule_id="POL-DEDUCT-APPLIED-01",
            rule_name="Deductible Applied",
            status=RuleStatus.APPLIED,
            claimed_amount=current_admissible,
            admissible_amount=new_admissible,
            discrepancy_amount=applied,
            formula_applied=f"Admissible ({current_admissible:,.2f}) - Deductible ({applied:,.2f})",
            reason=f"Mandatory policy deductible of ₹{applied:,.2f} applied to admissible settlement.",
            metadata={"deductible_amount": applied}
        )

    def evaluate(self, claim: Claim, policy: Policy, context: Optional[dict] = None) -> list:
        return []
