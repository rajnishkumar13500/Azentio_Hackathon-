from typing import Optional, Tuple
from src.rules.base import BasePolicyRule
from src.schemas import Claim, Policy, LineItem, RuleResult, RuleStatus
from src.catalog import medical_catalog

class SubLimitRule(BasePolicyRule):
    rule_id = "POL-SUBLIM-001"
    rule_name = "Sub-Limits & Category Capping Engine"
    description = "Enforces daily room rent limits, ICU caps, and procedure-specific financial ceilings."

    def evaluate_line_item(
        self, item: LineItem, claim: Claim, policy: Policy
    ) -> Optional[RuleResult]:
        cat = item.category.upper()

        # 1. Room Rent Daily Cap
        if cat == "ROOM_RENT":
            allowed_daily = policy.sub_limits.daily_room_rent
            billed_daily = item.unit_price
            days = item.quantity

            if billed_daily > allowed_daily:
                excess_per_day = billed_daily - allowed_daily
                total_excess = excess_per_day * days
                admissible = allowed_daily * days
                return RuleResult(
                    rule_id="POL-SUBLIM-ROOM-01",
                    rule_name="Daily Room Rent Limit Breach",
                    status=RuleStatus.BREACHED,
                    claimed_amount=item.total_amount,
                    admissible_amount=admissible,
                    discrepancy_amount=total_excess,
                    formula_applied=f"({billed_daily} - {allowed_daily}) * {days} days",
                    reason=(
                        f"Policy caps standard room rent at ₹{allowed_daily:,.2f}/day. "
                        f"Billed at ₹{billed_daily:,.2f}/day for {days:.0f} days. "
                        f"Calculated excess: ₹{total_excess:,.2f}."
                    ),
                    metadata={"billed_daily": billed_daily, "allowed_daily": allowed_daily, "days": days}
                )

        # 2. ICU Daily Cap
        if cat == "ICU_RENT":
            allowed_icu = policy.sub_limits.daily_icu_rent
            billed_daily = item.unit_price
            days = item.quantity

            if billed_daily > allowed_icu:
                excess_per_day = billed_daily - allowed_icu
                total_excess = excess_per_day * days
                admissible = allowed_icu * days
                return RuleResult(
                    rule_id="POL-SUBLIM-ICU-02",
                    rule_name="Daily ICU Rent Limit Breach",
                    status=RuleStatus.BREACHED,
                    claimed_amount=item.total_amount,
                    admissible_amount=admissible,
                    discrepancy_amount=total_excess,
                    formula_applied=f"({billed_daily} - {allowed_icu}) * {days} days",
                    reason=(
                        f"Policy caps ICU rent at ₹{allowed_icu:,.2f}/day. "
                        f"Billed at ₹{billed_daily:,.2f}/day for {days:.0f} days. "
                        f"Calculated excess: ₹{total_excess:,.2f}."
                    ),
                    metadata={"billed_daily": billed_daily, "allowed_daily": allowed_icu, "days": days}
                )

        return None

    def evaluate_procedure_cap(
        self, current_admissible: float, claim: Claim, policy: Policy
    ) -> Optional[RuleResult]:
        """
        Evaluates disease / procedure specific caps (e.g. Cataract, Appendicitis, Knee Replacement).
        """
        icd10 = claim.incident_details.icd10_code
        diag = claim.incident_details.diagnosis_description
        proc_key = medical_catalog.normalize_procedure(icd10, diag)

        if not proc_key or proc_key not in policy.sub_limits.procedure_caps:
            return None

        cap_amount = policy.sub_limits.procedure_caps[proc_key]
        if current_admissible > cap_amount:
            excess = current_admissible - cap_amount
            return RuleResult(
                rule_id="POL-SUBLIM-PROCEDURE-03",
                rule_name=f"Procedure Sub-Limit Cap ({proc_key.replace('_', ' ').title()})",
                status=RuleStatus.BREACHED,
                claimed_amount=current_admissible,
                admissible_amount=cap_amount,
                discrepancy_amount=excess,
                formula_applied=f"Admissible ({current_admissible:,.2f}) - Procedure_Cap ({cap_amount:,.2f})",
                reason=(
                    f"Policy imposes a specific cap of ₹{cap_amount:,.2f} for {proc_key.replace('_', ' ')}. "
                    f"Current admissible amount ₹{current_admissible:,.2f} exceeds cap by ₹{excess:,.2f}."
                ),
                metadata={"procedure_key": proc_key, "cap_amount": cap_amount}
            )

        return None

    def evaluate(self, claim: Claim, policy: Policy, context: Optional[dict] = None) -> list:
        return []

