"""
Tier 1: Fast Deterministic Exact Matcher.
Identifies identical claims and cross-claim duplicate line items in O(1) / linear scans.
"""

from typing import List, Optional
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
from ..config import RULE_EXACT_CLAIM, RULE_CROSS_CLAIM_LINE


class ExactMatcher:
    """Detects 100% deterministic duplicate claims and line items."""

    def check_exact_claim_duplicate(
        self,
        current_claim: Claim,
        historical_claims: List[Claim]
    ) -> Optional[DuplicateFinding]:
        """
        Detects if this incoming claim is an exact duplicate of an existing historical claim.
        Condition:
        1. Same Provider ID and exact same Invoice Number, OR
        2. Same Claimant ID, same Incident Date, and same Total Claimed Amount.
        """
        norm_curr_inv = current_claim.invoice_number.strip().upper()

        for hist in historical_claims:
            if hist.claim_id == current_claim.claim_id:
                continue

            norm_hist_inv = hist.invoice_number.strip().upper()

            # Criterion 1: Same provider and invoice number
            same_provider_invoice = (
                current_claim.provider_id == hist.provider_id and
                norm_curr_inv != "" and
                norm_curr_inv == norm_hist_inv
            )

            # Criterion 2: Same claimant, incident date, and exact amount
            same_incident_amount = (
                current_claim.claimant_id == hist.claimant_id and
                current_claim.incident_date == hist.incident_date and
                abs(current_claim.total_claimed_amount - hist.total_claimed_amount) < 0.01
            )

            if same_provider_invoice or same_incident_amount:
                reason = (
                    f"Identical invoice '{current_claim.invoice_number}' from provider '{current_claim.provider_name}' "
                    f"was already submitted/settled under Claim ID '{hist.claim_id}'."
                    if same_provider_invoice else
                    f"Claim matches prior Claim ID '{hist.claim_id}' for claimant '{current_claim.claimant_name}' "
                    f"on incident date {current_claim.incident_date} with exact amount ₹{current_claim.total_claimed_amount:,.2f}."
                )

                return DuplicateFinding(
                    finding_id=f"FND-EXACT-CLM-{current_claim.claim_id}",
                    scenario_type=DuplicateScenarioType.EXACT_DUPLICATE_CLAIM,
                    severity=Severity.CRITICAL,
                    confidence_score=1.0,
                    leakage_classification=LeakageClassification.CALCULATED_EXACT,
                    leakage_amount=current_claim.total_claimed_amount,
                    current_claim_id=current_claim.claim_id,
                    current_line_id=None,
                    current_line_description=f"Full Claim Submission ({len(current_claim.line_items)} line items)",
                    current_line_amount=current_claim.total_claimed_amount,
                    evidence=MatchedEvidence(
                        source_type="HISTORICAL_CLAIM",
                        matched_claim_id=hist.claim_id,
                        matched_invoice_number=hist.invoice_number,
                        matched_amount=hist.total_claimed_amount,
                        similarity_score=1.0
                    ),
                    explanation=reason,
                    rule_code=RULE_EXACT_CLAIM,
                    suggested_action=Recommendation.REJECT_CLAIM,
                    arithmetic_proof=ArithmeticProof(
                        formula="1.0 * total_claimed_amount",
                        input_values=f"₹{current_claim.total_claimed_amount:,.2f}",
                        calculated_discrepancy=current_claim.total_claimed_amount,
                        explanation=f"Exact duplicate claim: 100% of claimed amount ₹{current_claim.total_claimed_amount:,.2f} is disallowed."
                    )
                )

        return None

    def check_cross_claim_line_duplicates(
        self,
        current_claim: Claim,
        historical_claims: List[Claim]
    ) -> List[DuplicateFinding]:
        """
        Identifies individual line items in the current claim that were already billed
        and settled in a prior historical claim for the same claimant.
        """
        findings: List[DuplicateFinding] = []

        # Build lookup table of historical lines for this claimant
        # Key: (service_code, service_date, amount)
        for curr_line in current_claim.line_items:
            # Skip valid repeat items (will also be handled by repeat guard)
            if curr_line.is_recurring_treatment:
                continue

            for hist in historical_claims:
                if hist.claim_id == current_claim.claim_id:
                    continue
                # Same claimant
                if hist.claimant_id != current_claim.claimant_id:
                    continue

                for hist_line in hist.line_items:
                    # Check exact match on service code and service date
                    if (
                        curr_line.service_code == hist_line.service_code and
                        curr_line.service_date == hist_line.service_date and
                        abs(curr_line.total_amount - hist_line.total_amount) < 0.01
                    ):
                        findings.append(DuplicateFinding(
                            finding_id=f"FND-CROSS-LIN-{curr_line.line_id}",
                            scenario_type=DuplicateScenarioType.CROSS_CLAIM_DUPLICATE_LINE,
                            severity=Severity.HIGH,
                            confidence_score=1.0,
                            leakage_classification=LeakageClassification.CALCULATED_EXACT,
                            leakage_amount=curr_line.total_amount,
                            current_claim_id=current_claim.claim_id,
                            current_line_id=curr_line.line_id,
                            current_line_description=curr_line.service_description,
                            current_line_amount=curr_line.total_amount,
                            evidence=MatchedEvidence(
                                source_type="HISTORICAL_CLAIM_LINE",
                                matched_claim_id=hist.claim_id,
                                matched_line_id=hist_line.line_id,
                                matched_invoice_number=hist.invoice_number,
                                matched_service_code=hist_line.service_code,
                                matched_service_description=hist_line.service_description,
                                matched_service_date=hist_line.service_date,
                                matched_amount=hist_line.total_amount,
                                similarity_score=1.0
                            ),
                            explanation=(
                                f"Line item '{curr_line.service_description}' (₹{curr_line.total_amount:,.2f}) on {curr_line.service_date} "
                                f"was already claimed and settled under prior Claim '{hist.claim_id}' (Line {hist_line.line_id})."
                            ),
                            rule_code=RULE_CROSS_CLAIM_LINE,
                            suggested_action=Recommendation.DISALLOW_LINE_ITEM,
                            arithmetic_proof=ArithmeticProof(
                                formula="1.0 * line_total_amount",
                                input_values=f"₹{curr_line.total_amount:,.2f}",
                                calculated_discrepancy=curr_line.total_amount,
                                explanation=f"Cross-claim duplicate line item: 100% of charge ₹{curr_line.total_amount:,.2f} already paid under claim '{hist.claim_id}'."
                            )
                        ))
                        break  # Found match for this line, proceed to next curr_line

        return findings

