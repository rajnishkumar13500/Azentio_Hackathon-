"""
Tier 3: Fuzzy / Near-Duplicate Matcher.
Identifies claims and line items with minor typos, slight date shifts, or minor amount variances.
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
from ..utils import (
    token_sort_ratio,
    string_similarity,
    days_between,
    amount_difference_ratio
)
from ..embeddings import get_semantic_embedder
from ..config import (
    INVOICE_STRING_SIMILARITY_THRESHOLD,
    DESCRIPTION_STRING_SIMILARITY_THRESHOLD,
    AMOUNT_TOLERANCE_PERCENTAGE,
    DATE_SLOP_WINDOW_DAYS,
    RULE_NEAR_DUPLICATE_CLAIM,
    RULE_NEAR_DUPLICATE_LINE
)


class FuzzyMatcher:
    """Detects near-duplicates requiring human review due to typos, date slop, or slight price shifts."""

    def __init__(self, embedder=None):
        self.embedder = embedder or get_semantic_embedder()

    def check_near_duplicate_claim(
        self,
        current_claim: Claim,
        historical_claims: List[Claim]
    ) -> Optional[DuplicateFinding]:
        """
        Flags if incoming claim strongly resembles an existing historical claim
        despite minor differences in invoice number, date, or amount.
        """
        for hist in historical_claims:
            if hist.claim_id == current_claim.claim_id:
                continue

            # Must belong to same claimant or same provider
            same_claimant = (current_claim.claimant_id == hist.claimant_id)
            same_provider = (current_claim.provider_id == hist.provider_id)

            if not (same_claimant or same_provider):
                continue

            # 1. Invoice Number Similarity
            inv_sim = string_similarity(current_claim.invoice_number, hist.invoice_number)

            # 2. Date proximity (incident date or invoice date)
            date_diff = days_between(current_claim.incident_date, hist.incident_date)
            date_ok = (date_diff is not None and date_diff <= DATE_SLOP_WINDOW_DAYS)

            # 3. Amount tolerance
            amt_diff_ratio = amount_difference_ratio(
                current_claim.total_claimed_amount,
                hist.total_claimed_amount
            )
            amt_ok = (amt_diff_ratio <= AMOUNT_TOLERANCE_PERCENTAGE)

            # Condition A: Invoice number has typo (e.g. >= 0.80) and date within window and amount similar
            is_near_dup = False
            confidence = 0.0
            reasons = []

            if inv_sim >= INVOICE_STRING_SIMILARITY_THRESHOLD and date_ok and amt_ok:
                is_near_dup = True
                confidence = round(0.70 + (inv_sim * 0.20) + (1.0 - amt_diff_ratio) * 0.10, 2)
                reasons.append(f"Invoice number similarity: {inv_sim*100:.1f}% ('{current_claim.invoice_number}' vs '{hist.invoice_number}')")
                reasons.append(f"Incident dates differ by only {date_diff} day(s)")
                reasons.append(f"Amount difference is only {amt_diff_ratio*100:.2f}% (₹{current_claim.total_claimed_amount:,.2f} vs ₹{hist.total_claimed_amount:,.2f})")

            elif same_claimant and same_provider and date_ok and amt_ok:
                # Even if invoice number is different, same claimant, same hospital, same date window and same amount
                is_near_dup = True
                confidence = 0.78
                reasons.append(f"Same claimant and hospital with incident date within {date_diff} day(s)")
                reasons.append(f"Amount matches within {amt_diff_ratio*100:.2f}%")

            if is_near_dup:
                return DuplicateFinding(
                    finding_id=f"FND-NEAR-CLM-{current_claim.claim_id}",
                    scenario_type=DuplicateScenarioType.NEAR_DUPLICATE_CLAIM,
                    severity=Severity.HIGH,
                    confidence_score=min(confidence, 0.95),
                    leakage_classification=LeakageClassification.SUSPECTED_ESTIMATED,
                    leakage_amount=current_claim.total_claimed_amount,
                    current_claim_id=current_claim.claim_id,
                    current_line_id=None,
                    current_line_description=f"Near-Duplicate Claim Submission ({len(current_claim.line_items)} line items)",
                    current_line_amount=current_claim.total_claimed_amount,
                    evidence=MatchedEvidence(
                        source_type="HISTORICAL_CLAIM",
                        matched_claim_id=hist.claim_id,
                        matched_invoice_number=hist.invoice_number,
                        matched_amount=hist.total_claimed_amount,
                        similarity_score=inv_sim
                    ),
                    explanation="; ".join(reasons) + f". Prior settled claim: '{hist.claim_id}'.",
                    rule_code=RULE_NEAR_DUPLICATE_CLAIM,
                    suggested_action=Recommendation.INVESTIGATE_FOR_REVIEW,
                    arithmetic_proof=ArithmeticProof(
                        formula="estimated_leakage_risk = total_claimed_amount",
                        input_values=f"₹{current_claim.total_claimed_amount:,.2f}",
                        calculated_discrepancy=current_claim.total_claimed_amount,
                        explanation=f"Near-duplicate claim risk: Potential exposure of ₹{current_claim.total_claimed_amount:,.2f} pending adjuster investigation."
                    )
                )

        return None

    def check_near_duplicate_lines(
        self,
        current_claim: Claim,
        historical_claims: List[Claim]
    ) -> List[DuplicateFinding]:
        """
        Flags line items that have minor fuzzy description differences or date shifts
        compared against historical settled items.
        """
        findings: List[DuplicateFinding] = []

        for curr_line in current_claim.line_items:
            if curr_line.is_recurring_treatment:
                continue

            for hist in historical_claims:
                if hist.claim_id == current_claim.claim_id:
                    continue
                if hist.claimant_id != current_claim.claimant_id:
                    continue

                for hist_line in hist.line_items:
                    if hist_line.is_recurring_treatment:
                        continue

                    # Hybrid semantic embedding and token sort similarity
                    text_sim = token_sort_ratio(
                        curr_line.service_description,
                        hist_line.service_description
                    )
                    embed_sim = self.embedder.cosine_similarity(
                        curr_line.service_description,
                        hist_line.service_description
                    )
                    semantic_sim = max(text_sim, embed_sim, round(0.60 * embed_sim + 0.40 * text_sim, 3))

                    date_diff = days_between(curr_line.service_date, hist_line.service_date)
                    date_ok = (date_diff is not None and date_diff <= DATE_SLOP_WINDOW_DAYS)
                    amt_diff_ratio = amount_difference_ratio(curr_line.total_amount, hist_line.total_amount)
                    amt_ok = (amt_diff_ratio <= AMOUNT_TOLERANCE_PERCENTAGE)

                    if semantic_sim >= DESCRIPTION_STRING_SIMILARITY_THRESHOLD and date_ok and amt_ok:
                        confidence = round(0.65 + (semantic_sim * 0.20) + (1.0 - amt_diff_ratio) * 0.15, 2)
                        findings.append(DuplicateFinding(
                            finding_id=f"FND-NEAR-LIN-{curr_line.line_id}",
                            scenario_type=DuplicateScenarioType.NEAR_DUPLICATE_LINE,
                            severity=Severity.MEDIUM,
                            confidence_score=min(confidence, 0.95),
                            leakage_classification=LeakageClassification.SUSPECTED_ESTIMATED,
                            leakage_amount=curr_line.total_amount,
                            current_claim_id=current_claim.claim_id,
                            current_line_id=curr_line.line_id,
                            current_line_description=curr_line.service_description,
                            current_line_amount=curr_line.total_amount,
                            evidence=MatchedEvidence(
                                source_type="HISTORICAL_CLAIM_LINE",
                                matched_claim_id=hist.claim_id,
                                matched_line_id=hist_line.line_id,
                                matched_service_code=hist_line.service_code,
                                matched_service_description=hist_line.service_description,
                                matched_service_date=hist_line.service_date,
                                matched_amount=hist_line.total_amount,
                                similarity_score=semantic_sim
                            ),
                            explanation=(
                                f"Semantic & text similarity match ({semantic_sim*100:.1f}% [Cosine: {embed_sim*100:.1f}%, Token: {text_sim*100:.1f}%]): "
                                f"'{curr_line.service_description}' matches historical item '{hist_line.service_description}' from claim '{hist.claim_id}'. "
                                f"Date delta: {date_diff} day(s), Amount delta: {amt_diff_ratio*100:.1f}%."
                            ),
                            rule_code=RULE_NEAR_DUPLICATE_LINE,
                            suggested_action=Recommendation.INVESTIGATE_FOR_REVIEW
                        ))
                        break

        return findings

