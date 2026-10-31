"""
Policy Limit Validator and Discrepancy Calculator.
Evaluates room charges, ICU limits, and benefit caps against policy terms,
generating exact mathematical proofs of financial leakage.
"""

from typing import List, Dict, Any, Optional
from .models import (
    Claim,
    LineItem,
    DuplicateFinding,
    DuplicateScenarioType,
    MatchedEvidence,
    Severity,
    LeakageClassification,
    Recommendation,
    ArithmeticProof
)
from .config import RULE_POLICY_LIMIT


class PolicyLimitValidator:
    """Validates claims against policy conditions and sub-limits."""

    def check_policy_limits(
        self,
        claim: Claim,
        policy_data: Optional[Dict[str, Any]] = None
    ) -> List[DuplicateFinding]:
        """
        Validates line items against applicable policy terms (e.g. daily room rent limits, ICU caps).
        """
        if not policy_data:
            return []

        findings: List[DuplicateFinding] = []
        room_limit = float(policy_data.get("daily_room_rent_limit", 0))
        icu_limit = float(policy_data.get("icu_limit", 0))

        for line in claim.line_items:
            category = line.service_category.upper()
            desc_lower = line.service_description.lower()

            # 1. Room Rent Limit Check
            if (category == "ROOM_CHARGES" or "room" in desc_lower) and room_limit > 0 and "icu" not in desc_lower:
                if line.unit_price > room_limit:
                    rate_excess = line.unit_price - room_limit
                    discrepancy = round(rate_excess * line.quantity, 2)

                    proof = ArithmeticProof(
                        formula="(billed_rate - policy_limit) * duration_days",
                        input_values=f"(₹{line.unit_price:,.2f} - ₹{room_limit:,.2f}) * {line.quantity:.0f} days",
                        calculated_discrepancy=discrepancy,
                        explanation=(
                            f"Room charge rate of ₹{line.unit_price:,.2f}/day exceeds the policy daily limit of "
                            f"₹{room_limit:,.2f}/day by ₹{rate_excess:,.2f}/day for {line.quantity:.0f} day(s), "
                            f"yielding a calculated excess of ₹{discrepancy:,.2f}."
                        )
                    )

                    findings.append(DuplicateFinding(
                        finding_id=f"FND-POL-ROOM-{line.line_id}",
                        scenario_type=DuplicateScenarioType.POLICY_LIMIT_BREACH,
                        severity=Severity.HIGH,
                        confidence_score=1.0,
                        leakage_classification=LeakageClassification.CALCULATED_EXACT,
                        leakage_amount=discrepancy,
                        current_claim_id=claim.claim_id,
                        current_line_id=line.line_id,
                        current_line_description=line.service_description,
                        current_line_amount=line.total_amount,
                        evidence=MatchedEvidence(
                            source_type="POLICY_TERM",
                            matched_service_code=line.service_code,
                            matched_service_description=f"Policy Daily Room Limit: ₹{room_limit:,.2f}",
                            matched_amount=room_limit,
                            similarity_score=1.0
                        ),
                        explanation=proof.explanation,
                        rule_code=RULE_POLICY_LIMIT,
                        suggested_action=Recommendation.DISALLOW_LINE_ITEM,
                        arithmetic_proof=proof
                    ))

            # 2. ICU Limit Check
            elif ("icu" in desc_lower or "intensive care" in desc_lower) and icu_limit > 0:
                if line.unit_price > icu_limit:
                    rate_excess = line.unit_price - icu_limit
                    discrepancy = round(rate_excess * line.quantity, 2)

                    proof = ArithmeticProof(
                        formula="(billed_icu_rate - policy_icu_limit) * duration_days",
                        input_values=f"(₹{line.unit_price:,.2f} - ₹{icu_limit:,.2f}) * {line.quantity:.0f} days",
                        calculated_discrepancy=discrepancy,
                        explanation=(
                            f"ICU charge rate of ₹{line.unit_price:,.2f}/day exceeds the policy ICU limit of "
                            f"₹{icu_limit:,.2f}/day by ₹{rate_excess:,.2f}/day for {line.quantity:.0f} day(s), "
                            f"yielding a calculated excess of ₹{discrepancy:,.2f}."
                        )
                    )

                    findings.append(DuplicateFinding(
                        finding_id=f"FND-POL-ICU-{line.line_id}",
                        scenario_type=DuplicateScenarioType.POLICY_LIMIT_BREACH,
                        severity=Severity.HIGH,
                        confidence_score=1.0,
                        leakage_classification=LeakageClassification.CALCULATED_EXACT,
                        leakage_amount=discrepancy,
                        current_claim_id=claim.claim_id,
                        current_line_id=line.line_id,
                        current_line_description=line.service_description,
                        current_line_amount=line.total_amount,
                        evidence=MatchedEvidence(
                            source_type="POLICY_TERM",
                            matched_service_code=line.service_code,
                            matched_service_description=f"Policy Daily ICU Limit: ₹{icu_limit:,.2f}",
                            matched_amount=icu_limit,
                            similarity_score=1.0
                        ),
                        explanation=proof.explanation,
                        rule_code=RULE_POLICY_LIMIT,
                        suggested_action=Recommendation.DISALLOW_LINE_ITEM,
                        arithmetic_proof=proof
                    ))

        return findings

