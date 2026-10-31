from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from app.domain.enums import ClaimType

class PolicyBenefitSchema(BaseModel):
    benefit_id: Optional[str] = None
    benefit_code: str
    description: Optional[str] = None
    benefit_period: Optional[str] = None
    sub_limit: Optional[Decimal] = None
    deductible: Optional[Decimal] = None
    copay_percentage: Optional[Decimal] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

class PolicyCoverageSchema(BaseModel):
    coverage_id: Optional[str] = None
    coverage_type: str
    description: Optional[str] = None
    coverage_limit: Optional[Decimal] = None

class PolicyExclusionSchema(BaseModel):
    exclusion_id: Optional[str] = None
    exclusion_code: str
    description: str

class PolicySchema(BaseModel):
    policy_id: Optional[str] = None
    policy_number: str
    effective_from: date
    effective_to: date
    sum_insured: Decimal
    currency: str = "INR"
    coverages: List[PolicyCoverageSchema] = Field(default_factory=list)
    exclusions: List[PolicyExclusionSchema] = Field(default_factory=list)
    benefits: List[PolicyBenefitSchema] = Field(default_factory=list)

class ProviderSchema(BaseModel):
    provider_id: str
    provider_name: str
    provider_code: Optional[str] = None
    provider_type: Optional[str] = None
    address: Optional[str] = None

class ClaimSchema(BaseModel):
    claim_id: str
    policy_number: Optional[str] = None
    policy_id: Optional[str] = None
    claimant_id: str
    claimant_name: str
    incident_date: date
    claim_type: str
    requested_amount: Decimal
    currency: str = "INR"
    claim_status: str = "SUBMITTED"

class InvoiceLineItemSchema(BaseModel):
    line_item_id: str
    invoice_id: Optional[str] = None
    invoice_reference: Optional[str] = None
    service_code: Optional[str] = None
    description: str
    category: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    line_amount: Decimal

class InvoiceSchema(BaseModel):
    invoice_id: str
    claim_id: str
    provider_id: Optional[str] = None
    provider_code: Optional[str] = None
    invoice_reference: str
    invoice_date: date
    total_amount: Decimal
    currency: str = "INR"
    line_items: List[InvoiceLineItemSchema] = Field(default_factory=list)

class ClaimHistorySchema(BaseModel):
    history_id: Optional[str] = None
    claim_id: str
    event_type: str
    event_date: date
    event_description: str
    amount: Optional[Decimal] = None
    source_reference: Optional[str] = None

class SettlementSchema(BaseModel):
    settlement_id: str
    claim_id: str
    approved_amount: Decimal
    paid_amount: Decimal
    settlement_date: date
    settlement_status: str
    currency: str = "INR"

class DocumentCandidateSchema(BaseModel):
    document_id: Optional[str] = None
    original_filename: str
    document_type: str
    claim_id: Optional[str] = None
    invoice_reference: Optional[str] = None
    invoice_date: Optional[date] = None
    provider_name: Optional[str] = None
    total_amount: Optional[Decimal] = None
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: Optional[float] = None
    raw_text: Optional[str] = None
