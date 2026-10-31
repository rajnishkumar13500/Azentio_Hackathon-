================================================================================
AZENTIO.AI CLAIMS LEAKAGE PREVENTION STUDIO - LEVEL 2 STEP 4 DEMO GUIDE
STEP 4: RECOMMENDED SETTLEMENT CORRECTIONS
================================================================================

OBJECTIVE:
Propose specific settlement adjustments rather than generic warnings:
- Removing duplicate / excluded line items
- Applying correct policy deductibles and co-pays
- Capping room charges at applicable sub-limits with proportionate deduction cascades
- Showing original amount, corrected amount, calculation formula, and policy clause citation.

FILES IN THIS FOLDER:
- 01_settlement_corrections_case.json: Comprehensive inpatient surgical claim triggering:
  1. Room Rent Sub-Limit Capping (₹12,000 billed vs ₹5,000 policy cap per day)
  2. Proportionate Deduction on Surgeon & OT Fees
  3. Consumable Items Exclusion (Gloves, Sanitizers)
  4. Policy Deductible & Co-payment Application

API ENDPOINT:
GET /api/v1/investigation/{claim_id}/corrections
Returns structured SettlementCorrection items with formula, amounts, and policy rule citations.

