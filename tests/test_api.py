from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["groq_model"] == "qwen-2.5-32b"

def test_sample_claims_endpoint():
    response = client.get("/api/v1/sample-claims")
    assert response.status_code == 200
    claims = response.json()
    assert len(claims) == 5

def test_validate_demo_endpoint():
    response = client.post("/api/v1/validate-demo/CLM-001")
    assert response.status_code == 200
    report = response.json()
    assert report["claim_id"] == "CLM-001"
    assert report["summary"]["overall_status"] == "FLAGGED_LEAKAGE"
    assert report["summary"]["calculated_leakage_prevented"] > 40000.0
