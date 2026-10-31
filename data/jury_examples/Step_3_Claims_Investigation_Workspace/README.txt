================================================================================
AZENTIO.AI CLAIMS LEAKAGE PREVENTION STUDIO — STEP 3 INVESTIGATION WORKSPACE
================================================================================
This folder contains the complete case package for demonstrating Capability 3:
The Claims Investigation Workspace.

CAPABILITY 3 VERIFICATION CHECKLIST:
1. Original Claim:
   • 01_investigation_claim_case.json (Claim CLM-DOC-AUDIT-001)
   • Examines patient demographics, hospital stay, and itemized billing ledger.

2. Relevant Policy Terms & Sub-Limits:
   • 02_policy_terms_registry.json (POL-COMPREHENSIVE-01)
   • Sum Insured (₹500,000), Balance (₹420,000), Room Rent Cap (₹5,000/day), 
     Co-Payment (10%), Deductible (₹5,000), and Proportionate Deduction Clause.

3. Related Claims (Cross-Claim Correlation):
   • Multi-entity graph linkages, shared invoices, and overlapping hospitalization.

4. Extracted Document Evidence & Comparison:
   • hospital_tax_invoice_saket.txt (Hospital Tax Invoice - ₹135,000)
   • clinical_discharge_summary.txt (Clinical Discharge Summary - Discharge: 2026-08-13)
   • Verbatim line-by-line reconciliation with source quotes.

5. Detected Discrepancies & Calculated Leakage:
   • Total amount mismatch (₹10,000 excess in claim)
   • Surgeon fee unit rate inflation (₹80,000 billed vs ₹70,000 on invoice)
   • Unsubstantiated line item (₹10,000 physical rehab session absent from bill)
   • Date mismatch (Claimed discharge 2026-08-14 vs clinical summary 2026-08-13)

6. Analyst Notes & Evidence Inspection:
   • Persistent working notes with auditor identity & timestamps.
   • Interactive "View Full Supporting Document" raw evidence viewer modal.
================================================================================

