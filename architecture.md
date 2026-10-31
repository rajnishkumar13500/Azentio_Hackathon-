# Claims Policy Validation Microservice Architecture

> **AI for Insurance Claims Intelligence & Financial Leakage Prevention**  
> *Azentio Hackathon 2026*

---

## 1. High-Level System Architecture

This microservice is a **stateless, high-throughput claims validation and financial leakage prevention engine**. It consumes normalized claim payloads and policy terms, evaluates both line items and aggregate claims through a strict insurance financial waterfall, and produces audit-ready settlement reports.

```mermaid
flowchart TD
    subgraph Upstream ["Upstream Ingestion Layer"]
        A["Claims Ingestion / OCR Service"] -->|POST Claim JSON + Policy Snapshot| B["FastAPI Gateway / REST Router"]
    end

    subgraph CoreEngine ["Policy Validation Engine (Stateless Microservice)"]
        B --> C["Stage 1: Policy Coverage & Eligibility Gatekeeper"]
        C -->|If Inactive / Ineligible / Waiting Period Breach| REJ["REJECT CLAIM (100% Leakage Prevented)"]
        
        C -->|If Coverage Valid| D["Stage 2: Clinical Normalization & Semantic Mapping"]
        D <-->|ICD-10, SNOMED & IRDAI Non-Payables| CAT["Medical Catalog"]
        D <-->|Contextual Reasoning / Jargon Check| GROQ["Groq LLM (Qwen 2.5)"]
        
        D --> E["Stage 3: Line-Item Adjudication Engine"]
        E -->|Consumables / Non-Payables| EXCL["IRDAI Exclusions Rule"]
        E -->|Daily Room / ICU Rent Excess| ROOM["Room & ICU Sub-Limits Rule"]
        E -->|Regional Benchmark Outliers| ANOM["Benchmark Pricing Anomaly Detector"]
        
        E --> F["Stage 4: Proportionate Deduction Cascade"]
        F --> G["Stage 5: Procedure & Disease Specific Capping"]
        G --> H["Stage 6: Policy Deductible Waterfall"]
        H --> I["Stage 7: Mandatory Co-Payment Deduction"]
        I --> J["Stage 8: Balance Sum Insured Ceiling"]
    end

    subgraph OutputReconciliation ["Settlement & Leakage Reconciliation"]
        J --> K["Discrepancy & Leakage Reconciler"]
        K -->|Reconcile Proposed vs. Calculated Settlement| L["Audit Report Generator"]
        L --> OUT1["Calculated Discrepancy (Deterministic ₹)"]
        L --> OUT2["Suspected Leakage (Statistical Anomaly ₹)"]
        L --> OUT3["Rule Audit Trail with Exact Formulas"]
    end

    subgraph Downstream ["Downstream Consumers"]
        L --> UI["Human-in-the-Loop Investigation Workbench"]
        L --> AUDIT["Core Claims Settlement & Audit System"]
    end
```

---

## 2. Insurance Settlement Financial Waterfall Flow

The mathematical sequence of health insurance claim adjudication is critical. Applying deductions in the wrong order results in erroneous payouts. This engine enforces the standard IRDAI regulatory waterfall:

```mermaid
flowchart TD
    START(["Total Invoiced Amount (Gross Claim)"]) --> STEP1
    
    subgraph Step1 ["Step 1: Regulatory Exclusions"]
        STEP1["(-) Ineligible Items & Non-Payable Consumables<br/><i>(Gloves, PPE, luxury charges, admin fees)</i>"]
    end
    
    STEP1 --> STEP2
    
    subgraph Step2 ["Step 2: Room & ICU Daily Sub-Limits"]
        STEP2["(-) Daily Room / ICU Rent Excess<br/><i>Formula: (Actual Daily Rate - Policy Cap) × Days</i>"]
    end
    
    STEP2 --> STEP3
    
    subgraph Step3 ["Step 3: Proportionate Deductions"]
        STEP3["(-) Associated Expenses Proportionate Reduction<br/><i>Formula: Associated Fee × (Allowed Room / Actual Room)</i>"]
    end
    
    STEP3 --> STEP4
    
    subgraph Step4 ["Step 4: Disease / Procedure Caps"]
        STEP4["(-) Procedure Specific Ceiling Excess<br/><i>(e.g., Cataract capped at ₹35k, Appendicitis at ₹100k)</i>"]
    end
    
    STEP4 --> STEP5
    
    subgraph Step5 ["Step 5: Deductibles"]
        STEP5["(-) Policy Deductible Applied<br/><i>Formula: min(Deductible, Current Admissible)</i>"]
    end
    
    STEP5 --> STEP6
    
    subgraph Step6 ["Step 6: Co-Payments"]
        STEP6["(-) Mandatory Co-Payment Applied<br/><i>Formula: Current Base × Co-Payment %</i>"]
    end
    
    STEP6 --> STEP7
    
    subgraph Step7 ["Step 7: Sum Insured Ceiling"]
        STEP7["(-) Remaining Balance Sum Insured Cap<br/><i>Formula: min(Current Base, Balance Sum Insured)</i>"]
    end
    
    STEP7 --> FINAL(["Calculated Admissible Settlement"])
    
    FINAL --> COMPARE{"Compare with Claim Handler's<br/>Proposed Settlement"}
    
    COMPARE -->|Proposed > Calculated| LEAK["★ Calculated Financial Leakage Prevented<br/><i>Proposed Settlement - Calculated Settlement</i>"]
    COMPARE -->|Proposed <= Calculated| CLEAN["✔ Zero Leakage (Approved as Submitted)"]
```

---

## 3. Component Architecture & Responsibilities

| Component | File Path | Core Functionality |
| :--- | :--- | :--- |
| **Config & Environment** | [`src/config.py`](file:///d:/Azentio_Hackathon/src/config.py) | Manages `.env` loading, Groq Qwen model selection, and paths to synthetic datasets. |
| **Data Contracts** | [`src/schemas/`](file:///d:/Azentio_Hackathon/src/schemas/) | Pydantic v2 schemas: `Policy`, `Claim`, `LineItem`, `RuleResult`, `ValidationReport`. |
| **Clinical Catalog** | [`src/catalog/medical_catalog.py`](file:///d:/Azentio_Hackathon/src/catalog/medical_catalog.py) | In-memory lookup with **word-boundary regex matching** to eliminate false positives (e.g. prevents matching `ppe` inside `appendectomy`). |
| **AI Clinical Agent** | [`src/ai/groq_client.py`](file:///d:/Azentio_Hackathon/src/ai/groq_client.py) | Connects to **Groq (`qwen-2.5-32b`)** for contextual clinical reasoning on complex or ambiguous medical descriptions. Fails over gracefully to catalog offline. |
| **Coverage Rule** | [`src/rules/coverage.py`](file:///d:/Azentio_Hackathon/src/rules/coverage.py) | Validates policy active status, date windows, covered dependents, 30-day initial waiting period, 24-month specific ailment waiting period, and 36-month pre-existing condition (PED) waiting period. |
| **Exclusion Rule** | [`src/rules/exclusions.py`](file:///d:/Azentio_Hackathon/src/rules/exclusions.py) | Flags IRDAI non-payable consumables (syringes, gloves, sanitizers, drapes) and administrative fees. |
| **Sub-Limit Rule** | [`src/rules/sub_limits.py`](file:///d:/Azentio_Hackathon/src/rules/sub_limits.py) | Computes room rent excess ($$\text{Daily Rate} > \text{Policy Cap}$$), ICU excess, and procedure-specific financial caps. |
| **Proportionate Deduction Rule** | [`src/rules/proportionate.py`](file:///d:/Azentio_Hackathon/src/rules/proportionate.py) | Contractual clause: if standard room rent is breached, associated surgeon, doctor, and nursing charges are reduced proportionally: $$\text{Ratio} = \frac{\text{Allowed Room Rate}}{\text{Actual Room Rate}}$$. |
| **Deductible Rule** | [`src/rules/deductible.py`](file:///d:/Azentio_Hackathon/src/rules/deductible.py) | Deducts per-claim or annual remaining deductible from the admissible base. |
| **Co-Payment Rule** | [`src/rules/copay.py`](file:///d:/Azentio_Hackathon/src/rules/copay.py) | Calculates and deducts contractual co-payment percentage (e.g. 10% or 20%). |
| **Benefit Limit Rule** | [`src/rules/benefit_limit.py`](file:///d:/Azentio_Hackathon/src/rules/benefit_limit.py) | Enforces remaining balance sum insured ceiling across the policy period. |
| **Benchmark Anomaly Rule** | [`src/rules/anomaly.py`](file:///d:/Azentio_Hackathon/src/rules/anomaly.py) | Flags provider procedure rates that exceed regional benchmarks as **Suspected Leakage** (requiring medical review, without breaking deterministic math). |
| **Waterfall Orchestrator** | [`src/engine/orchestrator.py`](file:///d:/Azentio_Hackathon/src/engine/orchestrator.py) | Executes all rules in strict waterfall order, compiles line-item audits, and reconciles financial leakage. |
| **Microservice Gateway & CLI** | [`src/main.py`](file:///d:/Azentio_Hackathon/src/main.py) | Provides FastAPI REST endpoints (`/health`, `/api/v1/validate`, `/api/v1/validate-demo/{id}`) and interactive Rich terminal CLI inspector. |

---

## 4. Sequence Diagram: Claim Validation Request

```mermaid
sequenceDiagram
    autonumber
    actor Handler as Claims Handler / Upstream System
    participant API as FastAPI Gateway (src/main.py)
    participant Engine as PolicyValidationEngine (orchestrator.py)
    participant Coverage as CoverageRule
    participant Catalog as MedicalCatalog
    participant Groq as Groq Qwen (groq_client.py)
    participant LineRules as LineItem Rules (Exclusions & SubLimits)
    participant Waterfall as Settlement Waterfall (Deductible, Copay, Caps)

    Handler->>API: POST /api/v1/validate (Claim + Policy)
    API->>Engine: validate_claim(claim, policy)
    
    Engine->>Coverage: evaluate(claim, policy)
    alt Policy Inactive / Waiting Period Breached
        Coverage-->>Engine: FAILED (RuleResult with reason)
        Engine-->>API: ValidationReport (Status: REJECTED, 100% Leakage Prevented)
        API-->>Handler: HTTP 200 OK (Report)
    else Policy & Dates Valid
        Coverage-->>Engine: PASSED
        
        loop For Each Line Item
            Engine->>LineRules: evaluate_line_item(item)
            LineRules->>Catalog: is_non_payable_consumable(desc)
            opt If Ambiguous & Groq Configured
                LineRules->>Groq: normalize_clinical_line_item(desc)
                Groq-->>LineRules: {concept, is_excluded, reasoning}
            end
            LineRules-->>Engine: RuleResult (EXCLUDED / BREACHED / PASSED)
        end
        
        Engine->>Waterfall: Apply Procedure Caps
        Engine->>Waterfall: Apply Deductibles
        Engine->>Waterfall: Apply Co-Payments
        Engine->>Waterfall: Enforce Balance Sum Insured
        Waterfall-->>Engine: Final Calculated Admissible Settlement
        
        Engine->>Engine: Reconcile (Proposed Settlement - Calculated Settlement)
        Engine-->>API: ValidationReport (Line Items + Summary + Formulas)
        API-->>Handler: HTTP 200 OK (JSON Audit Report)
    end
```

---

## 5. Distinction: Calculated Discrepancy vs. Suspected Leakage

As explicitly required by the hackathon problem statement:
- **Calculated Discrepancy (Deterministic ₹)**:
  - Exact mathematical overpayment resulting from objective policy terms.
  - Examples: Room rent overage ($$\text{Daily Rate} - \text{Limit} \times \text{Days}$$), non-payable consumables (gloves, PPE), co-payments, deductibles, or sum insured ceiling.
  - Handlers can automatically accept or apply this calculation.
- **Suspected Leakage (Statistical / Anomaly ₹)**:
  - Discrepancies resulting from provider price outliers (e.g. charging ₹1,25,000 for an appendectomy when the regional benchmark is ₹65,000).
  - The engine flags this as `ANOMALY_SUSPECTED` with the exact statistical delta ($$\text{Billed} - \text{Median}$$), keeping deterministic eligibility intact until a medical auditor approves or dismisses the finding.
