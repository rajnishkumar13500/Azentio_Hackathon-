import os
import io
import csv
import json
import shutil
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.persistence.database import get_db
from app.domain.enums import ImportJobStatus, StagingRecordStatus
from app.domain.schemas.import_schemas import (
    ImportJobResponse,
    StagingRecordResponse,
    ValidationErrorResponse,
    CommitRequest,
    CommitResponse,
    StagingRecordUpdateRequest,
    AuditEventResponse
)
from app.persistence.models.import_models import ImportJob, ImportFile, StagingRecord, ValidationError
from app.ingestion.job_manager import JobManager
from app.ingestion.staging_service import StagingService
from app.validation.engine import ValidationEngine
from app.persistence.commit_service import CommitService
from app.audit.audit_service import AuditService
from app.config import settings

router = APIRouter(prefix="/imports", tags=["Imports"])

@router.post("", response_model=ImportJobResponse)
async def create_import(
    files: List[UploadFile] = File(...),
    created_by: str = Form("user"),
    db: Session = Depends(get_db)
):
    """Create a new import job and upload files."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    job = JobManager.create_job(db=db, source_type="UPLOAD", created_by=created_by)
    upload_dir = os.path.join(settings.STORAGE_DIR, "uploads", job.import_id)
    os.makedirs(upload_dir, exist_ok=True)

    for file in files:
        # Security validation on file extension
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File extension '{ext}' for file '{file.filename}' is not supported. Allowed: {list(settings.ALLOWED_EXTENSIONS)}"
            )

        saved_path = os.path.join(upload_dir, file.filename)
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds max size limit of {settings.MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
            )

        with open(saved_path, "wb") as f_out:
            f_out.write(content)

        fmt = ext.replace(".", "").upper()
        if fmt in ["JPG", "JPEG", "PNG"]:
            fmt = "IMAGE"
        JobManager.register_file(
            db=db,
            import_id=job.import_id,
            filename=file.filename,
            file_path=saved_path,
            file_format=fmt
        )

    # Process files into staging
    JobManager.process_import_files(db=db, import_id=job.import_id)
    # Run validation immediately
    ValidationEngine.validate_import(db=db, import_id=job.import_id)

    db.refresh(job)
    return job


@router.post("/sample-datasets", response_model=ImportJobResponse)
def import_sample_dataset(
    dataset_name: str = Query("small", regex="^(small|large)$"),
    db: Session = Depends(get_db)
):
    """
    Starts an import using a built-in synthetic dataset.
    Invokes exactly the same pipeline as file upload!
    """
    job = JobManager.create_job(db=db, source_type=f"SAMPLE_DATASET_{dataset_name.upper()}", created_by="synthetic_generator")
    
    # Locate sample files
    sample_dir = os.path.join(settings.SAMPLE_DATA_DIR, dataset_name)
    if not os.path.exists(sample_dir):
        raise HTTPException(status_code=404, detail=f"Sample dataset '{dataset_name}' not found at {sample_dir}")

    dest_dir = os.path.join(settings.STORAGE_DIR, "uploads", job.import_id)
    os.makedirs(dest_dir, exist_ok=True)

    for item in os.listdir(sample_dir):
        src_path = os.path.join(sample_dir, item)
        if os.path.isfile(src_path):
            dest_path = os.path.join(dest_dir, item)
            shutil.copy2(src_path, dest_path)
            ext = os.path.splitext(item)[1].lower()
            fmt = ext.replace(".", "").upper()
            if fmt in ["JPG", "JPEG", "PNG"]:
                fmt = "IMAGE"

            JobManager.register_file(
                db=db,
                import_id=job.import_id,
                filename=item,
                file_path=dest_path,
                file_format=fmt
            )

    # Process and validate using canonical pipeline
    JobManager.process_import_files(db=db, import_id=job.import_id)
    ValidationEngine.validate_import(db=db, import_id=job.import_id)

    db.refresh(job)
    return job


@router.get("", response_model=List[ImportJobResponse])
def list_imports(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List all previous import jobs."""
    jobs = db.query(ImportJob).order_by(ImportJob.created_at.desc()).offset(skip).limit(limit).all()
    return jobs


@router.get("/{import_id}", response_model=ImportJobResponse)
def get_import(
    import_id: str,
    db: Session = Depends(get_db)
):
    """Get import status and reconciliation summary."""
    job = db.query(ImportJob).filter(ImportJob.import_id == import_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Import job {import_id} not found")
    return job


@router.get("/{import_id}/preview")
def preview_staged_records(
    import_id: str,
    record_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Preview staged records with filtering and pagination."""
    job = db.query(ImportJob).filter(ImportJob.import_id == import_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    query = db.query(StagingRecord).filter(StagingRecord.import_id == import_id)
    if record_type:
        query = query.filter(StagingRecord.record_type == record_type)
    if status:
        query = query.filter(StagingRecord.processing_status == status)

    total = query.count()
    records = query.order_by(StagingRecord.source_row.asc()).offset((page - 1) * page_size).limit(page_size).all()

    formatted_records = []
    for r in records:
        try:
            raw_p = json.loads(r.raw_payload) if r.raw_payload else {}
            norm_p = json.loads(r.normalised_payload) if r.normalised_payload else {}
        except Exception:
            raw_p, norm_p = {}, {}

        errors = [
            {
                "field_name": e.field_name,
                "error_code": e.error_code,
                "severity": e.severity,
                "message": e.message,
                "received_value": e.received_value
            }
            for e in r.validation_errors
        ]

        formatted_records.append({
            "staging_record_id": r.staging_record_id,
            "record_type": r.record_type,
            "source_file": r.source_file,
            "source_sheet": r.source_sheet,
            "source_row": r.source_row,
            "source_record_id": r.source_record_id,
            "raw_payload": raw_p,
            "normalised_payload": norm_p,
            "processing_status": r.processing_status,
            "validation_errors": errors,
            "updated_at": r.updated_at
        })

    return {
        "import_id": import_id,
        "total_records": total,
        "page": page,
        "page_size": page_size,
        "records": formatted_records
    }


@router.post("/{import_id}/validate")
def run_validation(
    import_id: str,
    db: Session = Depends(get_db)
):
    """Run or rerun validation on staged records."""
    try:
        counts = ValidationEngine.validate_import(db=db, import_id=import_id)
        job = db.query(ImportJob).filter(ImportJob.import_id == import_id).first()
        return {
            "import_id": import_id,
            "status": job.status,
            "summary": counts
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{import_id}/errors")
def get_errors_and_warnings(
    import_id: str,
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get detailed row-level errors and warnings."""
    query = db.query(ValidationError).join(StagingRecord).filter(
        StagingRecord.import_id == import_id
    )
    if severity:
        query = query.filter(ValidationError.severity == severity.upper())

    errors = query.all()
    results = []
    for err in errors:
        st = err.staging_record_id
        st_rec = err.staging_record
        results.append({
            "validation_error_id": err.validation_error_id,
            "staging_record_id": err.staging_record_id,
            "source_file": st_rec.source_file if st_rec else None,
            "source_sheet": st_rec.source_sheet if st_rec else None,
            "source_row": st_rec.source_row if st_rec else None,
            "record_type": st_rec.record_type if st_rec else None,
            "source_record_id": st_rec.source_record_id if st_rec else None,
            "field_name": err.field_name,
            "error_code": err.error_code,
            "severity": err.severity,
            "message": err.message,
            "received_value": err.received_value
        })
    return results


@router.get("/{import_id}/errors/export")
def export_error_report(
    import_id: str,
    db: Session = Depends(get_db)
):
    """Downloadable CSV error report per RFC Section 9."""
    query = db.query(ValidationError).join(StagingRecord).filter(
        StagingRecord.import_id == import_id
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Error ID", "Staging Record ID", "Record Type", "Source File", "Sheet", "Row",
        "Source Identifier", "Field Name", "Error Code", "Severity", "Message", "Received Value"
    ])

    for err in query:
        st_rec = err.staging_record
        writer.writerow([
            err.validation_error_id,
            err.staging_record_id,
            st_rec.record_type if st_rec else "",
            st_rec.source_file if st_rec else "",
            st_rec.source_sheet if st_rec else "",
            st_rec.source_row if st_rec else "",
            st_rec.source_record_id if st_rec else "",
            err.field_name or "",
            err.error_code,
            err.severity,
            err.message,
            err.received_value or ""
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=validation_errors_{import_id}.csv"}
    )


@router.patch("/{import_id}/records/{record_id}")
def update_staged_record(
    import_id: str,
    record_id: str,
    payload: StagingRecordUpdateRequest,
    db: Session = Depends(get_db)
):
    """Correct a staged record and optionally re-mark as valid."""
    try:
        updated = StagingService.update_staged_record(
            db=db,
            staging_record_id=record_id,
            updated_normalised_payload=payload.normalised_payload,
            mark_as_valid=payload.mark_as_valid
        )
        # Rerun validation to refresh error list and reconciliation
        ValidationEngine.validate_import(db=db, import_id=import_id)
        return {
            "message": "Record updated and revalidated.",
            "staging_record_id": record_id,
            "processing_status": updated.processing_status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{import_id}/commit", response_model=CommitResponse)
def commit_import(
    import_id: str,
    req: CommitRequest,
    db: Session = Depends(get_db)
):
    """Explicitly commit eligible records to the canonical operational database."""
    try:
        res = CommitService.commit_import(
            db=db,
            import_id=import_id,
            commit_request=req,
            actor="user"
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{import_id}/cancel")
def cancel_import(
    import_id: str,
    db: Session = Depends(get_db)
):
    """Cancel an in-progress or draft import."""
    job = db.query(ImportJob).filter(ImportJob.import_id == import_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    if job.status in [ImportJobStatus.COMPLETED.value, ImportJobStatus.COMPLETED_WITH_REJECTIONS.value]:
        raise HTTPException(status_code=400, detail="Cannot cancel an already completed import.")

    job.status = ImportJobStatus.CANCELLED.value
    AuditService.log_event(
        db=db,
        import_id=import_id,
        event_type="IMPORT_CANCELLED",
        actor="user"
    )
    db.commit()
    return {"message": f"Import {import_id} has been cancelled."}


@router.get("/{import_id}/audit-logs", response_model=List[AuditEventResponse])
def get_audit_logs(
    import_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve audit history events for an import."""
    events = AuditService.get_events_for_import(db, import_id)
    return events
