"""
Azentio.ai Claims Investigation Workspace Module.
Includes Cross-Claim Correlation, Document Analysis, Settlement Recommender, and Audit Trail.
"""

from .models import (
    CorrelationRelationshipType,
    CorrelationMatch,
    CrossClaimCorrelationReport,
    VarianceType,
    DocumentSourceCitation,
    DocumentFieldComparison,
    DocumentLineItemComparison,
    DocumentReconciliationReport,
)
from .correlation import CrossClaimCorrelationEngine
from .document_comparator import DocumentInvoiceAnalyzer, document_analyzer

__all__ = [
    "CorrelationRelationshipType",
    "CorrelationMatch",
    "CrossClaimCorrelationReport",
    "CrossClaimCorrelationEngine",
    "VarianceType",
    "DocumentSourceCitation",
    "DocumentFieldComparison",
    "DocumentLineItemComparison",
    "DocumentReconciliationReport",
    "DocumentInvoiceAnalyzer",
    "document_analyzer",
]

