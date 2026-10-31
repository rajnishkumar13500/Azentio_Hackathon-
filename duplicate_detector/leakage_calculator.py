"""
Financial Leakage Calculator for Insurance Claims.
Calculates and distinguishes between deterministic calculated leakage and suspected leakage.
"""

from typing import List
from .models import (
    DuplicateFinding,
    LeakageSummary,
    LeakageClassification,
    Severity,
    Recommendation,
    DuplicateScenarioType
)


class LeakageCalculator:
    """Computes exact and suspected financial leakage amounts with deduplication logic."""

    def summarize(self, findings: List[DuplicateFinding], total_claimed_amount: float) -> LeakageSummary:
        if not findings:
            return LeakageSummary(
                total_leakage_calculated=0.0,
                total_leakage_suspected=0.0,
                overall_leakage_amount=0.0,
                highest_severity=Severity.NONE,
                findings_count=0,
                recommendation=Recommendation.ALLOW
            )

        # Check if entire claim is an exact duplicate
        exact_claim_findings = [
            f for f in findings if f.scenario_type == DuplicateScenarioType.EXACT_DUPLICATE_CLAIM
        ]

        if exact_claim_findings:
            # Entire claim is duplicate: leakage is capped at total_claimed_amount
            calc_leakage = total_claimed_amount
            susp_leakage = 0.0
            return LeakageSummary(
                total_leakage_calculated=calc_leakage,
                total_leakage_suspected=susp_leakage,
                overall_leakage_amount=calc_leakage,
                highest_severity=Severity.CRITICAL,
                findings_count=len(findings),
                recommendation=Recommendation.REJECT_CLAIM
            )

        # Check if entire claim is a near duplicate
        near_claim_findings = [
            f for f in findings if f.scenario_type == DuplicateScenarioType.NEAR_DUPLICATE_CLAIM
        ]

        if near_claim_findings:
            calc_leakage = 0.0
            susp_leakage = total_claimed_amount
            return LeakageSummary(
                total_leakage_calculated=calc_leakage,
                total_leakage_suspected=susp_leakage,
                overall_leakage_amount=susp_leakage,
                highest_severity=Severity.HIGH,
                findings_count=len(findings),
                recommendation=Recommendation.INVESTIGATE_FOR_REVIEW
            )

        # Line-item level leakages: deduplicate by line_id to avoid double counting
        accounted_lines = set()
        calc_leakage = 0.0
        susp_leakage = 0.0

        for f in findings:
            line_key = f.current_line_id or f.finding_id
            if line_key in accounted_lines:
                continue
            accounted_lines.add(line_key)

            if f.leakage_classification == LeakageClassification.CALCULATED_EXACT:
                calc_leakage += f.leakage_amount
            elif f.leakage_classification == LeakageClassification.SUSPECTED_ESTIMATED:
                susp_leakage += f.leakage_amount

        # Determine highest severity
        severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.NONE]
        highest_sev = Severity.NONE
        for s in severity_order:
            if any(f.severity == s for f in findings):
                highest_sev = s
                break

        # Determine recommendation
        if calc_leakage > 0:
            rec = Recommendation.DISALLOW_LINE_ITEM
        elif susp_leakage > 0:
            rec = Recommendation.INVESTIGATE_FOR_REVIEW
        else:
            rec = Recommendation.ALLOW

        return LeakageSummary(
            total_leakage_calculated=round(calc_leakage, 2),
            total_leakage_suspected=round(susp_leakage, 2),
            overall_leakage_amount=round(calc_leakage + susp_leakage, 2),
            highest_severity=highest_sev,
            findings_count=len(findings),
            recommendation=rec
        )

