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
    AnalystDecisionType,
    EscalationTarget,
    FindingType,
    SettlementCorrection,
    FindingDecision,
    FindingDecisionRequest,
    AnalystInvestigationReport,
)
from .correlation import CrossClaimCorrelationEngine
from .document_comparator import DocumentInvoiceAnalyzer, document_analyzer
from .analyst_service import AnalystReviewService, analyst_service

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
    "AnalystDecisionType",
    "EscalationTarget",
    "FindingType",
    "SettlementCorrection",
    "FindingDecision",
    "FindingDecisionRequest",
    "AnalystInvestigationReport",
    "AnalystReviewService",
    "analyst_service",
]

