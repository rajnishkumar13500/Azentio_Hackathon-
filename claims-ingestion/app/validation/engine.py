import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.domain.enums import StagingRecordStatus, ValidationSeverity, ImportJobStatus
from app.persistence.models.import_models import ImportJob, StagingRecord, ValidationError
from app.validation.field_validators import FieldValidator, ValidationErrorItem
from app.validation.business_validators import BusinessValidator
from app.validation.referential_validators import ReferentialValidator
from app.validation.duplicate_validators import DuplicateValidator
from app.audit.audit_service import AuditService

class ValidationEngine:
    @staticmethod
    def validate_import(db: Session, import_id: str) -> Dict[str, Any]:
        """
        Runs comprehensive deterministic validation on all staged records in the import job.
        Persists all errors and updates job reconciliation summary.
        """
        job = db.query(ImportJob).filter(ImportJob.import_id == import_id).first()
        if not job:
            raise ValueError(f"Import job {import_id} not found")

        job.status = ImportJobStatus.VALIDATING.value
        db.commit()

        # Fetch all staged records for this import
        staged_records = db.query(StagingRecord).filter(
            StagingRecord.import_id == import_id
        ).all()

        # Clear existing validation errors for idempotent re-runs
        staging_ids = [r.staging_record_id for r in staged_records]
        if staging_ids:
            db.query(ValidationError).filter(
                ValidationError.staging_record_id.in_(staging_ids)
            ).delete(synchronize_session=False)
            db.commit()

        # Group records by type for bundle cross-referencing
        records_by_type: Dict[str, List[Dict[str, Any]]] = {}
        all_records_repr: List[Dict[str, Any]] = []

        for r in staged_records:
            try:
                norm_dict = json.loads(r.normalised_payload) if r.normalised_payload else {}
            except Exception:
                norm_dict = {}
            rec_repr = {
                "staging_record_id": r.staging_record_id,
                "record_type": r.record_type,
                "normalised_payload": norm_dict,
                "source_file": r.source_file,
                "source_row": r.source_row
            }
            records_by_type.setdefault(r.record_type, []).append(rec_repr)
            all_records_repr.append(rec_repr)

        # 1. Check duplicates across bundle & database
        duplicate_issues_by_record = DuplicateValidator.check_duplicate_records(db, all_records_repr)

        # 2. Check invoice total vs line items arithmetic
        invoice_cross_checks = ReferentialValidator.validate_invoice_totals_cross_check(
            records_by_type.get("INVOICE", []),
            records_by_type.get("INVOICE_LINE_ITEM", [])
        )

        counts = {
            "valid": 0,
            "warning": 0,
            "invalid": 0,
            "duplicate": 0,
            "pending_review": 0,
            "skipped": 0,
        }

        # 3. Validate each staged record
        for r in staged_records:
            # If explicitly skipped during parsing (e.g. blank row), keep as SKIPPED
            if r.processing_status == StagingRecordStatus.SKIPPED.value:
                counts["skipped"] += 1
                continue

            try:
                payload = json.loads(r.normalised_payload) if r.normalised_payload else {}
            except Exception:
                payload = {}

            record_issues: List[ValidationErrorItem] = []

            # Field-level mandatory validation
            record_issues.extend(FieldValidator.validate_mandatory(r.record_type, payload))
            if r.record_type == "CLAIM":
                record_issues.extend(FieldValidator.validate_claim_type(payload))

            # Business validation (Amounts & Dates)
            record_issues.extend(BusinessValidator.validate_amounts(r.record_type, payload))
            record_issues.extend(BusinessValidator.validate_dates(r.record_type, payload))

            # Referential validation (Bundle & Database)
            record_issues.extend(ReferentialValidator.validate_references(
                db, records_by_type, r.record_type, payload
            ))

            # Add invoice total mismatch if applicable
            if r.staging_record_id in invoice_cross_checks:
                record_issues.extend(invoice_cross_checks[r.staging_record_id])

            # Add duplicate issues if applicable
            is_dup = False
            if r.staging_record_id in duplicate_issues_by_record:
                for issue in duplicate_issues_by_record[r.staging_record_id]:
                    record_issues.append(issue)
                    if "DUPLICATE" in issue.error_code:
                        is_dup = True

            # Persist validation error records
            for issue in record_issues:
                err_db = ValidationError(
                    staging_record_id=r.staging_record_id,
                    field_name=issue.field_name,
                    error_code=issue.error_code,
                    severity=issue.severity.value,
                    message=issue.message,
                    received_value=str(issue.received_value) if issue.received_value is not None else None
                )
                db.add(err_db)

            # Determine record status
            has_error = any(iss.severity == ValidationSeverity.ERROR for iss in record_issues)
            has_warning = any(iss.severity == ValidationSeverity.WARNING for iss in record_issues)

            is_doc_candidate = r.source_file.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")) or r.record_type == "DOCUMENT"

            if is_dup:
                r.processing_status = StagingRecordStatus.DUPLICATE.value
                counts["duplicate"] += 1
            elif has_error:
                r.processing_status = StagingRecordStatus.INVALID.value
                counts["invalid"] += 1
            elif has_warning:
                r.processing_status = StagingRecordStatus.WARNING.value
                counts["warning"] += 1
            elif is_doc_candidate and r.processing_status == StagingRecordStatus.PENDING_REVIEW.value:
                # Document OCR candidate requiring explicit human confirmation
                counts["pending_review"] += 1
            else:
                r.processing_status = StagingRecordStatus.VALID.value
                counts["valid"] += 1

        db.commit()

        # Update job summary and reconciliation
        job.valid_records = counts["valid"]
        job.warning_records = counts["warning"]
        job.invalid_records = counts["invalid"]
        job.duplicate_records = counts["duplicate"]
        job.pending_review_records = counts["pending_review"]
        job.explicitly_skipped_records = counts["skipped"]

        # Job status determination
        if (counts["valid"] > 0 or counts["warning"] > 0) and counts["invalid"] == 0 and counts["pending_review"] == 0:
            job.status = ImportJobStatus.READY_TO_COMMIT.value
        else:
            job.status = ImportJobStatus.VALIDATION_COMPLETED.value

        AuditService.log_event(
            db=db,
            import_id=import_id,
            event_type="VALIDATION_COMPLETED",
            actor="system",
            event_details=counts
        )

        db.commit()
        return counts
