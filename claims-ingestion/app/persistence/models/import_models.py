import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.persistence.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class ImportJob(Base):
    __tablename__ = "import_jobs"

    import_id = Column(String(36), primary_key=True, default=generate_uuid)
    source_type = Column(String(50), nullable=False)  # UPLOAD, SAMPLE_DATASET
    status = Column(String(50), nullable=False, default="CREATED", index=True)
    
    total_source_records = Column(Integer, default=0, nullable=False)
    parsed_records = Column(Integer, default=0, nullable=False)
    valid_records = Column(Integer, default=0, nullable=False)
    warning_records = Column(Integer, default=0, nullable=False)
    invalid_records = Column(Integer, default=0, nullable=False)
    duplicate_records = Column(Integer, default=0, nullable=False)
    pending_review_records = Column(Integer, default=0, nullable=False)
    explicitly_skipped_records = Column(Integer, default=0, nullable=False)
    imported_records = Column(Integer, default=0, nullable=False)
    failed_records = Column(Integer, default=0, nullable=False)
    
    created_by = Column(String(100), default="system", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    commit_token = Column(String(100), nullable=True, unique=True)
    failure_reason = Column(Text, nullable=True)

    files = relationship("ImportFile", back_populates="import_job", cascade="all, delete-orphan")
    staging_records = relationship("StagingRecord", back_populates="import_job", cascade="all, delete-orphan")
    audit_events = relationship("ImportAuditEvent", back_populates="import_job", cascade="all, delete-orphan")


class ImportFile(Base):
    __tablename__ = "import_files"

    import_file_id = Column(String(36), primary_key=True, default=generate_uuid)
    import_id = Column(String(36), ForeignKey("import_jobs.import_id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    file_format = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    import_job = relationship("ImportJob", back_populates="files")


class StagingRecord(Base):
    __tablename__ = "staging_records"

    staging_record_id = Column(String(36), primary_key=True, default=generate_uuid)
    import_id = Column(String(36), ForeignKey("import_jobs.import_id"), nullable=False, index=True)
    record_type = Column(String(50), nullable=False, index=True)  # CLAIM, POLICY, INVOICE, etc.
    source_file = Column(String(255), nullable=False)
    source_sheet = Column(String(100), nullable=True)
    source_row = Column(Integer, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_record_id = Column(String(100), nullable=True, index=True)
    raw_payload = Column(Text, nullable=False)  # JSON representation of raw input
    normalised_payload = Column(Text, nullable=False)  # JSON representation of canonical mapped input
    processing_status = Column(String(50), nullable=False, default="PENDING_REVIEW", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    import_job = relationship("ImportJob", back_populates="staging_records")
    validation_errors = relationship("ValidationError", back_populates="staging_record", cascade="all, delete-orphan")


class ValidationError(Base):
    __tablename__ = "validation_errors"

    validation_error_id = Column(String(36), primary_key=True, default=generate_uuid)
    staging_record_id = Column(String(36), ForeignKey("staging_records.staging_record_id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=True)
    error_code = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False)  # ERROR, WARNING, INFO
    message = Column(Text, nullable=False)
    received_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    staging_record = relationship("StagingRecord", back_populates="validation_errors")


class FieldMapping(Base):
    __tablename__ = "field_mappings"

    mapping_id = Column(String(36), primary_key=True, default=generate_uuid)
    template_name = Column(String(100), nullable=False, index=True)
    record_type = Column(String(50), nullable=False)
    source_field = Column(String(100), nullable=False)
    canonical_field = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ImportAuditEvent(Base):
    __tablename__ = "import_audit_events"

    audit_event_id = Column(String(36), primary_key=True, default=generate_uuid)
    import_id = Column(String(36), ForeignKey("import_jobs.import_id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    actor = Column(String(100), nullable=False, default="user")
    event_details = Column(Text, nullable=True)  # JSON text
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    import_job = relationship("ImportJob", back_populates="audit_events")
