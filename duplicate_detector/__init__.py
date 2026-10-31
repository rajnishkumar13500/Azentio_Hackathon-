"""
Duplicate Claims & Leakage Detection Engine Package.
"""

from .models import (
    Claim,
    LineItem,
    DuplicateDetectionResult,
    DuplicateFinding,
    DuplicateScenarioType,
    LeakageClassification,
    Severity,
    Recommendation,
    LeakageSummary
)
from .engine import DuplicateDetectionEngine

__all__ = [
    "Claim",
    "LineItem",
    "DuplicateDetectionResult",
    "DuplicateFinding",
    "DuplicateScenarioType",
    "LeakageClassification",
    "Severity",
    "Recommendation",
    "LeakageSummary",
    "DuplicateDetectionEngine"
]

