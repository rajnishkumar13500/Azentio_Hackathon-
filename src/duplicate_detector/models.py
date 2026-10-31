"""
Data Models for Duplicate Claims and Leakage Detection Engine.
Uses Python dataclasses for robust typing and serialization without external dependencies.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class DuplicateScenarioType(str, Enum):
    EXACT_DUPLICATE_CLAIM = "EXACT_DUPLICATE_CLAIM"
    INTRA_CLAIM_DUPLICATE_LINE = "INTRA_CLAIM_DUPLICATE_LINE"
    CROSS_CLAIM_DUPLICATE_LINE = "CROSS_CLAIM_DUPLICATE_LINE"
    NEAR_DUPLICATE_CLAIM = "NEAR_DUPLICATE_CLAIM"
    NEAR_DUPLICATE_LINE = "NEAR_DUPLICATE_LINE"
    POLICY_LIMIT_BREACH = "POLICY_LIMIT_BREACH"
    LEGITIMATE_REPEAT_SERVICE = "LEGITIMATE_REPEAT_SERVICE"
    CLEAN_VALID_CLAIM = "CLEAN_VALID_CLAIM"


class LeakageClassification(str, Enum):
    CALCULATED_EXACT = "CALCULATED_EXACT"
    SUSPECTED_ESTIMATED = "SUSPECTED_ESTIMATED"
    NONE = "NONE"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class Recommendation(str, Enum):
    REJECT_CLAIM = "REJECT_CLAIM"
    DISALLOW_LINE_ITEM = "DISALLOW_LINE_ITEM"
    INVESTIGATE_FOR_REVIEW = "INVESTIGATE_FOR_REVIEW"
    ALLOW = "ALLOW"


@dataclass
class LineItem:
    line_id: str
    claim_id: str
    invoice_number: str
    service_date: str
    service_code: str
    service_category: str
    service_description: str
    quantity: float
    unit_price: float
    total_amount: float
    is_recurring_treatment: bool = False
    session_number: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineItem":
        return cls(
            line_id=data["line_id"],
            claim_id=data["claim_id"],
            invoice_number=data.get("invoice_number", ""),
            service_date=data["service_date"],
            service_code=data["service_code"],
            service_category=data.get("service_category", "GENERAL"),
            service_description=data["service_description"],
            quantity=float(data.get("quantity", 1)),
            unit_price=float(data["unit_price"]),
            total_amount=float(data["total_amount"]),
            is_recurring_treatment=bool(data.get("is_recurring_treatment", False)),
            session_number=int(data["session_number"]) if data.get("session_number") is not None else None
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    claim_id: str
    policy_number: str
    claimant_id: str
    claimant_name: str
    incident_date: str
    claim_submission_date: str
    claim_type: str
    claim_status: str
    provider_id: str
    provider_name: str
    invoice_number: str
    invoice_date: str
    total_claimed_amount: float
    approved_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    line_items: List[LineItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], items: Optional[List[LineItem]] = None) -> "Claim":
        lines = items if items is not None else [
            LineItem.from_dict(item) for item in data.get("line_items", [])
        ]
        return cls(
            claim_id=data["claim_id"],
            policy_number=data["policy_number"],
            claimant_id=data["claimant_id"],
            claimant_name=data["claimant_name"],
            incident_date=data["incident_date"],
            claim_submission_date=data["claim_submission_date"],
            claim_type=data.get("claim_type", "HEALTH"),
            claim_status=data.get("claim_status", "SUBMITTED"),
            provider_id=data["provider_id"],
            provider_name=data["provider_name"],
            invoice_number=data["invoice_number"],
            invoice_date=data["invoice_date"],
            total_claimed_amount=float(data["total_claimed_amount"]),
            approved_amount=float(data["approved_amount"]) if data.get("approved_amount") is not None else None,
            paid_amount=float(data["paid_amount"]) if data.get("paid_amount") is not None else None,
            line_items=lines
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["line_items"] = [item.to_dict() for item in self.line_items]
        return d


@dataclass
class ArithmeticProof:
    formula: str                  # e.g., "(unit_price - policy_limit) * quantity"
    input_values: str             # e.g., "(₹7,000 - ₹5,000) * 3"
    calculated_discrepancy: float # e.g., 6000.0
    explanation: str              # Step-by-step arithmetic summary

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MatchedEvidence:
    source_type: str  # "HISTORICAL_CLAIM", "CURRENT_CLAIM_LINE", "POLICY_TERM"
    matched_claim_id: Optional[str] = None
    matched_line_id: Optional[str] = None
    matched_invoice_number: Optional[str] = None
    matched_service_code: Optional[str] = None
    matched_service_description: Optional[str] = None
    matched_service_date: Optional[str] = None
    matched_amount: Optional[float] = None
    similarity_score: float = 1.0


@dataclass
class DuplicateFinding:
    finding_id: str
    scenario_type: DuplicateScenarioType
    severity: Severity
    confidence_score: float  # 0.0 to 1.0
    leakage_classification: LeakageClassification
    leakage_amount: float
    current_claim_id: str
    current_line_id: Optional[str]
    current_line_description: Optional[str]
    current_line_amount: Optional[float]
    evidence: MatchedEvidence
    explanation: str
    rule_code: str
    suggested_action: Recommendation
    arithmetic_proof: Optional[ArithmeticProof] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scenario_type"] = self.scenario_type.value
        d["severity"] = self.severity.value
        d["leakage_classification"] = self.leakage_classification.value
        d["suggested_action"] = self.suggested_action.value
        if self.arithmetic_proof:
            d["arithmetic_proof"] = self.arithmetic_proof.to_dict()
        return d


@dataclass
class LeakageSummary:
    total_leakage_calculated: float
    total_leakage_suspected: float
    overall_leakage_amount: float
    highest_severity: Severity
    findings_count: int
    recommendation: Recommendation

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["highest_severity"] = self.highest_severity.value
        d["recommendation"] = self.recommendation.value
        return d


@dataclass
class DuplicateDetectionResult:
    claim_id: str
    has_duplicate_leakage: bool
    summary: LeakageSummary
    findings: List[DuplicateFinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "has_duplicate_leakage": self.has_duplicate_leakage,
            "summary": self.summary.to_dict(),
            "findings": [f.to_dict() for f in self.findings]
        }

