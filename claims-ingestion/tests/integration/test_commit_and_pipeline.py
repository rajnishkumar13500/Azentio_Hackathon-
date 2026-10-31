import os
import shutil
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.persistence.database import Base
from app.persistence.models import *
from app.ingestion.job_manager import JobManager
from app.validation.engine import ValidationEngine
from app.persistence.commit_service import CommitService
from app.domain.schemas.import_schemas import CommitRequest
from app.config import settings

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()

def test_full_ingestion_and_commit_pipeline(test_db):
    # 1. Create Job
    job = JobManager.create_job(db=test_db, source_type="TEST_PIPELINE", created_by="test_suite")
    assert job.status == "CREATED"

    # 2. Copy and register files from sample_data/small
    sample_dir = os.path.join(settings.SAMPLE_DATA_DIR, "small")
    temp_upload = os.path.join(settings.STORAGE_DIR, "uploads", job.import_id)
    os.makedirs(temp_upload, exist_ok=True)

    for item in os.listdir(sample_dir):
        src = os.path.join(sample_dir, item)
        if os.path.isfile(src):
            dst = os.path.join(temp_upload, item)
            shutil.copy2(src, dst)
            ext = os.path.splitext(item)[1].lower().replace(".", "").upper()
            if ext in ["JPG", "JPEG", "PNG"]:
                ext = "IMAGE"
            JobManager.register_file(test_db, job.import_id, item, dst, ext)

    # 3. Process files into staging
    staged = JobManager.process_import_files(test_db, job.import_id)
    assert staged > 0

    # 4. Run validation
    counts = ValidationEngine.validate_import(test_db, job.import_id)
    assert counts["valid"] > 0
    assert counts["invalid"] > 0  # Planted errors caught!
    assert counts["skipped"] > 0  # Blank row caught!

    # Verify reconciliation equation: parsed = valid + warning + invalid + duplicate + pending_review + skipped
    total_reconciled = (
        job.valid_records +
        job.warning_records +
        job.invalid_records +
        job.duplicate_records +
        job.pending_review_records +
        job.explicitly_skipped_records
    )
    assert total_reconciled == job.parsed_records

    # 5. Commit eligible records
    req = CommitRequest(
        confirm=True,
        include_valid=True,
        include_reviewed_warnings=True,
        acknowledged_warning_count=job.warning_records
    )
    res = CommitService.commit_import(
        db=test_db,
        import_id=job.import_id,
        commit_request=req,
        actor="test_runner"
    )

    assert res.imported_records > 0
    assert job.status in ["COMPLETED", "COMPLETED_WITH_REJECTIONS"]

    # Verify invalid records were NOT imported
    claims_in_db = test_db.query(Claim).all()
    assert any(c.claim_id == "CLM-1001" for c in claims_in_db)
    # CLM-1004 had missing claimant name, CLM-1005 had negative amount: neither should be imported!
    assert not any(c.claim_id == "CLM-1004" for c in claims_in_db)
    assert not any(c.claim_id == "CLM-1005" for c in claims_in_db)

    # 6. Idempotency test: repeating commit should return same summary without duplicating
    res_repeat = CommitService.commit_import(
        db=test_db,
        import_id=job.import_id,
        commit_request=req,
        actor="test_runner"
    )
    assert res_repeat.imported_records == res.imported_records
    assert len(test_db.query(Claim).filter(Claim.claim_id == "CLM-1001").all()) == 1
