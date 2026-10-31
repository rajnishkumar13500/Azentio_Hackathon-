import sys
import json
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

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.config import settings
from src.schemas import Claim, Policy, ValidationReport
from src.engine import validation_engine

console = Console()

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
