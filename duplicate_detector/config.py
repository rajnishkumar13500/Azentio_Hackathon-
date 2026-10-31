"""
Configuration and Rule Constants for Claims Duplicate Detection Engine.
"""

from typing import Set

# Near-Duplicate Similarity Thresholds
INVOICE_STRING_SIMILARITY_THRESHOLD: float = 0.85
DESCRIPTION_STRING_SIMILARITY_THRESHOLD: float = 0.80
AMOUNT_TOLERANCE_PERCENTAGE: float = 0.05  # Within 5% variance
DATE_SLOP_WINDOW_DAYS: int = 3             # Incident or service date within ±3 days

# Categories and Codes that Represent Valid Repeat Services
LEGITIMATE_REPEAT_CATEGORIES: Set[str] = {
    "THERAPY_REHAB",
    "DIALYSIS",
    "CHEMOTHERAPY",
    "PHYSIOTHERAPY",
    "WOUND_DRESSING"
}

LEGITIMATE_REPEAT_SERVICE_CODES: Set[str] = {
    "SRV-THERAPY-PHYSIO",
    "SRV-DIALYSIS-HEMO",
    "SRV-CHEMO-CYCLE",
    "SRV-DRESS-DAILY"
}

# Rule Codes for Audit & Explainability
RULE_EXACT_CLAIM: str = "RULE-DUP-001"
RULE_INTRA_CLAIM_LINE: str = "RULE-DUP-002"
RULE_CROSS_CLAIM_LINE: str = "RULE-DUP-003"
RULE_NEAR_DUPLICATE_CLAIM: str = "RULE-DUP-004"
RULE_NEAR_DUPLICATE_LINE: str = "RULE-DUP-005"
RULE_POLICY_LIMIT: str = "RULE-POL-001"
RULE_REPEAT_GUARD: str = "RULE-DUP-GUARD"

