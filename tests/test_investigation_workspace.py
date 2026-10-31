"""
Unit and Integration Tests for Claims Investigation Workspace (Level 2 Step 3).
"""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_investigation_workspace_payload():
    # Test comprehensive 360-degree workspace retrieval
    res = client.get("/api/v1/investigation/CLM-001/workspace")
    assert res.status_code == 200
    data = res.json()

    assert data["claim_id"] == "CLM-001"
    assert "original_claim" in data
    assert "policy_terms" in data
    assert data["policy_terms"]["policy_id"] == "POL-COMPREHENSIVE-01"
    assert data["policy_terms"]["sum_insured"] == 500000.0
    assert data["policy_terms"]["sub_limits"]["daily_room_rent"] == 5000.0

    assert "validation_report" in data
    assert "correlations" in data
    assert "document_evidence" in data
    assert "adjudication" in data
    assert "available_documents" in data
    assert len(data["available_documents"]) >= 2


def test_raw_supporting_document_retrieval():
    # Test verbatim document text retrieval for evidence inspection
    res = client.get("/api/v1/investigation/documents/hospital_tax_invoice_saket.txt")
    assert res.status_code == 200
    data = res.json()

    assert data["document_name"] == "hospital_tax_invoice_saket.txt"
    assert data["line_count"] > 10
    assert data["size_bytes"] > 100
    assert "MAX SUPER SPECIALITY HOSPITAL" in data["content"]
    assert "INV-MAX-2026-881" in data["content"]


def test_save_and_retrieve_working_notes():
    # 1. Save interim working note without closing claim
    note_payload = {
        "notes": "Reviewed hospital invoice Line 2. Surgeon fee billed ₹80k vs ₹70k verified on invoice. Contacting billing desk.",
        "adjudicated_by": "Senior Claims Investigator - Sharma"
    }
    save_res = client.post("/api/v1/investigation/CLM-001/notes", json=note_payload)
    assert save_res.status_code == 200
    save_data = save_res.json()
    assert save_data["status"] == "SUCCESS"
    assert save_data["adjudication"]["notes"] == note_payload["notes"]
    assert save_data["adjudication"]["adjudicated_by"] == note_payload["adjudicated_by"]

    # 2. Verify note persists in workspace
    ws_res = client.get("/api/v1/investigation/CLM-001/workspace")
    assert ws_res.status_code == 200
    ws_data = ws_res.json()
    assert ws_data["adjudication"]["notes"] == note_payload["notes"]
    assert ws_data["adjudication"]["adjudicated_by"] == note_payload["adjudicated_by"]
    assert ws_data["adjudication"]["timestamp"] is not None

    # 3. Verify note appears in adjudication report
    adj_res = client.get("/api/v1/claims/CLM-001/adjudicate")
    assert adj_res.status_code == 200
    adj_data = adj_res.json()
    assert adj_data["adjudication"]["notes"] == note_payload["notes"]

