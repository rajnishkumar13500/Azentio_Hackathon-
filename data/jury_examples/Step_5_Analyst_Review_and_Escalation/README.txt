================================================================================
AZENTIO.AI CLAIMS LEAKAGE PREVENTION STUDIO - LEVEL 2 STEP 5 DEMO GUIDE
STEP 5: ANALYST REVIEW AND ESCALATION
================================================================================

OBJECTIVE:
Allow claims analysts to record a granular decision on every finding (line-item
and policy rule violation) with full workflow enforcement:
1. Confirm Discrepancy: Confirms leakage deduction as audited fact.
2. Mark as False Positive: Requires mandatory justification reason and reimburses claimant.
3. Request Additional Evidence: Requests missing pharmacy/hospital proof.
4. Escalate: Routes complex case to Senior Claims Reviewer or Special Investigation Unit (SIU).
5. Accept Recommended Correction: Locks in calculated settlement correction.

DEMO STEPS FOR JURY:
1. Load "01_analyst_review_case.json" via the Upload Modal or Folder Selector.
2. Click "Audit Claim" to open the 360° Claims Investigation Workspace.
3. Scroll down to:
   - "📋 Analyst Review & Escalation Dossier Report"
   - "Itemized Bill Line Items & Adjudication Rules"
   - "⚖️ Policy Adjudication Rules & Triggered Violations"
4. Click "⚖️ Record Decision" on any line item or rule.
5. Demonstrate all 5 actions:
   • Select "Mark as False Positive" -> Notice mandatory reason validation.
   • Select "Escalate" -> Notice target routing options (Senior Reviewer vs SIU).
   • Select "Accept Recommended Correction".
6. Observe live recalculation of Net Adjusted Settlement, Overrides Credited Back, and Dossier status.
7. Click "📥 Export Dossier (JSON)" to download the complete audit trail.

API ENDPOINTS:
- POST /api/v1/investigation/{claim_id}/decision
- GET  /api/v1/investigation/{claim_id}/decisions
- GET  /api/v1/investigation/{claim_id}/analyst-report
- GET  /api/v1/investigation/{claim_id}/workspace

