from typing import List, Optional
from pydantic import BaseModel, Field

class Claimant(BaseModel):
    claimant_id: str
    name: str
    relationship_to_insured: str = Field(default="SELF", description="SELF, SPOUSE, CHILD_1, PARENT")
    age: int = Field(ge=0, le=120)

class IncidentDetails(BaseModel):
    admission_date: str
    discharge_date: str
    hospital_id: str
    hospital_name: Optional[str] = None
    icd10_code: Optional[str] = None
    diagnosis_description: str
    policy_tenure_months: int = Field(default=12, ge=0, description="Months since policy initiation")
    is_pre_existing: bool = Field(default=False, description="Whether condition is flagged as pre-existing")
    proposed_settlement_amount: float = Field(default=0.0, ge=0.0, description="Amount proposed by claim handler")

class LineItem(BaseModel):
    line_id: str
    category: str = Field(
        description="ROOM_RENT, ICU_RENT, SURGERY, CONSULTATION, CONSUMABLE, PHARMACY, INVESTIGATION, ADMINISTRATIVE"
    )
    item_code: str
    description: str
    quantity: float = Field(default=1.0, gt=0)
    unit_price: float = Field(ge=0.0)
    total_amount: float = Field(ge=0.0)
    service_date: Optional[str] = None

class Claim(BaseModel):
    claim_id: str
    case_title: Optional[str] = None
    policy_id: str
    claimant: Claimant
    incident_details: IncidentDetails
    line_items: List[LineItem] = Field(default_factory=list)
