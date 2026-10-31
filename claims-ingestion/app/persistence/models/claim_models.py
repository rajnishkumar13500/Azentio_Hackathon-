import uuid
from datetime import datetime
from sqlalchemy import Column, String, Date, DateTime, Numeric, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.persistence.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Policy(Base):
    __tablename__ = "policies"

    policy_id = Column(String(36), primary_key=True, default=generate_uuid)
    policy_number = Column(String(100), unique=True, nullable=False, index=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=False)
    sum_insured = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    coverages = relationship("PolicyCoverage", back_populates="policy", cascade="all, delete-orphan")
    exclusions = relationship("PolicyExclusion", back_populates="policy", cascade="all, delete-orphan")
    benefits = relationship("PolicyBenefit", back_populates="policy", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="policy")


class PolicyCoverage(Base):
    __tablename__ = "policy_coverages"

    coverage_id = Column(String(36), primary_key=True, default=generate_uuid)
    policy_id = Column(String(36), ForeignKey("policies.policy_id"), nullable=False, index=True)
    coverage_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    coverage_limit = Column(Numeric(14, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    policy = relationship("Policy", back_populates="coverages")


class PolicyExclusion(Base):
    __tablename__ = "policy_exclusions"

    exclusion_id = Column(String(36), primary_key=True, default=generate_uuid)
    policy_id = Column(String(36), ForeignKey("policies.policy_id"), nullable=False, index=True)
    exclusion_code = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    policy = relationship("Policy", back_populates="exclusions")


class PolicyBenefit(Base):
    __tablename__ = "policy_benefits"

    benefit_id = Column(String(36), primary_key=True, default=generate_uuid)
    policy_id = Column(String(36), ForeignKey("policies.policy_id"), nullable=False, index=True)
    benefit_code = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    benefit_period = Column(String(100), nullable=True)
    sub_limit = Column(Numeric(14, 2), nullable=True)
    deductible = Column(Numeric(14, 2), nullable=True)
    copay_percentage = Column(Numeric(5, 2), nullable=True)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    policy = relationship("Policy", back_populates="benefits")


class Provider(Base):
    __tablename__ = "providers"

    provider_id = Column(String(100), primary_key=True)
    provider_name = Column(String(255), nullable=False)
    provider_code = Column(String(100), nullable=True, index=True)
    provider_type = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoices = relationship("Invoice", back_populates="provider")


class Claim(Base):
    __tablename__ = "claims"

    claim_id = Column(String(100), primary_key=True, index=True)
    policy_id = Column(String(36), ForeignKey("policies.policy_id"), nullable=False, index=True)
    claimant_id = Column(String(100), nullable=False, index=True)
    claimant_name = Column(String(255), nullable=False)
    incident_date = Column(Date, nullable=False)
    claim_type = Column(String(50), nullable=False)  # CASHLESS, REIMBURSEMENT
    requested_amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    claim_status = Column(String(50), default="SUBMITTED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    policy = relationship("Policy", back_populates="claims")
    invoices = relationship("Invoice", back_populates="claim", cascade="all, delete-orphan")
    history_events = relationship("ClaimHistory", back_populates="claim", cascade="all, delete-orphan")
    settlements = relationship("Settlement", back_populates="claim", cascade="all, delete-orphan")
    documents = relationship("ClaimDocument", back_populates="claim")


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(String(100), primary_key=True, index=True)
    claim_id = Column(String(100), ForeignKey("claims.claim_id"), nullable=False, index=True)
    provider_id = Column(String(100), ForeignKey("providers.provider_id"), nullable=True, index=True)
    invoice_reference = Column(String(100), nullable=False, index=True)
    invoice_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    claim = relationship("Claim", back_populates="invoices")
    provider = relationship("Provider", back_populates="invoices")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    line_item_id = Column(String(100), primary_key=True, index=True)
    invoice_id = Column(String(100), ForeignKey("invoices.invoice_id"), nullable=False, index=True)
    service_code = Column(String(100), nullable=True)
    description = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(14, 2), nullable=False)
    line_amount = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoice = relationship("Invoice", back_populates="line_items")


class ClaimHistory(Base):
    __tablename__ = "claim_history"

    history_id = Column(String(100), primary_key=True, default=generate_uuid)
    claim_id = Column(String(100), ForeignKey("claims.claim_id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    event_date = Column(Date, nullable=False)
    event_description = Column(Text, nullable=False)
    amount = Column(Numeric(14, 2), nullable=True)
    source_reference = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    claim = relationship("Claim", back_populates="history_events")


class Settlement(Base):
    __tablename__ = "settlements"

    settlement_id = Column(String(100), primary_key=True, index=True)
    claim_id = Column(String(100), ForeignKey("claims.claim_id"), nullable=False, index=True)
    approved_amount = Column(Numeric(14, 2), nullable=False)
    paid_amount = Column(Numeric(14, 2), nullable=False)
    settlement_date = Column(Date, nullable=False)
    settlement_status = Column(String(50), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    claim = relationship("Claim", back_populates="settlements")


class ClaimDocument(Base):
    __tablename__ = "claim_documents"

    document_id = Column(String(100), primary_key=True, default=generate_uuid)
    claim_id = Column(String(100), ForeignKey("claims.claim_id"), nullable=True, index=True)
    document_type = Column(String(50), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    claim = relationship("Claim", back_populates="documents")
