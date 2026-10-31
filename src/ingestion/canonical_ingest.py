"""
Backend-only adapter for the claims-ingestion pipeline.

Runs JobManager → validation → commit, then maps canonical DB claims into
studio Claim objects so the existing dashboard can consume them.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Tuple

from src.ingestion.models import IngestionError, IngestionResult
from src.ingestion.pipeline_bridge import map_pipeline_claim_to_studio
from src.schemas import Claim

logger = logging.getLogger(__name__)

CLAIMS_INGESTION_ROOT = Path(__file__).resolve().parent.parent.parent / "claims-ingestion"
CANONICAL_HEADER_HINTS = ("policy_number", "claim_type", "requested_amount", "incident_date")
PIPELINE_EXTS = {"pdf", "png", "jpg", "jpeg"}
_READY = False


def _ensure_pipeline_on_path() -> None:
    root = str(CLAIMS_INGESTION_ROOT)
    if CLAIMS_INGESTION_ROOT.exists() and root not in sys.path:
        sys.path.insert(0, root)


def canonical_pipeline_available() -> bool:
    if not CLAIMS_INGESTION_ROOT.exists():
        return False
    try:
        _bootstrap()
        return True
    except Exception as e:
        logger.warning("Canonical ingestion pipeline unavailable: %s", e)
        return False


def _bootstrap() -> None:
    global _READY
    _ensure_pipeline_on_path()
    from app.persistence.database import engine, Base  # type: ignore
    from app.persistence import models as _models  # noqa: F401  type: ignore

    Base.metadata.create_all(bind=engine)
    _READY = True


def looks_like_canonical_payload(filename: str, content: bytes) -> bool:
    ext = os.path.splitext(filename or "")[1].lower().strip(".")
    if ext in PIPELINE_EXTS:
        return True
    sample = content[:12000].decode("utf-8", errors="replace").lower()
    hits = sum(1 for hint in CANONICAL_HEADER_HINTS if hint in sample)
    return hits >= 2


def ingest_bytes_via_canonical(filename: str, content: bytes) -> IngestionResult:
    return _run_job(
        files=[(filename, content)],
        source_type="UPLOAD",
        source_filename=filename,
        format_detected=os.path.splitext(filename)[1].lower().strip(".") or "unknown",
    )


def ingest_sample_dataset_via_canonical(dataset_name: str = "small") -> IngestionResult:
    _bootstrap()
    from app.config import settings  # type: ignore

    if dataset_name not in {"small", "large"}:
        raise ValueError("dataset_name must be 'small' or 'large'")

    sample_dir = os.path.join(settings.SAMPLE_DATA_DIR, dataset_name)
    if not os.path.isdir(sample_dir):
        raise FileNotFoundError(f"Sample dataset '{dataset_name}' not found at {sample_dir}")

    files: List[Tuple[str, bytes]] = []
    for item in sorted(os.listdir(sample_dir)):
        path = os.path.join(sample_dir, item)
        if os.path.isfile(path):
            with open(path, "rb") as handle:
                files.append((item, handle.read()))
    return _run_job(
        files=files,
        source_type=f"SAMPLE_DATASET_{dataset_name.upper()}",
        source_filename=f"canonical-{dataset_name}-dataset",
        format_detected="canonical_bundle",
    )


def _run_job(
    files: List[Tuple[str, bytes]],
    source_type: str,
    source_filename: str,
    format_detected: str,
) -> IngestionResult:
    _bootstrap()
    from app.config import settings  # type: ignore
    from app.domain.enums import StagingRecordStatus  # type: ignore
    from app.domain.schemas.import_schemas import CommitRequest  # type: ignore
    from app.ingestion.job_manager import JobManager  # type: ignore
    from app.persistence.commit_service import CommitService  # type: ignore
    from app.persistence.database import SessionLocal  # type: ignore
    from app.persistence.models.claim_models import Claim as PipelineClaim  # type: ignore
    from app.persistence.models.import_models import StagingRecord, ValidationError  # type: ignore
    from app.validation.engine import ValidationEngine  # type: ignore

    if not files:
        return IngestionResult(
            success=False,
            source_filename=source_filename,
            format_detected=format_detected,
            errors=[
                IngestionError(
                    field_name="files",
                    error_message="No files provided to the canonical ingestion pipeline.",
                )
            ],
        )

    db = SessionLocal()
    try:
        job = JobManager.create_job(db=db, source_type=source_type, created_by="studio")
        upload_dir = os.path.join(settings.STORAGE_DIR, "uploads", job.import_id)
        os.makedirs(upload_dir, exist_ok=True)

        for filename, content in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in settings.ALLOWED_EXTENSIONS:
                continue
            saved_path = os.path.join(upload_dir, filename)
            with open(saved_path, "wb") as out:
                out.write(content)
            fmt = ext.replace(".", "").upper()
            if fmt in {"JPG", "JPEG", "PNG"}:
                fmt = "IMAGE"
            JobManager.register_file(
                db=db,
                import_id=job.import_id,
                filename=filename,
                file_path=saved_path,
                file_format=fmt,
            )

        JobManager.process_import_files(db=db, import_id=job.import_id)
        ValidationEngine.validate_import(db=db, import_id=job.import_id)
        db.refresh(job)

        commit = CommitService.commit_import(
            db=db,
            import_id=job.import_id,
            commit_request=CommitRequest(
                confirm=True,
                include_valid=True,
                include_reviewed_warnings=True,
                acknowledged_warning_count=job.warning_records or 0,
            ),
            actor="studio",
        )
        db.refresh(job)

        claim_ids = []
        eligible_statuses = {
            StagingRecordStatus.VALID.value,
            StagingRecordStatus.WARNING.value,
            StagingRecordStatus.DUPLICATE.value,
        }
        for row in (
            db.query(StagingRecord)
            .filter(
                StagingRecord.import_id == job.import_id,
                StagingRecord.record_type == "CLAIM",
            )
            .all()
        ):
            if row.processing_status not in eligible_statuses:
                continue
            try:
                payload = json.loads(row.normalised_payload or "{}")
            except json.JSONDecodeError:
                payload = {}
            cid = payload.get("claim_id") or row.source_record_id
            if cid:
                claim_ids.append(cid)

        studio_claims: List[Claim] = []
        if claim_ids:
            db_claims = (
                db.query(PipelineClaim).filter(PipelineClaim.claim_id.in_(sorted(set(claim_ids)))).all()
            )
            for db_claim in db_claims:
                try:
                    studio_claims.append(map_pipeline_claim_to_studio(db_claim))
                except Exception as e:
                    logger.warning("Could not map pipeline claim %s: %s", db_claim.claim_id, e)

        errors: List[IngestionError] = []
        warnings: List[str] = []
        error_rows = (
            db.query(ValidationError, StagingRecord)
            .join(StagingRecord, ValidationError.staging_record_id == StagingRecord.staging_record_id)
            .filter(StagingRecord.import_id == job.import_id)
            .all()
        )
        for verr, staging in error_rows:
            item = IngestionError(
                record_id=staging.source_record_id,
                row_number=staging.source_row,
                field_name=verr.field_name or verr.error_code,
                rejected_value=verr.received_value,
                error_message=verr.message,
            )
            if (verr.severity or "").upper() == "WARNING":
                warnings.append(verr.message)
            else:
                errors.append(item)

        total = job.parsed_records or 0
        valid = len(studio_claims)
        invalid = max(total - valid, job.invalid_records or 0)
        success = valid > 0
        if commit.imported_records == 0 and valid == 0:
            success = False

        return IngestionResult(
            success=success,
            source_filename=source_filename,
            format_detected=format_detected,
            total_records=total,
            valid_records_count=valid,
            invalid_records_count=invalid,
            claims=studio_claims,
            errors=errors,
            warnings=warnings,
        )
    except Exception as e:
        logger.exception("Canonical ingestion failed")
        return IngestionResult(
            success=False,
            source_filename=source_filename,
            format_detected=format_detected,
            errors=[
                IngestionError(
                    field_name="canonical_pipeline",
                    rejected_value=str(e),
                    error_message=f"Canonical ingestion failed: {e}",
                )
            ],
        )
    finally:
        db.close()
