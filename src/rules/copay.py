from typing import Optional
from src.rules.base import BasePolicyRule
from src.schemas import Claim, Policy, RuleResult, RuleStatus

class CoPaymentRule(BasePolicyRule):
    rule_id = "POL-COPAY-001"
    rule_name = "Mandatory Co-Payment Engine"
    description = "Calculates and deducts contractual co-payment percentage from admissible amount."

    def evaluate_copay(
        self, current_admissible: float, policy: Policy
    ) -> RuleResult:
        copay_pct = policy.co_payment_percentage

        if copay_pct <= 0 or current_admissible <= 0:
            return RuleResult(
                rule_id="POL-COPAY-NONE-00",
                rule_name="Co-Payment Assessment",
                status=RuleStatus.PASSED,
                claimed_amount=current_admissible,
                admissible_amount=current_admissible,
                discrepancy_amount=0.0,
                reason="Policy specifies 0% co-payment."
            )

        copay_deduction = round(current_admissible * (copay_pct / 100.0), 2)
        new_admissible = round(current_admissible - copay_deduction, 2)

        return RuleResult(
            rule_id="POL-COPAY-APPLIED-01",
            rule_name=f"Mandatory {copay_pct:.0f}% Co-Payment Applied",
            status=RuleStatus.APPLIED,
            claimed_amount=current_admissible,
            admissible_amount=new_admissible,
            discrepancy_amount=copay_deduction,
            formula_applied=f"Admissible ({current_admissible:,.2f}) * {copay_pct}% = {copay_deduction:,.2f}",
            reason=f"Policy co-payment of {copay_pct}% deducted from settlement base (₹{copay_deduction:,.2f}).",
            metadata={"copay_pct": copay_pct, "deduction": copay_deduction}
        )

    def evaluate(self, claim: Claim, policy: Policy, context: Optional[dict] = None) -> list:
        return []
