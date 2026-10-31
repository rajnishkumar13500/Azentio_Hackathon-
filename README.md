# Azentio.ai — Insurance Claims Intelligence, Forensic Investigation & Financial Leakage Prevention Studio

> **Azentio Hackathon:** AI for Insurance Claims Intelligence & Financial Leakage Prevention  
> **Brand & Platform:** **Azentio.ai Claims Leakage Prevention Studio**  
> **Stack:** FastAPI, Python 3.13, Groq AI (Qwen 3.8-27B), Sentence-Transformers, PyPDF, OCR, SQLAlchemy, Tailwind CSS, Chart.js  
> **Coverage:** **Level 1 (Validation & Detection)** + **Level 2 (Claims Investigation Workspace, Evidence Comparison & Recommended Corrections)**  

---

## 📑 Table of Contents
1. [Executive Summary & Problem Statement](#-executive-summary--problem-statement)
2. [End-to-End System Architecture](#-end-to-end-system-architecture)
3. [Level 1: Claims Validation & Leakage Detection](#-level-1-claims-validation--leakage-detection)
   - [Step 1: Multi-Format Claims Ingestion Pipeline](#step-1-multi-format-claims-ingestion-pipeline)
   - [Step 2: 8-Stage Policy Rule Waterfall Engine](#step-2-8-stage-policy-rule-waterfall-engine)
   - [Step 3: 4-Tier Duplicate Detection & Clinical Embeddings](#step-3-4-tier-duplicate-detection--clinical-embeddings)
   - [Step 4: Deterministic Arithmetic Discrepancy Proofs](#step-4-deterministic-arithmetic-discrepancy-proofs)
   - [Step 5: Interactive Alert Dashboard & Adjudication Studio](#step-5-interactive-alert-dashboard--adjudication-studio)
4. [Level 2: Forensic Investigation & Settlement Corrections](#-level-2-forensic-investigation--settlement-corrections)
   - [1. Cross-Claim Multi-Entity Correlation](#1-cross-claim-multi-entity-correlation)
   - [2. Supporting Document & Invoice Evidence Reconciliation](#2-supporting-document--invoice-evidence-reconciliation)
   - [3. Claims Investigation Workspace](#3-claims-investigation-workspace)
   - [4. Recommended Settlement Corrections](#4-recommended-settlement-corrections)
   - [5. Analyst Review & Escalation Dossier](#5-analyst-review--escalation-dossier)
5. [Settlement Report & Explanation of Benefits (EOB)](#-settlement-report--explanation-of-benefits-eob)
6. [Jury Demonstration Guide & Pre-Packaged Datasets](#-jury-demonstration-guide--pre-packaged-datasets)
7. [Comprehensive API Reference](#-comprehensive-api-reference)
8. [Configuration & Environment Variables](#-configuration--environment-variables)
9. [Quick Start & Verification](#-quick-start--verification)
10. [Automated Test Suite](#-automated-test-suite)

---

## 📌 Executive Summary & Problem Statement

Insurance carriers process millions of healthcare and motor claims submitted across varied, unstructured channels: paper invoices, hospital PDFs, scanned discharge summaries, Excel rosters, and API payloads. Significant operational and financial leakage occurs due to:
- **Duplicate Claims & Double Dipping**: Identical invoices submitted across different policies, or subtle near-duplicates with altered dates, split stays, or modified amounts.
- **Sub-Limit & Proportionate Breaches**: Billed room rent exceeding daily policy limits without cascading proportional deductions across associated surgeon and consultant charges.
- **Unsubstantiated & Disguised Charges**: Billed hospital items not present on the actual tax invoice, or non-payable consumables disguised under generic clinical jargon.
- **Unapplied Cost-Sharing**: Missed annual deductibles, co-payment percentages, or balance sum insured ceilings.
- **Cross-Claim Collusion**: High-velocity provider billing rings and split stay unbundling designed to bypass individual policy authorization limits.

**Azentio.ai** combines **deterministic mathematical rule engines** with **Groq Qwen clinical intelligence**, **vector embeddings**, and **forensic document reconciliation** into a single unified claims studio.

---

## 🏛 End-to-End System Architecture

```
                          Multi-Format Claims & Evidence Uploads
                (CSV, Excel .xlsx, JSON, Hospital Text Bills, Scanned PDFs, Images)
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: INGESTION, DUPLICATE DETECTION & POLICY ADJUDICATION                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • Canonical Ingestion & OCR: PyPDF, Tesseract OCR, schema normalization, error logging │
│ • 4-Tier Duplicate Engine: Exact O(1) hash, intra-bill duplicates, clinical BERT embed │
│ • Policy Waterfall: Room rent capping, proportionate deduction cascade, co-pay/deduct  │
│ • Arithmetic Proof Engine: Step-by-step mathematical proofs with formula and inputs    │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: FORENSIC INVESTIGATION WORKSPACE & EVIDENCE RECONCILIATION                   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • Cross-Claim Correlation Engine: Links policies, claimants, providers, invoices      │
│ • Forensic Document Comparator: Table extraction, line rate inflation, missing charges │
│ • Investigation Workspace: Policy terms registry, raw document viewer, working notes  │
│ • Settlement Recommender: Specific, formulaic corrections with policy citations       │
│ • Analyst Review & Escalation: 5 supported decisions, SIU escalation, live recalculate │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ OUTPUT & REPORTING DISPATCH                                                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • Official EOB Settlement Report: Printable & downloadable audit certificate           │
│ • Itemized Bill Items & Policy Adjudication Rules Preview with Analyst Decisions       │
│ • Direct Customer Email Dispatch: Live SMTP or simulated archive with EOB attachments  │
│ • Downloadable Structured Investigation Dossier (JSON audit trail)                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Level 1: Claims Validation & Leakage Detection

### Step 1: Multi-Format Claims Ingestion Pipeline
- **Format Autodetection**: Ingests `.csv`, `.xlsx`, `.json`, `.txt`, `.pdf`, `.png`, and `.jpg` files without pre-processing.
- **Canonical Pipeline (`claims-ingestion/`)**: Multi-format staging with SQLite persistence, OCR text extraction, referential integrity checks, and line-level error trapping so bad records are flagged with exact line numbers rather than silently dropped.
- **Folder Upload**: Native directory picker allows selecting an entire demo folder (`data/jury_examples/`) with 1 click.

### Step 2: 8-Stage Policy Rule Waterfall Engine
Deterministically processes policy contracts (`src/rules/`):
1. **Eligibility Gatekeeper**: Active dates, covered dependents, initial 30-day and 24–36 month pre-existing disease waiting periods.
2. **Room Rent Ceiling Ratio**:
   $$\text{Proportionate Ratio} = \frac{\text{Allowed Daily Limit}}{\text{Billed Daily Rate}}$$
3. **Line-Item Adjudication**: Consumables exclusion (PPE, gloves, administrative fees), daily room/ICU capping, and proportionate deduction cascade on surgeon/OT fees.
4. **Procedure Sub-Limits**: Sub-limits for specific surgeries (Cataract, Appendicitis, Total Knee Replacement).
5. **Contractual Deductible**: Annual and per-claim deductibles deducted before admissible payout.
6. **Insured Co-Payment**: Percentage cost-sharing applied to eligible admissible expenses.
7. **Balance Sum Insured Ceiling**: Caps final payout at remaining available balance sum insured.
8. **Prevented Financial Leakage**:
   $$\text{Prevented Leakage} = \max(0, \text{Proposed Settlement} - \text{Calculated Admissible Settlement})$$

### Step 3: 4-Tier Duplicate Detection & Clinical Embeddings
- **Tier 1 (Fast Exact Matcher)**: $O(1)$ composite hash matching `(provider_id + invoice_number)` and `(claimant_id + date + amount)`.
- **Tier 2 (Intra-Claim Line Item Matcher)**: Catches double-billing on the same invoice (e.g., duplicated diagnostics or laboratory tests).
- **Tier 3 (Near-Duplicate & Semantic Matcher)**: Detects altered invoices (e.g. invoice suffix `-B`, date slop $\pm 1\text{--}3$ days) using `Sentence-Transformers` (`all-MiniLM-L6-v2`) and clinical ontology tokenization (`Arthroplasty` $\leftrightarrow$ `Knee Replacement`).
- **Tier 4 (Repeat Service Guard)**: Protects valid recurring treatments (dialysis, chemotherapy, physiotherapy) from false-positive flags.

### Step 4: Deterministic Arithmetic Discrepancy Proofs
Generates a formal mathematical breakdown for every discrepancy:
- **Formula**: Exact algebraic expression applied.
- **Input Variables**: Real monetary values and parameters inserted.
- **Calculated Leakage**: Exact numerical excess.
- **Audit Explanation**: Clear, human-readable narrative.

### Step 5: Interactive Alert Dashboard & Adjudication Studio
- **KPI Ribbon**: Total portfolio billed, exact prevented leakage, suspected leakage, flag rate.
- **Visual Analytics**: Chart.js charts for leakage by scenario, severity breakdown, and hospital provider distribution.
- **Drilldown View**: Patient timeline, ICD-10 codes, arithmetic proof box, policy waterfall, and Qwen AI clinical rationale.

---

## 🔍 Level 2: Forensic Investigation & Settlement Corrections

### 1. Cross-Claim Multi-Entity Correlation
Builds multi-dimensional linkages across policies, claimants, providers, invoices, and incidents:
- **Cross-Policy Double Dipping**: Detects the same hospital invoice number submitted under two distinct policies (`CLM-CORR-001` vs `CLM-CORR-002`).
- **Overlapping Hospitalization**: Identifies physically impossible concurrent inpatient stays for the same patient at different hospitals (`CLM-CORR-003` vs `CLM-CORR-004`).
- **Split Incident Stay Unbundling**: Detects consecutive stays within 48 hours for the same condition artificially split into two claims to stay beneath individual approval limits.
- **High-Velocity Provider Collusion**: Identifies sudden clusters of high-value claims submitted by the same hospital within hours.
- **Recycled Invoices Across Patients**: Uncovers fraudulent recycling of identical hospital invoice numbers across unrelated claimants.
- **Interactive Graph**: Generates nodes (Claim, Claimant, Provider, Invoice) and directed edges showing connection type and severity.

### 2. Supporting Document & Invoice Evidence Reconciliation
Extracts and cross-verifies sample supporting documents (hospital tax invoices, discharge summaries, repair estimates) against submitted claim data:
- **Variance Detection**: Identifies total amount mismatches, admission/discharge date discrepancies, and ICD-10 diagnosis discrepancies.
- **Line-Level Unit Rate Inflation**: Matches itemized invoice tables to detect rate inflation (e.g., surgeon fee billed at ₹80,000 in claim vs ₹70,000 on hospital invoice).
- **Unsubstantiated Charges**: Flags phantom billed items not found anywhere in the supporting document.
- **Verbatim Source Citations**: Every variance retains exact source document name, section, line number, and raw quote for forensic evidence.

### 3. Claims Investigation Workspace
Consolidates all evidence into an integrated 360° workspace for the claims auditor:
- **Relevant Policy Terms & Sub-Limits Card**: Displays sum insured, balance sum insured, daily room/ICU caps, co-pay %, deductible, and proportionate clause status.
- **Raw Document Inspector (`#rawDocModal`)**: Verbatim full-text document viewer with line count and size metrics.
- **Adjudicator Working Notes Center**: Supports drafting interim notes during ongoing investigation (`POST /api/v1/investigation/{claim_id}/notes`) without prematurely closing the claim.

### 4. Recommended Settlement Corrections
Replaces generic warnings with specific, actionable adjustments:
- Shows **Original Amount**, **Corrected Amount**, **Adjustment Amount**, **Calculation Formula**, and **Policy Rule / Evidence Citation**.
- Covers non-payable consumable removals, room rent capping, proportionate scaling, procedure caps, deductibles, and co-payments.

### 5. Analyst Review & Escalation Dossier
Enforces full regulatory decision workflows on every finding:
- **5 Supported Decisions**:
  1. `Confirm Discrepancy`: Validates leakage deduction as audited fact.
  2. `Mark as False Positive (with Reason)`: Enforces **mandatory justification reason** (API rejects empty reasons). Automatically credits back the discrepancy to the claimant.
  3. `Request Additional Evidence`: Places finding in pending review state while requesting supporting documentation.
  4. `Escalate to Senior Reviewer or SIU`: Routes finding to `SENIOR_CLAIMS_REVIEWER` or `SPECIAL_INVESTIGATION_UNIT` (SIU). Activates the `ROUTING: 🚨 SIU INVESTIGATION` banner.
  5. `Accept Recommended Correction`: Locks in the specific settlement adjustment.
- **Dynamic Settlement Recalculation**: Live calculation of Net Adjusted Settlement and False Positive Credits.
- **Export Dossier**: One-click download of the complete investigation dossier in structured JSON format.

---

## 📄 Settlement Report & Explanation of Benefits (EOB)

Accessible via the **"Preview"** and **"Download Customer Report"** buttons:
- **Publication-Quality EOB Certificate**: IRDAI-compliant layout containing claim reference, policy terms, and certified adjudicator seal.
- **Itemized Bill Line Items Table**: Complete line-level breakdown with line ID, category, billed amount, admissible amount, disallowed amount, rule note, and **Analyst Decision** column.
- **Policy Adjudication Rules & Triggered Violations Table**: Dedicated Section 3 displaying Rule ID, Policy Clause, Violation Formula, Discrepancy (₹), Rule Status, and **Analyst Decision** column.
- **Direct Email Dispatch**: Sends the complete EOB statement directly to the customer's inbox via live SMTP or persistent simulation archive (`data/dispatched_emails/`).

---

## 📂 Jury Demonstration Guide & Pre-Packaged Datasets

All jury demo files are structured into clean, individual folders under `data/jury_examples/`:

| Step Folder | Key Files | What It Demonstrates |
|---|---|---|
| `Step_1_Cross_Claim_Correlation/` | `01_cross_claim_correlation_benchmark.json`<br>`README.txt` | Cross-policy invoice double dipping (`CLM-CORR-001` vs `002`), overlapping physical impossibility (`CLM-CORR-003` vs `004`), split stay unbundling, and network graph. |
| `Step_2_Document_Analysis/` | `hospital_tax_invoice_saket.txt`<br>`clinical_discharge_summary.txt`<br>`repair_estimate_motor.txt`<br>`claim_for_document_audit.json` | Total variance (₹145k vs ₹135k), discharge date mismatch, unit rate inflation (₹80k vs ₹70k surgeon fee), and unsubstantiated charges. |
| `Step_3_Claims_Investigation_Workspace/` | `01_investigation_claim_case.json`<br>`02_policy_terms_registry.json`<br>`README.txt` | 360° workspace, policy terms sub-limits card, raw document inspector, and interim working notes. |
| `Step_4_Settlement_Corrections/` | `01_settlement_corrections_case.json`<br>`README.txt` | Specific non-generic adjustments with original amount, corrected amount, formula, and policy clause. |
| `Step_5_Analyst_Review_and_Escalation/` | `01_analyst_review_case.json`<br>`README.txt` | Complex cardiac claim demonstrating all 5 analyst decisions, mandatory false-positive reason validation, SIU escalation, and live dossier recalculation. |

---

## 🔌 Comprehensive API Reference

### Core Application & OpenAI Compatibility
- `GET  /` — Web application UI.
- `GET  /health` — Health check, Groq model status, and canonical ingestion availability.
- `GET  /v1/models` — OpenAI-compatible model listing.
- `POST /v1/chat/completions` — OpenAI-compatible completions endpoint.

### Claims & Portfolio Management
- `GET    /api/v1/claims` — List all claims in active portfolio with summary metrics.
- `GET    /api/v1/claims/{claim_id}` — Get single claim details.
- `DELETE /api/v1/claims` — Reset active portfolio.
- `POST   /api/v1/claims/seed-demo` — Seed demo batch.
- `GET    /api/v1/claims/{claim_id}/adjudicate` — Run policy waterfall on claim.
- `GET    /api/v1/claims/{claim_id}/report` — Generate official EOB HTML report (`?download=true` for file attachment).
- `POST   /api/v1/claims/{claim_id}/send-email` — Dispatch settlement report via email.

### Ingestion Pipeline
- `POST /api/v1/ingest/upload` — Ingest CSV, Excel, JSON, TXT, PDF, or image files.
- `POST /api/v1/ingest/upload-and-validate` — Full pipeline: Ingest -> Validate -> Persist -> Adjudicate.
- `POST /api/v1/ingest/canonical-sample` — Ingest sample dataset (`small` or `large`) via canonical pipeline.
- `GET  /api/v1/ingest/samples/{file_format}` — Download sample files (`csv`, `xlsx`, `txt`, `corr`, `json`, `step4`, `step5`).

### Level 2 Investigation Workspace
- `POST /api/v1/investigation/seed-correlation-dataset` — Seed 13 benchmark correlation claims.
- `GET  /api/v1/investigation/{claim_id}/correlations` — Get multi-entity correlations and network graph.
- `GET  /api/v1/investigation/correlations/all` — Portfolio-wide correlation scan.
- `GET  /api/v1/investigation/{claim_id}/document-evidence` — Reconcile claim against pre-linked documents.
- `POST /api/v1/investigation/{claim_id}/compare-document` — Upload new document and reconcile against claim.
- `GET  /api/v1/investigation/documents/{document_name}` — Get verbatim raw document content.
- `POST /api/v1/investigation/{claim_id}/notes` — Save interim auditor working notes.
- `GET  /api/v1/investigation/{claim_id}/workspace` — 360° consolidated workspace payload.
- `GET  /api/v1/investigation/{claim_id}/corrections` — Recommended settlement corrections list.
- `POST /api/v1/investigation/{claim_id}/decision` — Record analyst decision on a finding.
- `GET  /api/v1/investigation/{claim_id}/decisions` — Retrieve all recorded decisions for a claim.
- `GET  /api/v1/investigation/{claim_id}/analyst-report` — Generate complete Analyst Review & Escalation Dossier.

---

## ⚙️ Configuration & Environment Variables

Create or update `.env` in the project root:

```env
# Application Port
PORT=8000

# Groq AI Model Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_BASE_URL=https://api.groq.com

# SMTP Email Configuration (Optional - falls back to simulated archive)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=claims-adjudication@azentio.ai
SMTP_FROM_NAME="Azentio.ai Claims Adjudication Team"
```

---

## 🚀 Quick Start & Verification

### 1. Set Up Environment
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Application
```bash
# Launch Azentio.ai (starts FastAPI server on port 8000)
python app.py

# Or run directly via Uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 3. Open the Studio
Open `http://localhost:8000` in your browser:
1. Click **"Ingest Claims File"** and use **"Select Jury Folder"** to pick any folder in `data/jury_examples/`.
2. Click **"Audit"** to enter the Claims Investigation Workspace.
3. Inspect **Policy Terms & Sub-Limits**, click **"👁️ Inspect Raw Document"**, test **Working Notes**, and record **Analyst Decisions**.
4. Click **"Preview"** to examine the official Explanation of Benefits (EOB) certificate with itemized bill lines and triggered policy adjudication rules.

---

## 🧪 Automated Test Suite

Run the full pytest suite across all modules:

```bash
PYTHONPATH=. .venv/bin/pytest tests
```

### Test Suite Breakdown:
- `tests/test_analyst_review.py`: Tests all 5 analyst decisions, mandatory reason validation for false positives, SIU escalation, settlement corrections, and report preview tables.
- `tests/test_investigation_workspace.py`: Tests 360° workspace payload, verbatim document text inspection, and working notes persistence.
- `tests/test_document_analysis.py`: Tests invoice table extraction, stay date reconciliation, line-level unit rate inflation, and unsubstantiated charge detection.
- `tests/test_cross_claim_correlation.py`: Tests cross-policy double dipping, overlapping stay physical impossibility, split stay unbundling, and graph generation.
- `tests/test_duplicate_detector.py`: Tests 4-tier duplicate detection (exact, intra-claim, near-duplicate, repeat guard).
- `tests/test_clinical_embeddings.py`: Tests clinical ontology tokenization and semantic similarity scoring.
- `tests/test_email_service.py`: Tests customer settlement report generation and email dispatch.
- `tests/policy_rules/`: Tests policy rules, ingestion parsers, and synthetic claim portfolios.

**Result**: **61+ tests passed with zero errors**.
