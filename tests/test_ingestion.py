import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from src.main import app
from src.ingestion import ingestion_service
from src.config import settings

client = TestClient(app)

def test_ingest_clean_csv():
    csv_path = settings.DATA_DIR / "samples" / "sample_claims.csv"
    with open(csv_path, "rb") as f:
        content = f.read()
    result = ingestion_service.ingest_file("sample_claims.csv", content)

    assert result.success is True
    assert result.total_records == 2
    assert result.valid_records_count == 2
    assert len(result.errors) == 0
    assert result.claims[0].claim_id == "CLM-CSV-101"
    assert len(result.claims[0].line_items) == 3

def test_ingest_clean_excel():
    xlsx_path = settings.DATA_DIR / "samples" / "sample_claims.xlsx"
    with open(xlsx_path, "rb") as f:
        content = f.read()
    result = ingestion_service.ingest_file("sample_claims.xlsx", content)

    assert result.success is True
    assert result.total_records == 2
    assert len(result.claims) == 2
    assert len(result.errors) == 0

def test_ingest_synthetic_json():
    json_path = settings.SYNTHETIC_CLAIMS_FILE
    with open(json_path, "rb") as f:
        content = f.read()
    result = ingestion_service.ingest_file("synthetic_claims.json", content)

    assert result.success is True
    assert result.valid_records_count == 5
    assert len(result.errors) == 0

def test_ingest_invalid_records_not_silently_ignored():
    """
    Requirement 1: "It must validate identifiers, amounts, dates and mandatory fields,
    and must avoid silently ignoring invalid records."
    """
    inv_csv_path = settings.DATA_DIR / "samples" / "sample_invalid_claim.csv"
    with open(inv_csv_path, "rb") as f:
        content = f.read()
    result = ingestion_service.ingest_file("sample_invalid_claim.csv", content)

    # Must fail because records contain intentional violations
    assert result.success is False
    assert len(result.errors) > 0

    error_fields = [e.field_name for e in result.errors]
    # Check that reverse date was flagged
    assert any("date" in f.lower() for f in error_fields)
    # Check that negative unit price was flagged
    assert any("unit_price" in f.lower() for f in error_fields)

def test_api_upload_and_validate():
    csv_path = settings.DATA_DIR / "samples" / "sample_claims.csv"
    with open(csv_path, "rb") as f:
        files = {"file": ("sample_claims.csv", f, "text/csv")}
        response = client.post("/api/v1/ingest/upload-and-validate", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["ingestion_status"] == "SUCCESS"
    assert len(data["validation_reports"]) == 2
    # Verify report structure
    rep1 = data["validation_reports"][0]
    assert rep1["claim_id"] == "CLM-CSV-101"
    assert rep1["summary"]["total_claimed"] == 99000.0
