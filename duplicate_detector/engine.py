"""
Main Duplicate Detection Orchestrator Engine.
Coordinates the execution of all detection tiers, applies the repeat guard,
and invokes the financial leakage calculator.
"""

from typing import List, Dict, Any, Optional
from .models import (
    Claim,
    LineItem,
    DuplicateDetectionResult,
    DuplicateFinding,
    DuplicateScenarioType
)
from .tiers.exact_matcher import ExactMatcher
from .tiers.intra_claim_matcher import IntraClaimMatcher
from .tiers.fuzzy_matcher import FuzzyMatcher
from .tiers.repeat_guard import RepeatServiceGuard
from .leakage_calculator import LeakageCalculator
from .policy_limits import PolicyLimitValidator


class DuplicateDetectionEngine:
    """Unified AI and rule-driven engine for insurance duplicate claims and leakage detection."""

    def __init__(self):
        self.exact_matcher = ExactMatcher()
        self.intra_matcher = IntraClaimMatcher()
        self.fuzzy_matcher = FuzzyMatcher()
        self.repeat_guard = RepeatServiceGuard()
        self.policy_validator = PolicyLimitValidator()
        self.leakage_calculator = LeakageCalculator()

    def process_claim(
        self,
        current_claim_data: Dict[str, Any],
        historical_claims_data: Optional[List[Dict[str, Any]]] = None,
        policy_data: Optional[Dict[str, Any]] = None
    ) -> DuplicateDetectionResult:
        """
        Main entry point accepting standard parsed JSON dicts.
        """
        current_claim = Claim.from_dict(current_claim_data)
        hist_claims = [
            Claim.from_dict(c) for c in (historical_claims_data or [])
        ]
        return self.evaluate(current_claim, hist_claims, policy_data)

    def evaluate(
        self,
        claim: Claim,
        historical_claims: List[Claim],
        policy_data: Optional[Dict[str, Any]] = None
    ) -> DuplicateDetectionResult:
        """
        Executes the detection pipeline against the given claim and historical dataset.
        """
        findings: List[DuplicateFinding] = []

        # Step 0: Identify legitimate repeat items to protect from false positive flags
        protected_line_ids = self.repeat_guard.validate_repeat_sequence(claim.line_items)

        # Tier 1A: Exact Claim Duplicate Check (Primary Check)
        exact_claim_finding = self.exact_matcher.check_exact_claim_duplicate(claim, historical_claims)
        if exact_claim_finding:
            findings.append(exact_claim_finding)

        # Step 0B: Check Policy Limits & Sub-limits (only if claim is not already an exact duplicate)
        if not exact_claim_finding and policy_data:
            policy_findings = self.policy_validator.check_policy_limits(claim, policy_data)
            findings.extend(policy_findings)

        # Tier 1B: Cross-Claim Exact Duplicate Lines (only if claim itself wasn't already an exact duplicate)
        if not exact_claim_finding:
            cross_line_findings = self.exact_matcher.check_cross_claim_line_duplicates(claim, historical_claims)
            findings.extend(cross_line_findings)

        # Tier 2: Intra-Claim Duplicate Lines
        intra_findings = self.intra_matcher.check_intra_claim_duplicates(claim)
        findings.extend(intra_findings)

        # Tier 3A: Near-Duplicate Claim Check (only if no exact match on claim level)
        if not exact_claim_finding:
            near_claim_finding = self.fuzzy_matcher.check_near_duplicate_claim(claim, historical_claims)
            if near_claim_finding:
                findings.append(near_claim_finding)

        # Tier 3B: Near-Duplicate Line Item Check (only for lines not already flagged by exact matchers)
        already_flagged_lines = {f.current_line_id for f in findings if f.current_line_id is not None}
        if not exact_claim_finding and not any(f.scenario_type == DuplicateScenarioType.NEAR_DUPLICATE_CLAIM for f in findings):
            near_line_findings = self.fuzzy_matcher.check_near_duplicate_lines(claim, historical_claims)
            # Exclude lines that already have an exact duplicate finding
            for nlf in near_line_findings:
                if nlf.current_line_id not in already_flagged_lines:
                    findings.append(nlf)

        # Step 4: Repeat Guard Filtering
        # Remove any line-item level findings where the line is protected as a legitimate repeat
        filtered_findings = [
            f for f in findings
            if f.current_line_id is None or f.current_line_id not in protected_line_ids
        ]

        # Step 5: Financial Leakage Calculation
        has_leakage = len(filtered_findings) > 0
        summary = self.leakage_calculator.summarize(filtered_findings, claim.total_claimed_amount)

        return DuplicateDetectionResult(
            claim_id=claim.claim_id,
            has_duplicate_leakage=has_leakage,
            summary=summary,
            findings=filtered_findings
        )
