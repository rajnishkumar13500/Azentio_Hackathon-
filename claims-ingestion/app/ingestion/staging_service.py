import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.domain.enums import ImportJobStatus, StagingRecordStatus
from app.persistence.models.import_models import ImportJob, ImportFile, StagingRecord
from app.ingestion.parsers.base import ParsedSourceRecord
from app.ingestion.mapping.mapper import FieldMapper
from app.ingestion.normalisation.normaliser import Normaliser
from app.audit.audit_service import AuditService

class StagingService:
    @staticmethod
    def stage_records(
        db: Session,
        import_id: str,
        parsed_records: List[ParsedSourceRecord],
        mapping_rules: Optional[Dict[str, str]] = None
    ) -> int:
        job = db.query(ImportJob).filter(ImportJob.import_id == import_id).first()
        if not job:
            raise ValueError(f"Import job {import_id} not found")

        job.status = ImportJobStatus.STAGING.value
        db.commit()

        staged_count = 0
        skipped_count = 0

        for prec in parsed_records:
            rec_type = prec.record_type_hint or "CLAIM"

            if prec.is_skipped:
                # Store explicitly skipped record with reason
                st_rec = StagingRecord(
                    import_id=import_id,
                    record_type=rec_type,
                    source_file=prec.source_file,
                    source_sheet=prec.source_sheet,
                    source_row=prec.source_row,
                    source_page=prec.source_page,
                    source_record_id=prec.source_record_id,
                    raw_payload=json.dumps({"_skip_reason": prec.skip_reason}),
                    normalised_payload=json.dumps({"_skip_reason": prec.skip_reason}),
                    processing_status=StagingRecordStatus.SKIPPED.value,
                    created_at=datetime.utcnow()
                )
                db.add(st_rec)
                skipped_count += 1
                continue

            # Map raw fields to canonical schema
            mapped = FieldMapper.map_record(rec_type, prec.raw_payload, mapping_rules)
            # Normalise values
            normalised = Normaliser.normalise_record(rec_type, mapped)

            initial_status = StagingRecordStatus.PENDING_REVIEW.value if rec_type == "DOCUMENT" else StagingRecordStatus.PENDING_REVIEW.value

            st_rec = StagingRecord(
                import_id=import_id,
                record_type=rec_type,
                source_file=prec.source_file,
                source_sheet=prec.source_sheet,
                source_row=prec.source_row,
                source_page=prec.source_page,
                source_record_id=prec.source_record_id or normalised.get("claim_id") or normalised.get("policy_number") or normalised.get("invoice_id"),
                raw_payload=json.dumps(prec.raw_payload, default=str),
                normalised_payload=json.dumps(normalised, default=str),
                processing_status=initial_status,
                created_at=datetime.utcnow()
            )
            db.add(st_rec)
            staged_count += 1

        db.flush()

        job.parsed_records += (staged_count + skipped_count)
        job.total_source_records += (staged_count + skipped_count)
        job.explicitly_skipped_records += skipped_count
        db.commit()

        AuditService.log_event(
            db=db,
            import_id=import_id,
            event_type="RECORDS_STAGED",
            actor="system",
            event_details={"staged_records": staged_count, "skipped_records": skipped_count}
        )
        return staged_count

    @staticmethod
    def update_staged_record(
        db: Session,
        staging_record_id: str,
        updated_normalised_payload: Dict[str, Any],
        mark_as_valid: bool = False
    ) -> StagingRecord:
        record = db.query(StagingRecord).filter(
            StagingRecord.staging_record_id == staging_record_id
        ).first()
        if not record:
            raise ValueError(f"Staging record {staging_record_id} not found")

        # Re-normalise updated payload
        normalised = Normaliser.normalise_record(record.record_type, updated_normalised_payload)
        record.normalised_payload = json.dumps(normalised, default=str)
        if mark_as_valid:
            record.processing_status = StagingRecordStatus.VALID.value
        record.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(record)
        return record
