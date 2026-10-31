from fastapi.testclient import TestClient
from src.main import app
from src.config import settings

client = TestClient(app)

def test_ui_index_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Claims Leakage Detection Studio" in response.text

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["groq_model"] == settings.GROQ_MODEL

def test_portfolio_lifecycle_empty_and_seed():
    # 1. Clear portfolio
    del_res = client.delete("/api/v1/claims")
    assert del_res.status_code == 200

    # 2. Verify empty state
    res = client.get("/api/v1/claims")
    assert res.status_code == 200
    data = res.json()
    assert data["total_claims"] == 0
    assert len(data["claims"]) == 0

    # 3. Seed demo claims
    seed_res = client.post("/api/v1/claims/seed-demo")
    assert seed_res.status_code == 200
    assert seed_res.json()["count"] >= 5

    # 4. Verify populated portfolio
    res2 = client.get("/api/v1/claims")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total_claims"] >= 5
    assert data2["portfolio_metrics"]["total_invoiced"] > 0
    assert data2["portfolio_metrics"]["total_prevented_leakage"] > 0

    # 5. Adjudicate single claim with claim_history
    adj_res = client.get("/api/v1/claims/CLM-001/adjudicate")
    assert adj_res.status_code == 200
    rep = adj_res.json()
    assert rep["claim_id"] == "CLM-001"
    assert rep["summary"]["overall_status"] == "FLAGGED_LEAKAGE"

    # 6. Customer Settlement Report Download & Preview
    rep_res = client.get("/api/v1/claims/CLM-001/report?download=true")
    assert rep_res.status_code == 200
    assert "attachment" in rep_res.headers.get("content-disposition", "")
    assert "Explanation of Benefits" in rep_res.text
    assert "Azentio" in rep_res.text

def test_v1_models_discovery():
    res = client.get("/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "list"
    assert len(data["data"]) > 0
    model_ids = [m["id"] for m in data["data"]]
    assert settings.GROQ_MODEL in model_ids

    # Test single model retrieval
    single_res = client.get(f"/v1/models/{settings.GROQ_MODEL}")
    assert single_res.status_code == 200
    single_data = single_res.json()
    assert single_data["id"] == settings.GROQ_MODEL

def test_v1_chat_completions():
    res = client.post(
        "/v1/chat/completions",
        json={
            "model": settings.GROQ_MODEL,
            "messages": [{"role": "user", "content": "Analyze claim discrepancy for disposable syringes"}],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "message" in data["choices"][0]
    assert data["choices"][0]["message"]["role"] == "assistant"
