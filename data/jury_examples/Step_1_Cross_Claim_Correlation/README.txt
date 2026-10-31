================================================================================
AZENTIO.AI CLAIMS LEAKAGE PREVENTION STUDIO — JURY DEMO EXAMPLES
================================================================================
This folder contains grade-ready, pre-configured claims test files for demonstrating 
the end-to-end ingestion, validation, policy waterfall, duplicate detection, and 
cross-claim correlation capabilities to the evaluation jury.

Select any file or ingest them directly via the "Ingest Claims File" UI modal:

01_sample_claims.csv
  • Multi-claim tabular CSV input demonstrating batch claims ingestion.
  • Contains normal claims, room rent breaches, and consumable exclusions.

02_sample_claims.xlsx
  • Rich Excel spreadsheet workbook with itemized bill charges.
  • Tests multi-category line-item ingestion with pricing validation.

03_sample_hospital_invoice.txt
  • Real-world unstructured hospital tax invoice & discharge summary document.
  • Ingested via OCR / regex deterministic parser into structured claim format.

04_level2_cross_claim_correlations.json
  • Level 2 Cross-Claim Multi-Entity Correlation Benchmark Suite.
  • Scenarios demonstrated:
      1. Cross-Policy Double Dipping (Same invoice # across different policies)
      2. Overlapping Hospitalization (Physical impossibility of concurrent inpatient stays)
      3. Split Incident Stay (Unbundled hospitalization stay across separate bills)
      4. High-Velocity Provider Collusion (Clustered rapid-fire claims at same clinic)
      5. Legitimate Prior History Baseline (Informational history context)
      6. Recycled Hospital Invoice across distinct patients

05_sample_synthetic_claims.json
  • Complete 9-claim synthetic portfolio covering all 8 stages of the policy waterfall:
    Coverage, Room Rent, Proportionate Deduction, Consumables, Caps, Deductibles, 
    Co-payments, and Sum Insured Ceiling.

06_sample_invalid_claim.csv
  • Data Integrity & Guardrail validation file.
  • Contains negative amounts, missing claimant IDs, and reversed dates.
  • Proves the ingestion pipeline rejects invalid records rather than silently ignoring errors.
================================================================================

