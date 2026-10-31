from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class RuleStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    EXCLUDED = "EXCLUDED"
    BREACHED = "BREACHED"
    APPLIED = "APPLIED"
    ANOMALY_SUSPECTED = "ANOMALY_SUSPECTED"

class RuleResult(BaseModel):
    rule_id: str = Field(description="Unique rule code, e.g. POL-EXCL-001, POL-SUBLIM-002")
    rule_name: str
    status: RuleStatus
    claimed_amount: float = 0.0
    admissible_amount: float = 0.0
    discrepancy_amount: float = Field(default=0.0, description="Exact calculated leakage amount")
    suspected_leakage_amount: float = Field(default=0.0, description="Estimated/statistical leakage amount")
    formula_applied: Optional[str] = None
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class LineItemValidation(BaseModel):
    line_id: str
    description: str
    category: str
    claimed_amount: float
    admissible_amount: float
    discrepancy_amount: float
    suspected_leakage_amount: float = 0.0
    status: RuleStatus
    rules_applied: List[RuleResult] = Field(default_factory=list)

class ClaimValidationSummary(BaseModel):
    total_claimed: float
    total_excluded: float
    total_sublimit_deduction: float
    total_proportionate_deduction: float
    procedure_cap_deduction: float
    deductible_applied: float
    copay_applied: float
    balance_sum_insured_cap_deduction: float
    total_calculated_admissible: float
    proposed_settlement: float
    calculated_settlement: float
    calculated_leakage_prevented: float = Field(
        description="Exact overpayment prevented: proposed_settlement - calculated_settlement (if positive)"
    )
    suspected_leakage_total: float = Field(
        description="Estimated pricing outlier leakage requiring medical review"
    )
    overall_status: str = Field(description="APPROVED, FLAGGED_LEAKAGE, REJECTED")

class ValidationReport(BaseModel):
    claim_id: str
    case_title: Optional[str] = None
    policy_id: str
    summary: ClaimValidationSummary
    line_items: List[LineItemValidation] = Field(default_factory=list)
    claim_level_rules: List[RuleResult] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    duplicate_findings: List[Dict[str, Any]] = Field(default_factory=list)

