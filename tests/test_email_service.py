import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from src.main import app
from src.config import settings
from src.schemas import Claim, Policy
from src.engine import validation_engine
from src.email_service import email_service
from src.repository import claims_repository

client = TestClient(app)


def test_email_service_send_simulated_with_detailed_calculations():
    with open(settings.POLICIES_FILE, "r", encoding="utf-8") as f:
        policies_data = json.load(f)
    with open(settings.SYNTHETIC_CLAIMS_FILE, "r", encoding="utf-8") as f:
        claims_data = json.load(f)

    claim = Claim(**claims_data[0])  # CLM-001 (Comprehensive operational leakage)
    policy = Policy(**policies_data[claim.policy_id])
    report = validation_engine.validate_claim(claim, policy)

    res = email_service.send_settlement_report(
        claim=claim,
        policy=policy,
        report=report,
        adjudication={"notes": "Audited with room rent scaling and exclusions."},
        recipient_email="rohan.gupta@example.com",
        subject="Official Settlement Statement — CLM-001",
    )

    assert res["status"] == "SUCCESS"
    assert res["claim_id"] == claim.claim_id
    assert res["recipient_email"] == "rohan.gupta@example.com"
    assert res["dispatch_mode"] in ["SIMULATED", "LIVE_SMTP", "SIMULATED_FALLBACK"]
    assert "archive_path" in res

    # Verify that the generated email body contains detailed calculation waterfall and proofs
    archive_path = Path(res["archive_path"])
    assert archive_path.exists()
    with open(archive_path, "r", encoding="utf-8") as f:
        email_content = f.read()

    # Calculation details
    assert "Policy Settlement Financial Calculation Waterfall" in email_content
    assert "Gross Invoiced Amount" in email_content
    assert "Net Calculated Payable Settlement" in email_content
    assert "Daily Room Rent Limit Breach" in email_content
    assert "Proportionate Cascade" in email_content
    assert "Regulatory Excluded Consumables" in email_content
    assert "Contractual Policy Deductible" in email_content
    assert "Mandatory Co-Payment" in email_content
    # Itemized lines
    assert "Line-Level Bill Itemization & Disallowance Audit" in email_content
    assert "Single Deluxe Private Room" in email_content
    # Step 4 proof
    assert "STEP 4: ROOM RENT LIMIT BREACH PROOF" in email_content


def test_email_dispatch_api_endpoint():
    # 1. Seed demo batch to ensure claim CLM-001 is present
    seed_res = client.post("/api/v1/claims/seed-demo")
    assert seed_res.status_code == 200

    # 2. Call send-email endpoint
    payload = {
        "recipient_email": "rohan.gupta@example.com",
        "recipient_name": "Rohan Gupta",
        "subject": "Official Settlement for CLM-001",
        "notes": "Approved with proportionate room deductions."
    }
    res = client.post("/api/v1/claims/CLM-001/send-email", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["claim_id"] == "CLM-001"
    assert data["recipient_email"] == "rohan.gupta@example.com"

    # 3. Check email history endpoint
    hist_res = client.get("/api/v1/claims/CLM-001/email-history")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert len(hist) >= 1
    assert hist[0]["claim_id"] == "CLM-001"
    assert hist[0]["recipient_email"] == "rohan.gupta@example.com"
