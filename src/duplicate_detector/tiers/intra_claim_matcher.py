"""
Tier 2: Intra-Claim Duplicate Line Item Matcher.
Identifies duplicate charges repeated within the same claim/invoice.
"""

from typing import List, Dict, Set
from ..models import (
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
from ..config import RULE_INTRA_CLAIM_LINE


class IntraClaimMatcher:
    """Detects repeated charges billed multiple times on the same invoice/claim."""

    def check_intra_claim_duplicates(self, claim: Claim) -> List[DuplicateFinding]:
        findings: List[DuplicateFinding] = []
        seen_items: Dict[str, LineItem] = {}
        flagged_line_ids: Set[str] = set()

        for line in claim.line_items:
            # Skip legitimate recurring treatments (handled by repeat guard)
            if line.is_recurring_treatment:
                continue

            # Composite key for unique service on a specific service date
            # Key: (service_code, service_date, unit_price)
            key = f"{line.service_code.strip().upper()}_{line.service_date}_{line.unit_price:.2f}"

            if key in seen_items:
                prior_line = seen_items[key]
                flagged_line_ids.add(line.line_id)

                findings.append(DuplicateFinding(
                    finding_id=f"FND-INTRA-{line.line_id}",
                    scenario_type=DuplicateScenarioType.INTRA_CLAIM_DUPLICATE_LINE,
                    severity=Severity.HIGH,
                    confidence_score=0.98,
                    leakage_classification=LeakageClassification.CALCULATED_EXACT,
                    leakage_amount=line.total_amount,
                    current_claim_id=claim.claim_id,
                    current_line_id=line.line_id,
                    current_line_description=line.service_description,
                    current_line_amount=line.total_amount,
                    evidence=MatchedEvidence(
                        source_type="SAME_CLAIM_LINE",
                        matched_claim_id=claim.claim_id,
                        matched_line_id=prior_line.line_id,
                        matched_invoice_number=claim.invoice_number,
                        matched_service_code=prior_line.service_code,
                        matched_service_description=prior_line.service_description,
                        matched_service_date=prior_line.service_date,
                        matched_amount=prior_line.total_amount,
                        similarity_score=1.0
                    ),
                    explanation=(
                        f"Duplicate charge on same invoice: '{line.service_description}' (code: {line.service_code}) "
                        f"was already billed on line '{prior_line.line_id}' for the same date ({line.service_date}) "
                        f"at ₹{line.total_amount:,.2f}."
                    ),
                    rule_code=RULE_INTRA_CLAIM_LINE,
                    suggested_action=Recommendation.DISALLOW_LINE_ITEM,
                    arithmetic_proof=ArithmeticProof(
                        formula="1.0 * line_total_amount",
                        input_values=f"₹{line.total_amount:,.2f}",
                        calculated_discrepancy=line.total_amount,
                        explanation=f"Duplicate intra-claim line item: 100% of repeated charge ₹{line.total_amount:,.2f} on same bill is disallowed."
                    )
                ))
            else:
                seen_items[key] = line

        return findings

