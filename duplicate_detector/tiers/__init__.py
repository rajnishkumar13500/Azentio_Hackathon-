"""
Tiers package for duplicate detection.
"""

from .exact_matcher import ExactMatcher
from .intra_claim_matcher import IntraClaimMatcher
from .fuzzy_matcher import FuzzyMatcher
from .repeat_guard import RepeatServiceGuard

__all__ = [
    "ExactMatcher",
    "IntraClaimMatcher",
    "FuzzyMatcher",
    "RepeatServiceGuard"
]

