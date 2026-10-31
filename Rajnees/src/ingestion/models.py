from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from src.schemas import Claim

class IngestionError(BaseModel):
    record_id: Optional[str] = None
    row_number: Optional[int] = None
    field_name: str
    rejected_value: Any = None
    error_message: str

class IngestionResult(BaseModel):
    success: bool
    source_filename: Optional[str] = None
    format_detected: str
    total_records: int = 0
    valid_records_count: int = 0
    invalid_records_count: int = 0
    claims: List[Claim] = Field(default_factory=list)
    errors: List[IngestionError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

