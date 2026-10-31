"""
Data models for Claims Investigation Workspace & Cross-Claim Correlation.
"""

from datetime import datetime, UTC
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CorrelationRelationshipType(str, Enum):
    CROSS_POLICY_SHARED_INVOICE = "CROSS_POLICY_SHARED_INVOICE"
    OVERLAPPING_HOSPITALIZATION = "OVERLAPPING_HOSPITALIZATION"
    SPLIT_INCIDENT_CLAIM = "SPLIT_INCIDENT_CLAIM"
    HIGH_VELOCITY_PROVIDER_COLLUSION = "HIGH_VELOCITY_PROVIDER_COLLUSION"
    PROVIDER_SHARED_INVOICE_ACROSS_PATIENTS = "PROVIDER_SHARED_INVOICE_ACROSS_PATIENTS"
    CLAIMANT_HISTORY = "CLAIMANT_HISTORY"
    SHARED_INCIDENT_DETAILS = "SHARED_INCIDENT_DETAILS"


class NetworkNode(BaseModel):
    id: str
    label: str
    type: str  # CLAIM, POLICY, CLAIMANT, PROVIDER, INVOICE
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NetworkEdge(BaseModel):
    source: str
    target: str
    label: str
    relationship_type: str
    severity: str = "MEDIUM"


class CorrelationMatch(BaseModel):
    target_claim_id: str
    matched_claim_id: str
    relationship_type: CorrelationRelationshipType
    severity: str = Field(description="CRITICAL, HIGH, MEDIUM, LOW, INFO")
    matching_attributes: List[str] = Field(
        default_factory=list,
        description="List of attributes that link the claims (e.g. ['invoice_number', 'provider_id'])"
    )
    shared_values: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value pairs of matched attributes"
    )
    explanation: str = Field(
        description="Detailed, human-readable reason why these claims are correlated"
    )
    potential_leakage_amount: float = Field(
        default=0.0,
        description="Calculated financial exposure from this cross-claim correlation"
    )
    matched_claim_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary metadata of the correlated claim"
    )
    requires_investigation: bool = Field(
        default=True,
        description="Whether this correlation warrants active analyst review"
    )


class CrossClaimCorrelationReport(BaseModel):
    claim_id: str
    total_correlated_claims: int = 0
    highest_severity: str = "NONE"
    total_potential_leakage: float = 0.0
    correlations: List[CorrelationMatch] = Field(default_factory=list)
    network_nodes: List[NetworkNode] = Field(default_factory=list)
    network_edges: List[NetworkEdge] = Field(default_factory=list)


# =============================================================================
# Level 2 Step 2: Document & Invoice Analysis Models
# =============================================================================

class VarianceType(str, Enum):
    TOTAL_AMOUNT_MISMATCH = "TOTAL_AMOUNT_MISMATCH"
    DATE_MISMATCH = "DATE_MISMATCH"
    UNSUBSTANTIATED_CLAIM_ITEM = "UNSUBSTANTIATED_CLAIM_ITEM"
    OMITTED_INVOICE_ITEM = "OMITTED_INVOICE_ITEM"
    UNIT_RATE_INFLATION = "UNIT_RATE_INFLATION"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    DIAGNOSIS_MISMATCH = "DIAGNOSIS_MISMATCH"


class DocumentSourceCitation(BaseModel):
    document_name: str
    section: str = "GENERAL"
    line_number: Optional[int] = None
    raw_quote: str = ""


class DocumentFieldComparison(BaseModel):
    field_name: str
    claim_value: Any
    document_value: Any
    variance_type: VarianceType
    variance_amount: float = 0.0
    severity: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    source_citation: DocumentSourceCitation


class DocumentLineItemComparison(BaseModel):
    claim_line_id: Optional[str] = None
    document_item_num: Optional[int] = None
    category: str
    description: str
    claim_unit_rate: Optional[float] = None
    document_unit_rate: Optional[float] = None
    claim_total: Optional[float] = None
    document_total: Optional[float] = None
    discrepancy_amount: float = 0.0
    status: str  # MATCHED, RATE_INFLATED, UNSUBSTANTIATED_IN_CLAIM, OMITTED_FROM_CLAIM
    explanation: str
    source_citation: DocumentSourceCitation


class DocumentReconciliationReport(BaseModel):
    claim_id: str
    document_name: str
    document_type: str = "HOSPITAL_TAX_INVOICE"
    total_variances_detected: int = 0
    total_financial_leakage: float = 0.0
    field_comparisons: List[DocumentFieldComparison] = Field(default_factory=list)
    line_item_reconciliations: List[DocumentLineItemComparison] = Field(default_factory=list)
    extracted_metadata: Dict[str, Any] = Field(default_factory=dict)
    summary_verdict: str = "VERIFIED_MATCH"


# =============================================================================
# Level 2 Step 4 & 5: Recommended Settlement Corrections & Analyst Review
# =============================================================================

class AnalystDecisionType(str, Enum):
    CONFIRM_DISCREPANCY = "CONFIRM_DISCREPANCY"
    MARK_FALSE_POSITIVE = "MARK_FALSE_POSITIVE"
    REQUEST_ADDITIONAL_EVIDENCE = "REQUEST_ADDITIONAL_EVIDENCE"
    ESCALATE = "ESCALATE"
    ACCEPT_CORRECTION = "ACCEPT_CORRECTION"


class EscalationTarget(str, Enum):
    SENIOR_CLAIMS_REVIEWER = "SENIOR_CLAIMS_REVIEWER"
    SPECIAL_INVESTIGATION_UNIT = "SPECIAL_INVESTIGATION_UNIT"


class FindingType(str, Enum):
    LINE_ITEM = "LINE_ITEM"
    RULE_VIOLATION = "RULE_VIOLATION"
    CORRELATION = "CORRELATION"
    DOCUMENT_VARIANCE = "DOCUMENT_VARIANCE"


class SettlementCorrection(BaseModel):
    correction_id: str
    finding_id: str
    finding_type: FindingType
    category: str
    description: str
    original_amount: float
    corrected_amount: float
    adjustment_amount: float
    calculation_formula: str
    policy_rule_or_evidence: str
    status: str = "RECOMMENDED"


class FindingDecision(BaseModel):
    finding_id: str
    finding_type: FindingType
    decision: AnalystDecisionType
    reason: Optional[str] = None
    escalation_target: Optional[EscalationTarget] = None
    analyst_id: str = "Senior Claims Auditor"
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    original_leakage: float = 0.0
    adjusted_leakage: float = 0.0


class FindingDecisionRequest(BaseModel):
    finding_id: str
    finding_type: FindingType = FindingType.LINE_ITEM
    decision: AnalystDecisionType
    reason: Optional[str] = None
    escalation_target: Optional[EscalationTarget] = None
    analyst_id: Optional[str] = "Senior Claims Auditor"


class AnalystInvestigationReport(BaseModel):
    claim_id: str
    case_title: str
    total_findings: int
    total_reviewed: int
    pending_review: int
    decisions_breakdown: Dict[str, int]
    escalation_status: str  # NORMAL, SENIOR_REVIEW_REQUESTED, SIU_ESCALATED
    original_claimed_amount: float
    original_admissible_amount: float
    original_leakage_prevented: float
    net_adjusted_settlement: float
    net_adjusted_leakage: float
    line_item_findings: List[Dict[str, Any]]
    rule_findings: List[Dict[str, Any]]
    recommended_corrections: List[SettlementCorrection]
    decisions: List[FindingDecision]
    audit_notes: List[str] = Field(default_factory=list)

