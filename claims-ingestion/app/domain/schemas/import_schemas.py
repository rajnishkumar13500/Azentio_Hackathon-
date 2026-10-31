from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.domain.enums import ImportJobStatus, StagingRecordStatus, ValidationSeverity

class ValidationErrorResponse(BaseModel):
    validation_error_id: str
    staging_record_id: str
    field_name: Optional[str] = None
    error_code: str
    severity: ValidationSeverity
    message: str
    received_value: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class StagingRecordResponse(BaseModel):
    staging_record_id: str
    import_id: str
    record_type: str
    source_file: str
    source_sheet: Optional[str] = None
    source_row: Optional[int] = None
    source_page: Optional[int] = None
    source_record_id: Optional[str] = None
    raw_payload: Dict[str, Any]
    normalised_payload: Dict[str, Any]
    processing_status: StagingRecordStatus
    validation_errors: List[ValidationErrorResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ImportJobResponse(BaseModel):
    import_id: str
    source_type: str
    status: ImportJobStatus
    total_source_records: int
    parsed_records: int
    valid_records: int
    warning_records: int
    invalid_records: int
    duplicate_records: int
    pending_review_records: int
    explicitly_skipped_records: int
    imported_records: int
    failed_records: int
    created_by: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    class Config:
        from_attributes = True

class FieldMappingRule(BaseModel):
    source_field: str
    canonical_field: str

class FieldMappingRequest(BaseModel):
    template_name: Optional[str] = "default"
    record_type: str
    mappings: List[FieldMappingRule]

class CommitRequest(BaseModel):
    confirm: bool = True
    include_valid: bool = True
    include_reviewed_warnings: bool = True
    include_record_ids: List[str] = Field(default_factory=list)
    exclude_record_ids: List[str] = Field(default_factory=list)
    acknowledged_warning_count: int = 0
    commit_token: Optional[str] = None

class CommitResponse(BaseModel):
    import_id: str
    status: str
    imported_records: int
    rejected_records: int
    failed_records: int
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

class AuditEventResponse(BaseModel):
    audit_event_id: str
    import_id: str
    event_type: str
    actor: str
    event_details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class StagingRecordUpdateRequest(BaseModel):
    normalised_payload: Dict[str, Any]
    mark_as_valid: Optional[bool] = False
