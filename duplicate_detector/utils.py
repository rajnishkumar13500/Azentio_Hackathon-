"""
Utility functions for text normalization, string similarity, date math, and tolerance checks.
Built purely with standard library for fast, dependency-free execution.
"""

import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional


def normalize_text(text: Optional[str]) -> str:
    """Normalize text by converting to lowercase and stripping punctuation & excess whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def token_sort_ratio(s1: str, s2: str) -> float:
    """
    Computes token sort similarity ratio between two strings.
    Sorts tokens alphabetically to be order-agnostic:
    e.g. 'MRI Left Knee Joint' vs 'Left Knee Joint MRI' returns 1.0.
    """
    norm1 = normalize_text(s1)
    norm2 = normalize_text(s2)
    if not norm1 and not norm2:
        return 1.0
    if not norm1 or not norm2:
        return 0.0
    
    sorted1 = " ".join(sorted(norm1.split()))
    sorted2 = " ".join(sorted(norm2.split()))
    
    return SequenceMatcher(None, sorted1, sorted2).ratio()


def string_similarity(s1: str, s2: str) -> float:
    """Standard normalized character-sequence similarity."""
    norm1 = normalize_text(s1)
    norm2 = normalize_text(s2)
    if not norm1 and not norm2:
        return 1.0
    if not norm1 or not norm2:
        return 0.0
    return SequenceMatcher(None, norm1, norm2).ratio()


def days_between(date_str1: str, date_str2: str) -> Optional[int]:
    """Computes absolute number of calendar days between two YYYY-MM-DD date strings."""
    try:
        d1 = datetime.strptime(date_str1[:10], "%Y-%m-%d").date()
        d2 = datetime.strptime(date_str2[:10], "%Y-%m-%d").date()
        return abs((d1 - d2).days)
    except Exception:
        return None


def amount_difference_ratio(amount1: float, amount2: float) -> float:
    """
    Calculates percentage difference between two amounts relative to the larger amount.
    Returns 0.0 if both are identical.
    """
    if amount1 == 0 and amount2 == 0:
        return 0.0
    denom = max(abs(amount1), abs(amount2))
    return abs(amount1 - amount2) / denom

