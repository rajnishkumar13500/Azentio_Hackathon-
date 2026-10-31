# Azentio.ai — Insurance Claims Intelligence & Financial Leakage Prevention Studio
> **Azentio Hackathon:** AI for Insurance Claims Intelligence & Financial Leakage Prevention  
> **Brand & Platform:** **Azentio.ai**  
> **Stack:** FastAPI, Python 3.13, Groq AI (Qwen 3.8-27B), Scikit-Learn, NumPy, Tailwind CSS, Chart.js  
> **End-to-End Scope:** **Step 1 (Ingestion)** ➔ **Step 2 (Policy Waterfall)** ➔ **Step 3 (Duplicate Detection & Embeddings)** ➔ **Step 4 (Arithmetic Leakage Proofs)** ➔ **Step 5 (Azentio.ai Alert Dashboard & Adjudication Studio)**.

---

## 📑 Table of Contents
1. [Executive Summary & Problem Statement](#-executive-summary--problem-statement)
2. [End-to-End Unified Architecture](#-end-to-end-unified-architecture)
3. [Step 1: Multi-Format Claims Ingestion](#-step-1-multi-format-claims-ingestion)
4. [Step 2: Policy Rule Waterfall Engine](#-step-2-policy-rule-waterfall-engine)
5. [Step 3: 4-Tier Duplicate Detection & Clinical Embeddings](#-step-3-4-tier-duplicate-detection--clinical-embeddings)
6. [Step 4: Financial Leakage Assessment & Arithmetic Proofs](#-step-4-financial-leakage-assessment--arithmetic-proofs)
7. [Step 5: Azentio.ai Interactive Alert Dashboard & Adjudication Studio](#-step-5-azentioai-interactive-alert-dashboard--adjudication-studio)
8. [Configuration & Environment Variables](#-configuration--environment-variables)
9. [Quick Start & Verification](#-quick-start--verification)
10. [Test Suite & Benchmark Verification](#-test-suite--benchmark-verification)

---

## 📌 Executive Summary & Problem Statement

Insurance carriers process massive volumes of healthcare and general insurance claims consisting of multi-format invoices, hospital bills, and itemized receipts. Operational and financial leakage occurs when claims are overpaid due to:
- **Duplicate Submissions**: Identical invoice resubmissions or subtle near-duplicates with altered invoice numbers, date slop, or rounded amounts.
- **Double-Billed Line Items**: The same diagnostic test, consult, or imaging billed multiple times on a single hospital bill.
- **Policy Breaches**: Room rent breaches triggering mandatory proportionate deductions on associated surgeon and doctor fees.
- **Excluded Items**: Non-payable consumables (PPE, sanitizers, gloves, admin charges) disguised under clinical jargon.
- **Unapplied Cost-Sharing**: Overlooked annual deductibles, procedure sub-limits, or mandatory co-payments.
- **Exhausted Benefit Ceilings**: Payments exceeding remaining balance sum insured.

**Azentio.ai** provides an automated, explainable, and enterprise-grade claims adjudication studio that connects deterministic mathematical validation with semantic AI intelligence to eliminate overpayments.

---

## 🏛 End-to-End Unified Architecture

```
                                 Multi-Format Claims Batch
                     (CSV, Excel .xlsx, JSON, Hospital Text Invoice)
                                             │
                                             ▼
  ┌─────────────────────────────────────────────────────────────────────────────────────┐
  │ STEP 1: Multi-Format Ingestion Service                                              │
  │ • Format Autodetection & Schema Normalization                                       │
  │ • Date, Identifier, and Currency Sanitization                                       │
  │ • Line-level Error Trapping (Never silently drops bad records)                     │
  └──────────────────────────────────────────┬──────────────────────────────────────────┘
                                             │
                                             ▼
  ┌─────────────────────────────────────────────────────────────────────────────────────┐
  │ STEP 3: 4-Tier Duplicate & Frequency Detection Engine                               │
  │ ├─ Tier 4: Repeat Service Guard (Protects valid dialysis/chemo/physio)             │
  │ ├─ Tier 1: Fast Exact Matcher (Deterministic composite hash O(1))                   │
  │ ├─ Tier 2: Intra-Claim Line Item Matcher (Same-bill double billing)                │
  │ └─ Tier 3: Near-Duplicate Matcher (Token N-grams + BERT/Clinical Vector Embeddings) │
  └──────────────────────────────────────────┬──────────────────────────────────────────┘
                                             │
                                             ▼
  ┌─────────────────────────────────────────────────────────────────────────────────────┐
  │ STEP 2: Policy Rule Waterfall Engine                                                │
  │ ├─ Stage 1: Policy Coverage & Eligibility Gatekeeper (Active dates, waiting period) │
  │ ├─ Stage 2: Daily Room Rent Breach Pre-Calculation (Allowed / Billed ratio)         │
  │ ├─ Stage 3: Line-Level Evaluation (Consumables exclusions, sub-limits, anomalies)   │
  │ ├─ Stage 4: Procedure / Ailment Sub-Limit Capping (Cataract, Appendicitis, TKR)     │
  │ ├─ Stage 5: Policy Deductible Deduction                                             │
  │ ├─ Stage 6: Co-Payment Application                                                  │
  │ └─ Stage 7: Balance Sum Insured Ceiling Reconciliation                              │
  └──────────────────────────────────────────┬──────────────────────────────────────────┘
                                             │
                                             ▼
  ┌─────────────────────────────────────────────────────────────────────────────────────┐
  │ STEP 4: Financial Leakage Assessment & Arithmetic Proofs                            │
  │ • Calculated Discrepancy (Exact, deterministic mathematical proof)                  │
  │ • Suspected Pricing Leakage (Statistical outlier / regional pricing benchmark)      │
  │ • Formal Equation & Step-by-Step Mathematical Explanation                           │
  └──────────────────────────────────────────┬──────────────────────────────────────────┘
                                             │
                                             ▼
  ┌─────────────────────────────────────────────────────────────────────────────────────┐
  │ STEP 5: Azentio.ai Claims Alert Dashboard & Adjudication Studio                     │
  │ • Executive KPI Ribbon (Processed Volume, Flag Rate, Prevented Leakage)             │
  │ • Visual Analytics (Leakage by Scenario, Severity Distribution, Hospital Breakdown) │
  │ • Multi-Dimensional Filters (Severity, Scenario, Provider, Free-text search)        │
  │ • Drilldown Adjudication View & Side-by-Side Duplicate Evidence                     │
  │ • Adjudicator Action Center (Confirm Denial, Adjust Settlement, Dismiss Alert)      │
  └─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📥 Step 1: Multi-Format Claims Ingestion

The ingestion service (`src/ingestion/`) processes diverse raw input formats without requiring pre-formatting:

- **Supported Formats**:
  - **CSV (`.csv`)**: Standard tabular claims data with automatic header normalization.
  - **Excel (`.xlsx`)**: Multi-sheet workbooks processed using `openpyxl`.
  - **JSON (`.json`)**: Deeply nested patient, incident, line item, and prior claim structures.
  - **Text (`.txt`)**: Raw hospital bill invoices with structured key-value line items.
- **Data Integrity & Validation**:
  - Enforces mandatory fields: Claim ID, Policy ID, Claimant Name, Incident Dates, Line Item amounts.
  - Normalizes date strings to ISO-8601 format.
  - Surfaces line-numbered errors in the response so corrupt rows are visible rather than silently dropped.
- **Sample Files**: Pre-packaged under `data/samples/` (`sample_claims.csv`, `sample_claims.xlsx`, `sample_hospital_invoice.txt`, `sample_invalid_claim.csv`).

---

## ⚙️ Step 2: Policy Rule Waterfall Engine

The policy validation engine (`src/engine/orchestrator.py` & `src/rules/`) executes an 8-stage deterministic waterfall:

1. **Policy Coverage & Waiting Period Gatekeeper**: Validates policy active status, covered dependents, initial 30-day waiting period, and pre-existing disease waiting periods (24–36 months).
2. **Room Rent Breach & Proportionate Deduction Ratio**: If room rent exceeds policy daily limit (e.g., ₹7,500 vs ₹5,000 limit), calculates the scaling ratio:
   $$\text{Ratio} = \frac{\text{Allowed Limit}}{\text{Billed Rate}} = \frac{5,000}{7,500} = 0.6667$$
3. **Line-Item Level Adjudication**:
   - Excludes non-payable consumables (PPE kits, gloves, registration charges).
   - Applies room rent capping.
   - Applies proportionate deduction to associate surgical and physician fees:
     $$\text{Admissible Fee} = \text{Billed Fee} \times \text{Ratio}$$
   - Identifies statistical price anomalies exceeding regional benchmarks.
4. **Procedure-Specific Sub-Limits**: Enforces disease/procedure caps (e.g. Cataract ₹35,000, Appendicitis ₹100,000).
5. **Deductible Application**: Deducts remaining annual or per-claim deductibles.
6. **Co-Payment Application**: Applies mandatory insured cost-sharing percentage (e.g. 10%–20%).
7. **Balance Sum Insured Ceiling**: Caps final settlement to the claimant's remaining balance sum insured.
8. **Financial Leakage Reconciliation**: Calculates exact prevented leakage:
   $$\text{Prevented Leakage} = \max(0, \text{Proposed Settlement} - \text{Calculated Settlement})$$

---

## 🔎 Step 3: 4-Tier Duplicate Detection & Clinical Embeddings

The duplicate detection engine (`src/duplicate_detector/`) prevents duplicate payouts through four complementary tiers:

### Tier 1: Fast Deterministic Exact Matcher
- **Scope**: Identifies 100% duplicate claim resubmissions and cross-claim duplicate line items.
- **Composite Key Hash**: Evaluates `(provider_id + invoice_number)` and `(claimant_id + incident_date + total_amount)`.
- **Complexity**: $O(1)$ lookup across historical settled claims.

### Tier 2: Intra-Claim Line Item Matcher
- **Scope**: Catches double-billing on the same invoice (e.g. two Chest X-Rays or ECGs on the same date).
- **Evaluation**: Exact match on `(service_date, service_code)` or identical description on the same service day.

### Tier 3: Near-Duplicate Matcher & Semantic Embeddings
- **Scope**: Flags fraudulent or erroneous resubmissions with minor alterations (e.g., invoice suffix `-B`, date shifted by $\pm 1\text{--}3$ days, rounding differences).
- **Clinical Semantic Embeddings**:
  - `ClinicalSemanticEmbedder`: Clinical ontology tokenizer matching medical synonyms (`Arthroplasty` $\leftrightarrow$ `Knee Replacement`, `HRCT` $\leftrightarrow$ `High Resolution CT`).
  - `BertSemanticEmbedder`: High-dimensional vector embeddings with cosine similarity scoring.
  - Matches clinical meaning even when bill wording varies.

### Tier 4: Legitimate Repeat Service Guard
- **Scope**: Protects legitimate recurring treatments (physiotherapy sessions, chemotherapy cycles, dialysis) from being falsely flagged.
- **Evaluation**: Verifies clinical protocol intervals and physician orders before allowing repeat services.

---

## 🧮 Step 4: Financial Leakage Assessment & Arithmetic Proofs

Step 4 bridges detection and audit by generating formal mathematical proofs for every flagged issue (`src/duplicate_detector/leakage_calculator.py`):

1. **Calculated Discrepancy (Exact & Deterministic)**:
   - Used when policy terms or duplicate billing define the exact excess amount.
   - Example 1 (Room Rent Excess):
     $$\text{Discrepancy} = (\text{Billed Rate} - \text{Daily Limit}) \times \text{Days} = (₹7,500 - ₹5,000) \times 4 = ₹10,000$$
   - Example 2 (Duplicate Claim):
     $$\text{Discrepancy} = 1.0 \times \text{Total Claimed Amount} = ₹32,000$$
2. **Suspected Leakage (Estimated Anomaly)**:
   - Used for statistical outliers (e.g., procedure billed at ₹125,000 when the regional benchmark is ₹110,000) or near-duplicate resubmissions requiring investigation.
3. **Structured Proof Schema**:
   Every finding includes an `ArithmeticProof` containing:
   - `formula`: The algebraic equation applied.
   - `input_values`: Real numerical inputs inserted into the equation.
   - `calculated_discrepancy`: The exact numeric result.
   - `explanation`: Human-readable audit narrative.

---

## 🖥️ Step 5: Azentio.ai Interactive Alert Dashboard & Adjudication Studio

The web application (`static/index.html`) is an enterprise UI built with Tailwind CSS, Chart.js, and Google Fonts:

- **Executive KPI Ribbon**: Real-time display of total claims, billed volume, exact prevented leakage, suspected leakage, and flag rate.
- **Interactive Visualizations**:
  - *Doughnut Chart*: Breakdown of leakage exposure across scenarios.
  - *Bar Chart*: Severity and review status distribution.
  - *Provider Breakdown*: Hospital-wise claims volume and prevented overpayments.
- **Multi-Dimensional Filters**: Filter claims by severity (Critical, High, Medium, Clean), scenario (Exact Duplicate, Intra-Claim Duplicate, Near Duplicate, Room Rent Breach, Consumable Exclusion), hospital provider, or free-text search.
- **Drilldown Adjudication View**:
  - Patient timeline, hospital info, ICD-10 code, and tenure.
  - Arithmetic Proof card detailing the formula, input values, and clinical similarity score.
  - Complete 8-stage settlement financial waterfall table.
  - Itemized line items table with per-line status pills.
  - AI clinical notes powered by Groq Qwen (`qwen/qwen3.8-27b`).
- **Adjudicator Action Center & Customer Report Export**:
  - **Confirm Denial**: Rejects 100% of duplicate / unauthorized claims.
  - **Adjust Settlement**: Confirms adjusted admissible entitlement.
  - **Dismiss Alert**: Approves claim as legitimate exception.
  - **📥 Download Customer Report**: Generates and downloads an official Explanation of Benefits (EOB) audit document (`Azentio_Settlement_Report_{claim_id}.html`) ready to send to policyholders and hospitals, containing the full financial waterfall, Step 4 arithmetic proof, itemized line decisions, digital certification seal, and IRDAI grievance notes.
  - Persists auditor notes and updates portfolio metrics live.

---

## ⚙️ Configuration & Environment Variables

Create or update `.env` in the project root:

```env
# Application Port
PORT=8000

# AI / LLM Configuration (Groq with Qwen)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_BASE_URL=https://api.groq.com
```

---

## 🚀 Quick Start & Verification

### 1. Set Up Environment
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### 2. Run the Unified Application
```bash
# Launch Azentio.ai (opens browser automatically on port 8000)
python app.py

# Or run directly via Uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 3. Open the Dashboard
Navigate to `http://localhost:8000` in your browser.
- Click **"Load Demo Batch"** to load the 9 comprehensive test cases.
- Or click **"Ingest Claims File"** to upload a CSV, Excel, JSON, or text file.
- Click **"Audit"** on any claim to inspect the arithmetic proof, policy waterfall, and submit adjudicator decisions.

---

## 🧪 Test Suite & Benchmark Verification

Run the comprehensive pytest suite covering all 5 steps:

```bash
PYTHONPATH=. .venv/bin/pytest tests
```

### Test Coverage Summary:
- `tests/policy_rules/test_api.py`: FastAPI endpoints, health check, UI serving, portfolio lifecycle, single-claim adjudication.
- `tests/policy_rules/test_ingestion.py`: CSV, Excel (.xlsx), JSON, and TXT parsing, validation, and error reporting.
- `tests/policy_rules/test_rules.py`: Coverage rules, exclusions, room rent caps, proportionate deductions, deductibles, co-pays, balance sum insured.
- `tests/policy_rules/test_synthetic_claims.py`: End-to-end validation across synthetic claims portfolio.
- `tests/test_duplicate_detector.py`: Exact duplicate claim detection, intra-claim line item matching, near-duplicate fuzzy matching, date slop, repeat guard.
- `tests/test_clinical_embeddings.py`: Clinical ontology tokenizer, TF-IDF vectorizer, BERT semantic embeddings, and cosine similarity.

**Result**: **34 passed in ~6 seconds**.
