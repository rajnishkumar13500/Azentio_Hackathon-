from pathlib import Path
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
    assert data.get("canonical_ingestion_available") is True


def test_studio_dashboard_routes_are_unchanged():
    studio_claims = client.get("/api/v1/claims")
    assert studio_claims.status_code == 200
    assert "total_claims" in studio_claims.json()
    assert "portfolio_metrics" in studio_claims.json()

    ui = client.get("/")
    assert ui.status_code == 200
    assert "Claims Leakage Detection Studio" in ui.text
    assert "streamlit" not in ui.text.lower()

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

def test_investigation_correlation_endpoints():
    # 1. Seed correlation benchmark dataset
    seed_res = client.post("/api/v1/investigation/seed-correlation-dataset")
    assert seed_res.status_code == 200
    assert seed_res.json()["count"] >= 10

    # 2. Query correlations for double dipping target
    corr_res = client.get("/api/v1/investigation/CLM-CORR-001/correlations")
    assert corr_res.status_code == 200
    report = corr_res.json()
    assert report["claim_id"] == "CLM-CORR-001"
    assert report["total_correlated_claims"] >= 1
    assert report["highest_severity"] == "CRITICAL"
    assert len(report["network_nodes"]) >= 5
    assert len(report["network_edges"]) >= 4

    # 3. Query all portfolio correlations
    all_corr_res = client.get("/api/v1/investigation/correlations/all")
    assert all_corr_res.status_code == 200
    all_data = all_corr_res.json()
    assert all_data["total_flagged_with_correlations"] >= 1

def test_document_analysis_endpoints():
    # 1. Test pre-linked supporting document evidence endpoint
    doc_res = client.get("/api/v1/investigation/CLM-001/document-evidence")
    assert doc_res.status_code == 200
    data = doc_res.json()
    assert data["claim_id"] == "CLM-001"
    assert "total_variances_detected" in data
    assert "field_comparisons" in data
    assert "line_item_reconciliations" in data

    # 2. Test document upload comparison endpoint
    sample_invoice = Path("data/jury_examples/Step_2_Document_Analysis/hospital_tax_invoice_saket.txt")
    with open(sample_invoice, "rb") as f:
        upload_res = client.post(
            "/api/v1/investigation/CLM-001/compare-document",
            files={"file": ("hospital_tax_invoice_saket.txt", f, "text/plain")},
        )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["total_variances_detected"] >= 1
    assert len(upload_data["line_item_reconciliations"]) >= 1

def test_canonical_sample_lands_in_existing_studio_portfolio():
    res = client.post("/api/v1/ingest/canonical-sample?dataset_name=small")
    assert res.status_code == 200
    data = res.json()
    assert data["ingestion_status"] in ("SUCCESS", "PARTIAL_SUCCESS")
    assert data["ingestion_result"]["valid_records_count"] >= 1
    assert len(data["validation_reports"]) >= 1

    studio = client.get("/api/v1/claims/CLM-1001")
    assert studio.status_code == 200
    assert studio.json()["claim_id"] == "CLM-1001"
