import sys
import json
import time
import logging
import argparse
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.config import settings
from src.schemas import Claim, Policy, ValidationReport
from src.engine import validation_engine
from src.ingestion import ingestion_service, IngestionResult
from src.ingestion.canonical_ingest import (
    canonical_pipeline_available,
    ingest_bytes_via_canonical,
    ingest_sample_dataset_via_canonical,
    looks_like_canonical_payload,
)
from src.repository import claims_repository
from src.report_generator import generate_customer_report_html
from src.email_service import email_service
from src.ai.groq_client import groq_agent

logger = logging.getLogger(__name__)
console = Console()

# In-memory adjudication decision store
_adjudications: Dict[str, Dict[str, Any]] = {}

class SendEmailReportRequest(BaseModel):
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    notes: Optional[str] = None

class AdjudicationActionRequest(BaseModel):
    claim_id: str
    action: str  # CONFIRM_DENIAL, ADJUST_AMOUNT, DISMISS_FALSE_POSITIVE
    adjudicated_by: Optional[str] = "Adjudicator"
    adjusted_amount: Optional[float] = None
    notes: Optional[str] = None

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Microservice for Insurance Claims Policy Validation & Financial Leakage Prevention",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_data():
    with open(settings.POLICIES_FILE, "r", encoding="utf-8") as f:
        policies_data = json.load(f)
    with open(settings.SYNTHETIC_CLAIMS_FILE, "r", encoding="utf-8") as f:
        claims_data = json.load(f)
    return policies_data, claims_data

@app.get("/", include_in_schema=False)
def serve_ui():
    index_path = settings.STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Claims Policy Validation Microservice is Running"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "groq_configured": bool(settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your_")),
        "groq_model": settings.GROQ_MODEL,
        "canonical_ingestion_available": canonical_pipeline_available(),
    }

def get_available_models() -> List[Dict[str, Any]]:
    default_models = [
        {"id": settings.GROQ_MODEL, "object": "model", "created": 1700000000, "owned_by": "groq"},
        {"id": "llama-3.3-70b-versatile", "object": "model", "created": 1700000000, "owned_by": "groq"},
        {"id": "llama-3.1-8b-instant", "object": "model", "created": 1700000000, "owned_by": "groq"},
        {"id": "mixtral-8x7b-32768", "object": "model", "created": 1700000000, "owned_by": "groq"},
        {"id": "emilyalsentzer/Bio_ClinicalBERT", "object": "model", "created": 1700000000, "owned_by": "azentio-ai"},
        {"id": "all-MiniLM-L6-v2", "object": "model", "created": 1700000000, "owned_by": "azentio-ai"},
    ]
    if groq_agent.is_available:
        try:
            live_models = groq_agent.client.models.list()
            if hasattr(live_models, "data") and live_models.data:
                return [
                    {
                        "id": m.id,
                        "object": "model",
                        "created": getattr(m, "created", 1700000000),
                        "owned_by": getattr(m, "owned_by", "groq"),
                    }
                    for m in live_models.data
                ]
        except Exception:
            pass
    return default_models

@app.get("/v1/models")
@app.get("/models")
def list_models():
    """OpenAI-compatible models list endpoint for agent and client discovery."""
    return {
        "object": "list",
        "data": get_available_models(),
    }

@app.get("/v1/models/{model_id:path}")
@app.get("/models/{model_id:path}")
def get_model(model_id: str):
    """OpenAI-compatible model detail endpoint."""
    return {
        "id": model_id,
        "object": "model",
        "created": 1700000000,
        "owned_by": "azentio-ai",
        "permission": [],
        "root": model_id,
        "parent": None,
    }

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(req: Request):
    """
    OpenAI-compatible chat completions endpoint.
    Seamlessly routes agent requests to Groq or deterministic auditor fallback.
    """
    try:
        body = await req.json()
    except Exception:
        body = {}

    messages = body.get("messages", [])
    model = body.get("model", settings.GROQ_MODEL)
    temperature = body.get("temperature", 0.2)
    max_tokens = body.get("max_tokens", 1024)

    if groq_agent.is_available:
        try:
            response = groq_agent.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return json.loads(response.model_dump_json())
        except Exception as e:
            logger.warning(f"Groq chat completion fallback: {e}")

    # Fallback response for offline mode or test harnesses
    last_user_msg = "Hello"
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    return {
        "id": f"chatcmpl-azentio-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"Azentio.ai Claims Agent: Received message: '{last_user_msg[:80]}'. The claims validation microservice and duplicate detector are active.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(str(messages)),
            "completion_tokens": 30,
            "total_tokens": len(str(messages)) + 30,
        },
    }

@app.get("/api/v1/sample-policies")
def get_sample_policies():
    policies_data, _ = load_data()
    return policies_data

@app.get("/api/v1/sample-claims")
def get_sample_claims():
    _, claims_data = load_data()
    return claims_data

@app.post("/api/v1/validate", response_model=ValidationReport)
def validate_claim_endpoint(claim: Claim, policy: Optional[Policy] = None):
    if not policy:
        policies_data, _ = load_data()
        if claim.policy_id not in policies_data:
            raise HTTPException(
                status_code=404, detail=f"Policy '{claim.policy_id}' not found in registry."
            )
        policy = Policy(**policies_data[claim.policy_id])
    return validation_engine.validate_claim(claim, policy)

@app.post("/api/v1/validate-demo/{claim_id}", response_model=ValidationReport)
def validate_demo_claim(claim_id: str):
    policies_data, claims_data = load_data()
    matched_claim = next((c for c in claims_data if c["claim_id"] == claim_id), None)
    if not matched_claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found in demo suite.")
    claim = Claim(**matched_claim)
    policy = Policy(**policies_data[claim.policy_id])
    return validation_engine.validate_claim(claim, policy)

@app.get("/api/v1/claims")
@app.get("/api/claims")
def get_portfolio_dashboard():
    """
    Returns active claims in the portfolio dashboard with their computed validation status,
    duplicate detection findings, and adjudication state.
    """
    claims = claims_repository.get_all()
    policies_data, _ = load_data()

    total_invoiced = 0.0
    total_prevented_leakage = 0.0
    total_suspected_leakage = 0.0
    flagged_count = 0
    rejected_count = 0
    approved_count = 0

    claims_with_summary = []
    for c in claims:
        policy_dict = policies_data.get(c.policy_id, policies_data.get("POL-COMPREHENSIVE-01"))
        policy = Policy(**policy_dict)
        report = validation_engine.validate_claim(c, policy)
        s = report.summary

        total_invoiced += s.total_claimed
        total_prevented_leakage += s.calculated_leakage_prevented
        total_suspected_leakage += s.suspected_leakage_total

        if s.overall_status == "REJECTED":
            rejected_count += 1
        elif s.overall_status == "FLAGGED_LEAKAGE":
            flagged_count += 1
        else:
            approved_count += 1

        adj = _adjudications.get(c.claim_id, {
            "status": "PENDING_REVIEW" if s.overall_status in ["REJECTED", "FLAGGED_LEAKAGE"] else "AUTO_APPROVED",
            "adjudicated_by": None,
            "adjusted_amount": None,
            "notes": None,
            "timestamp": None
        })

        claims_with_summary.append({
            "claim": c,
            "summary": s,
            "validation_report": report,
            "duplicate_findings": report.duplicate_findings,
            "adjudication": adj,
            "top_recommendation": report.recommendations[0] if report.recommendations else None,
        })

    return {
        "total_claims": len(claims),
        "portfolio_metrics": {
            "total_invoiced": round(total_invoiced, 2),
            "total_prevented_leakage": round(total_prevented_leakage, 2),
            "total_suspected_leakage": round(total_suspected_leakage, 2),
            "flagged_count": flagged_count,
            "rejected_count": rejected_count,
            "approved_count": approved_count,
        },
        "claims": claims_with_summary,
    }

@app.get("/api/v1/kpis")
@app.get("/api/kpis")
def get_executive_kpis():
    """Returns aggregated executive metrics, category breakdowns, and provider distributions."""
    data = get_portfolio_dashboard()
    total_claims = data["total_claims"]
    metrics = data["portfolio_metrics"]
    claims_list = data["claims"]

    flagged_count = metrics["flagged_count"] + metrics["rejected_count"]
    total_amount = metrics["total_invoiced"]
    calc_leakage = metrics["total_prevented_leakage"]
    susp_leakage = metrics["total_suspected_leakage"]
    overall_leakage = round(calc_leakage + susp_leakage, 2)

    categories: Dict[str, float] = {}
    severities: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "CLEAN": 0}
    providers: Dict[str, Dict[str, Any]] = {}

    for item in claims_list:
        c = item["claim"]
        s = item["summary"]
        report = item["validation_report"]
        findings = item.get("duplicate_findings", [])

        # Leakage by category
        if findings:
            for f in findings:
                scen = f.get("scenario_type", "DUPLICATE")
                amt = f.get("leakage_amount", 0.0)
                categories[scen] = round(categories.get(scen, 0.0) + amt, 2)
        if s.total_sublimit_deduction > 0:
            categories["ROOM_RENT_LIMIT_BREACH"] = round(categories.get("ROOM_RENT_LIMIT_BREACH", 0.0) + s.total_sublimit_deduction, 2)
        if s.total_excluded > 0:
            categories["NON_PAYABLE_CONSUMABLES"] = round(categories.get("NON_PAYABLE_CONSUMABLES", 0.0) + s.total_excluded, 2)
        if s.total_proportionate_deduction > 0:
            categories["PROPORTIONATE_DEDUCTION"] = round(categories.get("PROPORTIONATE_DEDUCTION", 0.0) + s.total_proportionate_deduction, 2)
        if s.deductible_applied > 0 or s.copay_applied > 0:
            categories["DEDUCTIBLE_COPAY"] = round(categories.get("DEDUCTIBLE_COPAY", 0.0) + s.deductible_applied + s.copay_applied, 2)

        # Severity
        if s.overall_status == "REJECTED":
            severities["CRITICAL"] += 1
        elif s.calculated_leakage_prevented > 20000:
            severities["HIGH"] += 1
        elif s.calculated_leakage_prevented > 0 or s.suspected_leakage_total > 0:
            severities["MEDIUM"] += 1
        else:
            severities["CLEAN"] += 1

        # Provider breakdown
        p_name = c.incident_details.hospital_name or c.incident_details.hospital_id
        providers.setdefault(p_name, {"claims": 0, "leakage": 0.0, "total_billed": 0.0})
        providers[p_name]["claims"] += 1
        providers[p_name]["leakage"] = round(providers[p_name]["leakage"] + s.calculated_leakage_prevented + s.suspected_leakage_total, 2)
        providers[p_name]["total_billed"] = round(providers[p_name]["total_billed"] + s.total_claimed, 2)

    return {
        "total_claims_processed": total_claims,
        "total_claimed_amount": total_amount,
        "flagged_claims_count": flagged_count,
        "flag_rate_percentage": round((flagged_count / total_claims * 100), 1) if total_claims else 0.0,
        "total_calculated_leakage": calc_leakage,
        "total_suspected_leakage": susp_leakage,
        "overall_leakage_exposure": overall_leakage,
        "potential_savings_rate": round((overall_leakage / total_amount * 100), 1) if total_amount else 0.0,
        "leakage_by_category": categories,
        "severity_distribution": severities,
        "provider_breakdown": providers,
    }

@app.post("/api/v1/action")
@app.post("/api/action")
def record_adjudicator_action(req: AdjudicationActionRequest):
    """Records an adjudicator's decision (CONFIRM_DENIAL, ADJUST_AMOUNT, DISMISS_FALSE_POSITIVE)."""
    claim = claims_repository.get_by_id(req.claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{req.claim_id}' not found.")

    _adjudications[req.claim_id] = {
        "status": req.action,
        "adjudicated_by": req.adjudicated_by or "Adjudicator",
        "adjusted_amount": req.adjusted_amount,
        "notes": req.notes,
        "timestamp": datetime.utcnow().isoformat()
    }
    return {
        "status": "SUCCESS",
        "claim_id": req.claim_id,
        "action": req.action,
        "message": f"Claim {req.claim_id} updated to {req.action}"
    }

@app.get("/api/v1/claims/{claim_id}")
def get_claim_by_id(claim_id: str):
    claim = claims_repository.get_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found in portfolio.")
    return claim

@app.get("/api/v1/claims/{claim_id}/adjudicate", response_model=ValidationReport)
def adjudicate_claim(claim_id: str):
    claim = claims_repository.get_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found in portfolio.")
    policies_data, _ = load_data()
    policy_dict = policies_data.get(claim.policy_id, policies_data.get("POL-COMPREHENSIVE-01"))
    policy = Policy(**policy_dict)
    return validation_engine.validate_claim(claim, policy)

@app.get("/api/v1/claims/{claim_id}/report")
@app.get("/api/claims/{claim_id}/report")
def get_customer_report_endpoint(claim_id: str, download: bool = False):
    """
    Generates and returns an official customer settlement report / Explanation of Benefits (EOB).
    If download=true, sends Content-Disposition attachment header to save directly to disk.
    """
    claim = claims_repository.get_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found in portfolio.")
    policies_data, _ = load_data()
    policy_dict = policies_data.get(claim.policy_id, policies_data.get("POL-COMPREHENSIVE-01"))
    policy = Policy(**policy_dict)
    report = validation_engine.validate_claim(claim, policy)
    adjudication = _adjudications.get(claim_id, {})

    html_content = generate_customer_report_html(claim, policy, report, adjudication)
    headers = {"Content-Type": "text/html; charset=utf-8"}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="Azentio_Settlement_Report_{claim_id}.html"'

    return Response(content=html_content, media_type="text/html", headers=headers)

@app.post("/api/v1/claims/{claim_id}/send-email")
@app.post("/api/claims/{claim_id}/send-email")
def send_email_report_endpoint(claim_id: str, req: Optional[SendEmailReportRequest] = None):
    claim = claims_repository.get_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found in portfolio.")
    policies_data, _ = load_data()
    policy_dict = policies_data.get(claim.policy_id, policies_data.get("POL-COMPREHENSIVE-01"))
    policy = Policy(**policy_dict)
    report = validation_engine.validate_claim(claim, policy)
    adjudication = _adjudications.get(claim_id, {})

    payload = req or SendEmailReportRequest()
    return email_service.send_settlement_report(
        claim=claim,
        policy=policy,
        report=report,
        adjudication=adjudication,
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        auditor_notes=payload.notes,
    )

@app.get("/api/v1/claims/{claim_id}/email-history")
@app.get("/api/claims/{claim_id}/email-history")
def get_email_history_endpoint(claim_id: str):
    claim = claims_repository.get_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found in portfolio.")
    return email_service.get_email_history_for_claim(claim_id)

@app.post("/api/v1/claims/seed-demo")
def seed_demo_claims():
    """Populates the portfolio with the 5 pre-configured hackathon demo cases."""
    loaded = claims_repository.seed_demo_batch()
    return {"message": f"Successfully loaded {len(loaded)} demo claims into portfolio.", "count": len(loaded)}

@app.delete("/api/v1/claims")
def clear_portfolio_claims():
    """Resets the dashboard to empty state."""
    claims_repository.clear()
    return {"message": "Portfolio cleared. Ready for fresh file upload."}

def _ingest_uploaded_bytes(filename: str, content: bytes) -> IngestionResult:
    """
    Route an upload to the existing studio parser, or to the canonical
    claims-ingestion backend when the payload matches that schema / document types.

    Standalone hospital bills (PDF/PNG/JPG) always try the studio document parser
    first so they become portfolio claims instead of canonical invoice rows.
    """
    ext = Path(filename or "").suffix.lower().lstrip(".")
    if ext in {"pdf", "png", "jpg", "jpeg"}:
        studio_result = ingestion_service.ingest_file(filename, content)
        if studio_result.claims:
            return studio_result
        if canonical_pipeline_available():
            canonical_result = ingest_bytes_via_canonical(filename, content)
            if canonical_result.claims:
                return canonical_result
        return studio_result

    if looks_like_canonical_payload(filename, content) and canonical_pipeline_available():
        return ingest_bytes_via_canonical(filename, content)
    return ingestion_service.ingest_file(filename, content)


def _validate_ingested_claims(result: IngestionResult) -> dict:
    if not result.success and len(result.claims) == 0:
        return {
            "ingestion_status": "FAILED",
            "ingestion_result": result,
            "validation_reports": [],
        }

    if result.claims:
        claims_repository.add_claims(result.claims)

    policies_data, _ = load_data()
    validation_reports: List[ValidationReport] = []
    for claim in result.claims:
        if claim.policy_id not in policies_data:
            policy = Policy(**policies_data.get("POL-COMPREHENSIVE-01"))
        else:
            policy = Policy(**policies_data[claim.policy_id])
        validation_reports.append(validation_engine.validate_claim(claim, policy))

    return {
        "ingestion_status": "SUCCESS" if result.success else "PARTIAL_SUCCESS",
        "ingestion_result": result,
        "validation_reports": validation_reports,
    }


@app.post("/api/v1/ingest/upload", response_model=IngestionResult)
async def upload_claims_file(file: UploadFile = File(...)):
    """
    Ingests and validates claims data across CSV, Excel (.xlsx), JSON, documents,
    and canonical pipeline formats (PDF/images and operational CSV/JSON bundles).
    Persists valid claims into the active portfolio.
    """
    content = await file.read()
    result = _ingest_uploaded_bytes(file.filename, content)
    if result.claims:
        claims_repository.add_claims(result.claims)
    return result

@app.post("/api/v1/ingest/upload-and-validate")
async def upload_and_validate(file: UploadFile = File(...)):
    """
    Full pipeline: Ingests file -> Validates data integrity -> Persists claims -> Runs policy rule engine.
    """
    content = await file.read()
    result = _ingest_uploaded_bytes(file.filename, content)
    return _validate_ingested_claims(result)


@app.post("/api/v1/ingest/canonical-sample")
def ingest_canonical_sample(dataset_name: str = "small"):
    """
    Runs the claims-ingestion backend sample dataset (no Streamlit UI) and
    loads committed claims into the existing studio portfolio + policy engine.
    """
    if not canonical_pipeline_available():
        raise HTTPException(status_code=503, detail="Canonical ingestion backend is not available.")
    try:
        result = ingest_sample_dataset_via_canonical(dataset_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _validate_ingested_claims(result)

@app.get("/api/v1/ingest/samples/{file_format}")
def download_sample_file(file_format: str):
    samples_dir = settings.DATA_DIR / "samples"
    mapping = {
        "csv": ("sample_claims.csv", "text/csv"),
        "xlsx": ("sample_claims.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "txt": ("sample_hospital_invoice.txt", "text/plain"),
        "invalid": ("sample_invalid_claim.csv", "text/csv"),
    }
    fmt = file_format.lower()
    if fmt not in mapping:
        raise HTTPException(status_code=404, detail=f"Sample format '{fmt}' not found. Supported: csv, xlsx, txt, invalid.")

    filename, media_type = mapping[fmt]
    file_path = samples_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Sample file missing from disk.")
    return FileResponse(file_path, media_type=media_type, filename=filename)

def run_cli_demo():
    policies_data, claims_data = load_data()

    console.print(
        Panel.fit(
            f"[bold cyan]{settings.PROJECT_NAME}[/bold cyan]\n"
            f"[dim]Azentio Hackathon - Financial Leakage Prevention Engine[/dim]\n"
            f"[yellow]Groq Model:[/yellow] {settings.GROQ_MODEL} | "
            f"[yellow]Groq Configured:[/yellow] {'Yes' if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith('your_') else 'No (Deterministic fallback active)'}",
            title="Policy Validation Microservice",
            border_style="cyan",
        )
    )

    total_processed_amount = 0.0
    total_prevented_leakage = 0.0
    total_suspected_leakage = 0.0

    for raw_claim in claims_data:
        claim = Claim(**raw_claim)
        policy = Policy(**policies_data[claim.policy_id])
        report = validation_engine.validate_claim(claim, policy)
        s = report.summary

        total_processed_amount += s.total_claimed
        total_prevented_leakage += s.calculated_leakage_prevented
        total_suspected_leakage += s.suspected_leakage_total

        status_style = "bold red" if s.overall_status == "REJECTED" else ("bold yellow" if s.overall_status == "FLAGGED_LEAKAGE" else "bold green")

        console.print(f"\n[bold magenta]══════════════════════════════════════════════════════════════════════════════════════[/bold magenta]")
        console.print(f"[bold white]Claim ID:[/bold white] [cyan]{report.claim_id}[/cyan] | [bold white]Policy:[/bold white] [cyan]{report.policy_id}[/cyan] | [bold white]Status:[/bold white] [{status_style}]{s.overall_status}[/{status_style}]")
        console.print(f"[dim]{report.case_title}[/dim]")
        console.print(f"[bold magenta]──────────────────────────────────────────────────────────────────────────────────────[/bold magenta]")

        # Line items table
        if report.line_items:
            table = Table(title="Line-Item Level Adjudication", header_style="bold cyan", show_lines=True)
            table.add_column("Line", style="dim", width=6)
            table.add_column("Category", width=14)
            table.add_column("Description", width=34)
            table.add_column("Claimed (₹)", justify="right", width=12)
            table.add_column("Admissible (₹)", justify="right", width=14)
            table.add_column("Discrepancy (₹)", justify="right", style="bold red", width=15)
            table.add_column("Status", width=12)

            for line in report.line_items:
                badge_style = "green" if line.status == "PASSED" else ("red" if line.status == "EXCLUDED" else "yellow")
                table.add_row(
                    line.line_id,
                    line.category,
                    line.description,
                    f"₹{line.claimed_amount:,.2f}",
                    f"₹{line.admissible_amount:,.2f}",
                    f"₹{line.discrepancy_amount:,.2f}" if line.discrepancy_amount > 0 else "-",
                    f"[{badge_style}]{line.status}[/{badge_style}]",
                )
            console.print(table)

        # Financial Summary Table
        sum_table = Table(title="Settlement Financial Waterfall", header_style="bold green")
        sum_table.add_column("Financial Metric", width=40)
        sum_table.add_column("Amount (₹)", justify="right", width=20)

        sum_table.add_row("Total Invoiced Amount", f"₹{s.total_claimed:,.2f}")
        if s.total_excluded > 0:
            sum_table.add_row("(-) Excluded Consumables / Admin Charges", f"₹{s.total_excluded:,.2f}", style="red")
        if s.total_sublimit_deduction > 0:
            sum_table.add_row("(-) Daily Room / ICU Cap Breaches", f"₹{s.total_sublimit_deduction:,.2f}", style="red")
        if s.total_proportionate_deduction > 0:
            sum_table.add_row("(-) Proportionate Deduction Cascade", f"₹{s.total_proportionate_deduction:,.2f}", style="red")
        if s.procedure_cap_deduction > 0:
            sum_table.add_row("(-) Procedure Sub-Limit Cap Excess", f"₹{s.procedure_cap_deduction:,.2f}", style="red")
        if s.deductible_applied > 0:
            sum_table.add_row("(-) Policy Deductible Applied", f"₹{s.deductible_applied:,.2f}", style="yellow")
        if s.copay_applied > 0:
            sum_table.add_row(f"(-) Policy Co-Payment Applied", f"₹{s.copay_applied:,.2f}", style="yellow")
        if s.balance_sum_insured_cap_deduction > 0:
            sum_table.add_row("(-) Sum Insured Ceiling Excess", f"₹{s.balance_sum_insured_cap_deduction:,.2f}", style="bold red")

        sum_table.add_row("[bold white]Calculated Admissible Settlement[/bold white]", f"[bold green]₹{s.calculated_settlement:,.2f}[/bold green]")
        sum_table.add_row("Proposed Settlement (Handler)", f"₹{s.proposed_settlement:,.2f}")
        sum_table.add_row(
            "[bold red]★ Prevented Financial Leakage[/bold red]",
            f"[bold red]₹{s.calculated_leakage_prevented:,.2f}[/bold red]",
        )
        if s.suspected_leakage_total > 0:
            sum_table.add_row(
                "[bold yellow]⚠ Suspected Leakage (Benchmark Outlier)[/bold yellow]",
                f"[bold yellow]₹{s.suspected_leakage_total:,.2f}[/bold yellow]",
            )

        console.print(sum_table)

        # Rules Applied Audit
        console.print("[bold yellow]Audit Rules & Formulas Applied:[/bold yellow]")
        all_rules = report.claim_level_rules + [r for item in report.line_items for r in item.rules_applied]
        for r in all_rules:
            if r.status != "PASSED" or r.discrepancy_amount > 0:
                console.print(f"  • [bold cyan]{r.rule_id}[/bold cyan] ({r.rule_name}): {r.reason}")

    # Final Aggregate Impact Panel
    console.print(
        Panel(
            f"[bold white]Total Claims Processed:[/bold white] {len(claims_data)}\n"
            f"[bold white]Total Billed Portfolio:[/bold white] ₹{total_processed_amount:,.2f}\n"
            f"[bold green]Total Confirmed Leakage Prevented:[/bold green] [bold green]₹{total_prevented_leakage:,.2f}[/bold green]\n"
            f"[bold yellow]Total Suspected Leakage Flagged:[/bold yellow] [bold yellow]₹{total_suspected_leakage:,.2f}[/bold yellow]",
            title="[bold green]Executive Financial Impact Summary[/bold green]",
            border_style="green",
        )
    )

if __name__ == "__main__":
    if "--cli" in sys.argv or len(sys.argv) == 1:
        run_cli_demo()
    else:
        import uvicorn
        uvicorn.run("src.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
