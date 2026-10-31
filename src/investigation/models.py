"""
Data models for Claims Investigation Workspace & Cross-Claim Correlation.
"""

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
