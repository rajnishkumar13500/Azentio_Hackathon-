import hashlib
import os
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.domain.enums import ImportJobStatus, SupportedFileFormat
from app.persistence.models.import_models import ImportJob, ImportFile
from app.ingestion.parsers.csv_parser import CSVParser
from app.ingestion.parsers.excel_parser import ExcelParser
from app.ingestion.parsers.json_parser import JSONParser
from app.ingestion.parsers.pdf_parser import PDFParser
from app.ingestion.parsers.image_parser import ImageParser
from app.ingestion.parsers.base import ParsedSourceRecord
from app.ingestion.staging_service import StagingService
from app.audit.audit_service import AuditService
from app.config import settings

class JobManager:
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def create_job(db: Session, source_type: str = "UPLOAD", created_by: str = "user") -> ImportJob:
        job = ImportJob(
            source_type=source_type,
            status=ImportJobStatus.CREATED.value,
            created_by=created_by,
            created_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        AuditService.log_event(
            db=db,
            import_id=job.import_id,
            event_type="JOB_CREATED",
            actor=created_by,
            event_details={"source_type": source_type}
        )
        return job

    @staticmethod
    def register_file(
        db: Session,
        import_id: str,
        filename: str,
        file_path: str,
        file_format: str
    ) -> ImportFile:
        file_hash = JobManager.calculate_file_hash(file_path)
        file_size = os.path.getsize(file_path)

        # Check for duplicate file upload
        existing_file = db.query(ImportFile).filter(
            ImportFile.file_hash == file_hash,
            ImportFile.import_id != import_id
        ).first()

        import_file = ImportFile(
            import_id=import_id,
            filename=filename,
            file_hash=file_hash,
            file_format=file_format.upper(),
            file_size=file_size,
            storage_path=file_path,
            uploaded_at=datetime.utcnow()
        )
        db.add(import_file)
        
        job = db.query(ImportJob).filter(ImportJob.import_id == import_id).first()
        if job:
            job.status = ImportJobStatus.FILES_UPLOADED.value
            if existing_file:
                AuditService.log_event(
                    db=db,
                    import_id=import_id,
                    event_type="DUPLICATE_FILE_DETECTED",
                    actor="system",
                    event_details={
                        "filename": filename,
                        "file_hash": file_hash,
                        "prior_import_id": existing_file.import_id
                    }
                )

        db.commit()
        db.refresh(import_file)
        return import_file

    @staticmethod
    def process_import_files(
        db: Session,
        import_id: str,
        field_mappings: Optional[Dict[str, str]] = None
    ) -> int:
        job = db.query(ImportJob).filter(ImportJob.import_id == import_id).first()
        if not job:
            raise ValueError(f"Job {import_id} not found")

        job.status = ImportJobStatus.PARSING.value
        db.commit()

        files = db.query(ImportFile).filter(ImportFile.import_id == import_id).all()
        total_staged = 0

        csv_parser = CSVParser()
        excel_parser = ExcelParser()
        json_parser = JSONParser()
        pdf_parser = PDFParser()
        image_parser = ImageParser()

        for f in files:
            fmt = f.file_format.upper()
            parsed_records: List[ParsedSourceRecord] = []

            if fmt == "CSV":
                res = csv_parser.parse(f.storage_path, f.filename)
                parsed_records = res.records
            elif fmt in ["XLSX", "EXCEL"]:
                res = excel_parser.parse(f.storage_path, f.filename)
                parsed_records = res.records
            elif fmt == "JSON":
                res = json_parser.parse(f.storage_path, f.filename)
                parsed_records = res.records
            elif fmt == "PDF":
                res = pdf_parser.parse(f.storage_path, f.filename)
                parsed_records = res.records
            elif fmt in ["PNG", "JPG", "JPEG", "IMAGE"]:
                res = image_parser.parse(f.storage_path, f.filename)
                parsed_records = res.records

            if parsed_records:
                staged = StagingService.stage_records(
                    db=db,
                    import_id=import_id,
                    parsed_records=parsed_records,
                    mapping_rules=field_mappings
                )
                total_staged += staged

        return total_staged
