from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class WaitingPeriods(BaseModel):
    initial_waiting_days: int = 30
    specific_diseases_months: int = 24
    pre_existing_disease_months: int = 36

class PolicySubLimits(BaseModel):
    daily_room_rent: float = Field(default=5000.0, description="Max daily room rent allowed")
    daily_icu_rent: float = Field(default=10000.0, description="Max daily ICU rent allowed")
    ambulance_limit: float = Field(default=2500.0, description="Max ambulance expense allowed")
    procedure_caps: Dict[str, float] = Field(
        default_factory=dict,
        description="Disease or procedure specific financial caps, e.g. {'cataract': 35000.0}"
    )

class Policy(BaseModel):
    policy_id: str
    policy_name: str
    start_date: str
    end_date: str
    status: str = Field(default="ACTIVE", description="ACTIVE, EXPIRED, LAPSED, SUSPENDED")
    sum_insured: float = Field(gt=0, description="Total sum insured for policy year")
    balance_sum_insured: float = Field(ge=0, description="Remaining sum insured available")
    co_payment_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Co-pay % payable by claimant")
    deductible_per_claim: float = Field(default=0.0, ge=0.0, description="Deductible per claim")
    deductible_annual_remaining: float = Field(default=0.0, ge=0.0, description="Annual aggregate deductible remaining")
    proportionate_deduction: bool = Field(default=True, description="Enable proportionate deduction on room rent breach")
    sub_limits: PolicySubLimits = Field(default_factory=PolicySubLimits)
    waiting_periods: WaitingPeriods = Field(default_factory=WaitingPeriods)
    covered_dependents: List[str] = Field(default_factory=lambda: ["SELF", "SPOUSE", "CHILD_1", "CHILD_2"])

