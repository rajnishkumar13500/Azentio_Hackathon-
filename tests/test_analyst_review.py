"""
Unit and Integration Tests for Level 2 Step 4 & Step 5:
- Recommended Settlement Corrections
- Analyst Review and Escalation (all 5 decisions)
- Mandatory reason for False Positives
- Escalation to Senior Reviewer / SIU
- Recalculation of net adjusted settlement
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_recommended_settlement_corrections():
    """
    Step 4: Verify specific settlement adjustments rather than generic warnings:
    original amount, corrected amount, calculation, and policy rule.
    """
    res = client.get("/api/v1/investigation/CLM-001/corrections")
    assert res.status_code == 200
    corrections = res.json()
    assert len(corrections) >= 1

    first = corrections[0]
    assert "correction_id" in first
    assert "finding_id" in first
    assert "original_amount" in first
    assert "corrected_amount" in first
    assert "calculation_formula" in first
    assert "policy_rule_or_evidence" in first
    assert first["adjustment_amount"] > 0


def test_analyst_decision_confirm_discrepancy():
    """Step 5 Decision 1: Confirm Discrepancy."""
    payload = {
        "finding_id": "line_1",
        "finding_type": "LINE_ITEM",
        "decision": "CONFIRM_DISCREPANCY",
        "reason": "Audited against hospital bill; consumable charges non-admissible.",
        "analyst_id": "Senior Auditor - Verma"
    }
    res = client.post("/api/v1/investigation/CLM-001/decision", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["finding_id"] == "line_1"
    assert data["decision"] == "CONFIRM_DISCREPANCY"


def test_analyst_decision_false_positive_requires_reason():
    """Step 5 Decision 2: Mark as False Positive requires a mandatory reason."""
    # 1. Missing reason must fail with 400
    bad_payload = {
        "finding_id": "line_2",
        "finding_type": "LINE_ITEM",
        "decision": "MARK_FALSE_POSITIVE",
        "reason": ""  # Empty
    }
    res = client.post("/api/v1/investigation/CLM-001/decision", json=bad_payload)
    assert res.status_code == 400
    assert "reason" in res.json()["detail"].lower()

    # 2. Valid reason must succeed
    valid_payload = {
        "finding_id": "line_2",
        "finding_type": "LINE_ITEM",
        "decision": "MARK_FALSE_POSITIVE",
        "reason": "Surgeon provided operative note confirming emergency off-hours complexity."
    }
    res = client.post("/api/v1/investigation/CLM-001/decision", json=valid_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "MARK_FALSE_POSITIVE"
    assert data["adjusted_leakage"] == 0.0


def test_analyst_decision_request_additional_evidence():
    """Step 5 Decision 3: Request Additional Evidence."""
    payload = {
        "finding_id": "line_3",
        "finding_type": "LINE_ITEM",
        "decision": "REQUEST_ADDITIONAL_EVIDENCE",
        "reason": "Request itemized pharmacy batch bills for intravenous antibiotics."
    }
    res = client.post("/api/v1/investigation/CLM-001/decision", json=payload)
    assert res.status_code == 200
    assert res.json()["decision"] == "REQUEST_ADDITIONAL_EVIDENCE"


def test_analyst_decision_escalate_to_siu():
    """Step 5 Decision 4: Escalate to Special Investigation Unit (SIU)."""
    payload = {
        "finding_id": "rule_SEC_2_1_ROOM_CAP",
        "finding_type": "RULE_VIOLATION",
        "decision": "ESCALATE",
        "escalation_target": "SPECIAL_INVESTIGATION_UNIT",
        "reason": "Suspected provider systematic unbundling across multiple claims."
    }
    res = client.post("/api/v1/investigation/CLM-001/decision", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "ESCALATE"
    assert data["escalation_target"] == "SPECIAL_INVESTIGATION_UNIT"


def test_analyst_decision_accept_recommended_correction():
    """Step 5 Decision 5: Accept the Recommended Correction."""
    payload = {
        "finding_id": "line_4",
        "finding_type": "LINE_ITEM",
        "decision": "ACCEPT_CORRECTION",
        "reason": "Accepted capping at procedure benchmark schedule."
    }
    res = client.post("/api/v1/investigation/CLM-001/decision", json=payload)
    assert res.status_code == 200
    assert res.json()["decision"] == "ACCEPT_CORRECTION"


def test_analyst_investigation_report_and_workspace():
    """
    Step 5: Test structured Analyst Investigation Report endpoint
    and verify integration with 360-degree workspace.
    """
    res = client.get("/api/v1/investigation/CLM-001/analyst-report")
    assert res.status_code == 200
    report = res.json()

    assert report["claim_id"] == "CLM-001"
    assert report["total_findings"] >= 1
    assert report["total_reviewed"] >= 3
    assert report["escalation_status"] == "SIU_ESCALATED"  # From previous test
    assert "decisions_breakdown" in report
    assert report["decisions_breakdown"]["CONFIRM_DISCREPANCY"] >= 1
    assert report["decisions_breakdown"]["MARK_FALSE_POSITIVE"] >= 1
    assert report["decisions_breakdown"]["ESCALATE"] >= 1
    assert report["decisions_breakdown"]["ACCEPT_CORRECTION"] >= 1

    # Verify workspace contains report and decisions
    ws_res = client.get("/api/v1/investigation/CLM-001/workspace")
    assert ws_res.status_code == 200
    ws_data = ws_res.json()
    assert "corrections" in ws_data
    assert "analyst_report" in ws_data
    assert "decisions" in ws_data
    assert len(ws_data["decisions"]) >= 3

