"""
Azentio.ai Claims Investigation Workspace Module.
Includes Cross-Claim Correlation, Document Analysis, Settlement Recommender, and Audit Trail.
"""

from .models import (
    CorrelationRelationshipType,
    CorrelationMatch,
    CrossClaimCorrelationReport,
)
from .correlation import CrossClaimCorrelationEngine

__all__ = [
    "CorrelationRelationshipType",
    "CorrelationMatch",
    "CrossClaimCorrelationReport",
    "CrossClaimCorrelationEngine",
]
