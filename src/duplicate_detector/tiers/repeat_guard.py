"""
Tier 4: Legitimate Repeat Service Guard.
Ensures valid recurring treatments (physiotherapy, dialysis, chemo cycles, routine dressings)
are not erroneously flagged as duplicate leakage.
"""

import re
from typing import List, Set
from ..models import LineItem
from ..config import (
    LEGITIMATE_REPEAT_CATEGORIES,
    LEGITIMATE_REPEAT_SERVICE_CODES
)


class RepeatServiceGuard:
    """Safeguards legitimate recurring medical procedures from false-positive duplicate flags."""

    # Regex patterns indicating distinct treatment sessions
    SESSION_PATTERNS = [
        re.compile(r"session\s*#?\s*(\d+)", re.IGNORECASE),
        re.compile(r"cycle\s*#?\s*(\d+)", re.IGNORECASE),
        re.compile(r"day\s*#?\s*(\d+)", re.IGNORECASE),
        re.compile(r"visit\s*#?\s*(\d+)", re.IGNORECASE),
        re.compile(r"part\s*#?\s*(\d+)", re.IGNORECASE)
    ]

    def is_legitimate_repeat_candidate(self, line: LineItem) -> bool:
        """Determines if a line item belongs to a legitimate recurring therapy category."""
        if line.is_recurring_treatment:
            return True

        if line.service_category.upper() in LEGITIMATE_REPEAT_CATEGORIES:
            return True

        if line.service_code.upper() in LEGITIMATE_REPEAT_SERVICE_CODES:
            return True

        # Check description keywords
        desc_lower = line.service_description.lower()
        if any(term in desc_lower for term in ["physiotherapy", "dialysis", "chemotherapy", "rehab", "dressing"]):
            return True

        return False

    def validate_repeat_sequence(self, items: List[LineItem]) -> Set[str]:
        """
        Validates a group of repeat items. If they have distinct service dates
        or explicit session indicators, returns a set of valid line_ids that must NOT be flagged.
        """
        valid_line_ids: Set[str] = set()

        # Group by service code or normalized category
        grouped: dict = {}
        for item in items:
            if self.is_legitimate_repeat_candidate(item):
                grouped.setdefault(item.service_code, []).append(item)

        for srv_code, group in grouped.items():
            if len(group) <= 1:
                # Single item, no repeat ambiguity
                for it in group:
                    valid_line_ids.add(it.line_id)
                continue

            # Check if all items in this group have distinct dates OR distinct session numbers
            dates = [it.service_date for it in group]
            distinct_dates = (len(dates) == len(set(dates)))

            sessions = [it.session_number for it in group if it.session_number is not None]
            distinct_sessions = (len(sessions) == len(group) and len(set(sessions)) == len(sessions))

            # Also check text-based session tags (e.g. 'Session 1', 'Session 2')
            text_session_indices = []
            for it in group:
                found = None
                for pat in self.SESSION_PATTERNS:
                    match = pat.search(it.service_description)
                    if match:
                        found = match.group(1)
                        break
                text_session_indices.append(found)

            distinct_text_sessions = (
                all(idx is not None for idx in text_session_indices) and
                len(set(text_session_indices)) == len(group)
            )

            # If either dates are distinct, or session numbers/text are distinct, it's legitimate!
            if distinct_dates or distinct_sessions or distinct_text_sessions:
                for it in group:
                    valid_line_ids.add(it.line_id)

        return valid_line_ids

