from typing import Optional, List
from src.rules.base import BasePolicyRule
from src.schemas import Claim, Policy, LineItem, RuleResult, RuleStatus

class ProportionateDeductionRule(BasePolicyRule):
    rule_id = "POL-PROP-001"
    rule_name = "Proportionate Deduction on Room Rent Breach"
    description = (
        "When room rent exceeds the policy cap, associated medical charges "
        "(doctor visits, surgeon fees, nursing) are scaled proportionally."
    )

    ASSOCIATED_CATEGORIES = {"SURGERY", "CONSULTATION", "NURSING"}

    def evaluate_line_item(
        self,
        item: LineItem,
        room_proportion_ratio: Optional[float],
        policy: Policy
    ) -> Optional[RuleResult]:
        if not policy.proportionate_deduction:
            return None
        if not room_proportion_ratio or room_proportion_ratio >= 1.0:
            return None

        cat = item.category.upper()
        if cat in self.ASSOCIATED_CATEGORIES:
            original_amount = item.total_amount
            scaled_admissible = round(original_amount * room_proportion_ratio, 2)
            deduction_amount = round(original_amount - scaled_admissible, 2)

            return RuleResult(
                rule_id="POL-PROP-DEDUCT-01",
                rule_name=f"Proportionate Deduction ({cat.title()})",
                status=RuleStatus.BREACHED,
                claimed_amount=original_amount,
                admissible_amount=scaled_admissible,
                discrepancy_amount=deduction_amount,
                formula_applied=(
                    f"{original_amount} * (Allowed_Room / Actual_Room [{room_proportion_ratio:.4f}])"
                ),
                reason=(
                    f"Room rent limit was breached. Under policy proportionate deduction clause, "
                    f"{cat.lower()} charge is scaled by ratio {room_proportion_ratio:.2%}. "
                    f"Ineligible excess: ₹{deduction_amount:,.2f}."
                ),
                metadata={"ratio": room_proportion_ratio, "original": original_amount}
            )

        return None

    def evaluate(self, claim: Claim, policy: Policy, context: Optional[dict] = None) -> list:
        return []

