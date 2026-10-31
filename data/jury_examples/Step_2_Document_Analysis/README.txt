================================================================================
AZENTIO.AI CLAIMS LEAKAGE PREVENTION STUDIO — STEP 2 DOCUMENT ANALYSIS EXAMPLES
================================================================================
This folder contains sample supporting documents and claims for demonstrating
Level 2, Step 2: Document and Invoice Analysis & Evidence Reconciliation.

FILES IN THIS FOLDER:

1. hospital_tax_invoice_saket.txt
   • Official hospital tax invoice and itemized billing ledger.
   • Total Invoiced: INR 135,000.00
   • Key Discrepancy: Surgeon fee on invoice is ₹70,000, but claimed at ₹80,000.
     Also, pharmacy is ₹10,000 while claim includes an unsubstantiated ₹10,000 rehab session.

2. clinical_discharge_summary.txt
   • Clinical discharge summary from Max Super Speciality Saket.
   • Shows actual discharge date is 2026-08-13 (Length of stay: 3 days).
   • Discrepancy: Claim requests 4 days of room rent through 2026-08-14 (1 day date inflation).

3. repair_estimate_motor.txt
   • Authorized motor vehicle / equipment damage survey estimate.
   • Features part numbers, OEM rates, labor hours, and applicable depreciation schedules.

4. claim_for_document_audit.json
   • Submitted claim (CLM-DOC-AUDIT-001) for Vivek Singhania to compare against the above documents.
   • Shows 4 specific variances:
       - Total Amount Variance: ₹145,000 claimed vs ₹135,000 on hospital invoice (₹10,000 excess)
       - Rate Inflation: Line L2 claimed at ₹80,000 vs ₹70,000 on invoice (₹10,000 excess)
       - Unsubstantiated Line Item: Line L7 (₹10,000 Rehab) absent from supporting hospital bill
       - Date Mismatch: Claimed discharge 2026-08-14 vs Discharge Summary 2026-08-13
================================================================================

