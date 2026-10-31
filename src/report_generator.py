"""
Azentio.ai Customer Settlement Report & Explanation of Benefits (EOB) Generator.
Generates an official, publication-quality printable and downloadable HTML audit document.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from src.schemas import Claim, Policy, ValidationReport


def format_inr(val: Optional[float]) -> str:
    if val is None:
        return "₹0.00"
    return "₹" + f"{val:,.2f}"


def generate_customer_report_html(
    claim: Claim,
    policy: Policy,
    report: ValidationReport,
    adjudication: Optional[Dict[str, Any]] = None
) -> str:
    s = report.summary
    adj = adjudication or {}
    adj_status = adj.get("status") or (
        "CONFIRMED_DENIAL" if s.overall_status == "REJECTED" else (
            "ADJUSTED_SETTLEMENT" if s.calculated_leakage_prevented > 0 else "APPROVED"
        )
    )
    adj_by = adj.get("adjudicated_by") or "Senior Claims Adjudicator"
    adj_notes = adj.get("notes") or (report.recommendations[0] if report.recommendations else "Standard policy adjudication.")
    generation_date = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # Determine status badge colors
    if adj_status in ["CONFIRMED_DENIAL", "REJECTED"]:
        badge_bg = "#fef2f2"
        badge_color = "#991b1b"
        badge_border = "#fecaca"
        status_label = "REJECTED / 100% CLAIM DISALLOWANCE"
    elif adj_status in ["ADJUSTED", "ADJUST_AMOUNT", "ADJUSTED_SETTLEMENT", "FLAGGED_LEAKAGE"]:
        badge_bg = "#fffbeb"
        badge_color = "#92400e"
        badge_border = "#fde68a"
        status_label = "PARTIALLY APPROVED WITH POLICY DEDUCTIONS"
    else:
        badge_bg = "#ecfdf5"
        badge_color = "#065f46"
        badge_border = "#a7f3d0"
        status_label = "FULLY APPROVED SETTLEMENT"

    # Line items rows
    line_rows = ""
    for idx, item in enumerate(report.line_items, 1):
        status_color = "#059669" if item.status == "PASSED" else ("#dc2626" if item.status == "EXCLUDED" else "#d97706")
        status_bg = "#ecfdf5" if item.status == "PASSED" else ("#fef2f2" if item.status == "EXCLUDED" else "#fffbeb")
        primary_rule = item.rules_applied[0].rule_name if item.rules_applied else "Standard Admissible"
        reason = item.rules_applied[0].reason if item.rules_applied else "Complies with policy terms"

        line_rows += f"""
        <tr style="border-bottom: 1px solid #e2e8f0; font-size: 11px;">
            <td style="padding: 8px 10px; font-family: monospace; color: #64748b;">{item.line_id}</td>
            <td style="padding: 8px 10px; font-weight: 600; color: #1e293b;">{item.category}</td>
            <td style="padding: 8px 10px; color: #334155;">{item.description}<br><span style="font-size: 10px; color: #64748b;">{reason}</span></td>
            <td style="padding: 8px 10px; text-align: right; font-family: monospace;">{format_inr(item.claimed_amount)}</td>
            <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: 600; color: #047857;">{format_inr(item.admissible_amount)}</td>
            <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: 700; color: #b91c1c;">{format_inr(item.discrepancy_amount) if item.discrepancy_amount > 0 else '-'}</td>
            <td style="padding: 8px 10px; text-align: center;">
                <span style="background: {status_bg}; color: {status_color}; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 10px;">{item.status}</span>
            </td>
        </tr>
        """

    # Primary arithmetic proof
    findings = report.duplicate_findings or []
    proof_html = ""
    if findings and findings[0].get("arithmetic_proof"):
        p = findings[0]["arithmetic_proof"]
        proof_html = f"""
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; margin-top: 15px;">
            <div style="font-weight: 700; color: #166534; font-size: 12px; margin-bottom: 6px;">STEP 4: DETERMINISTIC ARITHMETIC DISCREPANCY PROOF</div>
            <div style="font-family: monospace; font-size: 11px; color: #1e293b; line-height: 1.6;">
                <div><strong>Applied Formula :</strong> {p.get('formula')}</div>
                <div><strong>Input Variables:</strong> {p.get('input_values')}</div>
                <div><strong>Excess Amount   :</strong> <span style="color: #b91c1c; font-weight: bold;">{format_inr(p.get('calculated_discrepancy'))}</span></div>
            </div>
            <p style="font-size: 11px; color: #166534; margin: 6px 0 0 0;">{p.get('explanation')}</p>
        </div>
        """
    elif s.total_sublimit_deduction > 0:
        proof_html = f"""
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; margin-top: 15px;">
            <div style="font-weight: 700; color: #166534; font-size: 12px; margin-bottom: 6px;">STEP 4: ROOM RENT LIMIT BREACH ARITHMETIC PROOF</div>
            <div style="font-family: monospace; font-size: 11px; color: #1e293b; line-height: 1.6;">
                <div><strong>Applied Formula :</strong> (Daily Room Rent Billed - Daily Policy Limit) × Inpatient Days</div>
                <div><strong>Discrepancy Amount:</strong> <span style="color: #b91c1c; font-weight: bold;">{format_inr(s.total_sublimit_deduction)}</span></div>
            </div>
            <p style="font-size: 11px; color: #166534; margin: 6px 0 0 0;">The daily room rent breached the policy entitlement ceiling. Mandatory proportionate deduction was cascaded across associated surgeon and consultant charges.</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Azentio.ai Settlement Report - {claim.claim_id}</title>
    <style>
        @page {{ size: A4; margin: 15mm; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1e293b;
            background: #fff;
            margin: 0;
            padding: 24px;
            font-size: 12px;
            line-height: 1.5;
        }}
        .print-btn {{
            position: fixed;
            top: 15px;
            right: 15px;
            background: #059669;
            color: #fff;
            border: none;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 12px;
            cursor: pointer;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}
        .print-btn:hover {{ background: #047857; }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ padding: 0; }}
        }}
    </style>
</head>
<body>

    <button onclick="window.print()" class="print-btn">🖨️ Print / Save as PDF</button>

    <!-- Header & Letterhead -->
    <div style="border-bottom: 3px solid #10b981; padding-bottom: 12px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 28px; height: 28px; background: #10b981; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 900; font-size: 16px;">🛡️</div>
                <h1 style="margin: 0; font-size: 20px; font-weight: 800; color: #064e3b; letter-spacing: -0.5px;">Azentio<span style="color: #10b981;">.ai</span></h1>
            </div>
            <p style="margin: 4px 0 0 0; font-size: 11px; color: #64748b;">Claims Intelligence, Policy Audit & Overpayment Prevention Engine</p>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 13px; font-weight: 800; color: #0f172a; text-transform: uppercase;">Explanation of Benefits (EOB)</div>
            <div style="font-size: 11px; color: #64748b;">Report Ref: DOC-AZN-{claim.claim_id}</div>
            <div style="font-size: 11px; color: #64748b;">Generated: {generation_date}</div>
        </div>
    </div>

    <!-- Status Verdict Banner -->
    <div style="background: {badge_bg}; border: 1px solid {badge_border}; border-radius: 8px; padding: 12px 16px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div style="font-size: 10px; font-weight: 700; color: {badge_color}; text-transform: uppercase; letter-spacing: 0.5px;">Adjudication Decision</div>
            <div style="font-size: 15px; font-weight: 800; color: {badge_color};">{status_label}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 10px; color: #64748b; text-transform: uppercase;">Net Admissible Payable</div>
            <div style="font-size: 18px; font-weight: 800; color: #047857; font-family: monospace;">{format_inr(s.calculated_settlement)}</div>
        </div>
    </div>

    <!-- Claimant & Incident Profile -->
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 18px; font-size: 11px;">
        <tr style="background: #f8fafc;">
            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; width: 25%;"><strong>Claim ID:</strong> {claim.claim_id}</td>
            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; width: 25%;"><strong>Policy ID:</strong> {policy.policy_id} ({policy.policy_name})</td>
            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; width: 25%;"><strong>Patient Name:</strong> {claim.claimant.name}</td>
            <td style="padding: 8px 12px; border: 1px solid #e2e8f0; width: 25%;"><strong>Age / Rel:</strong> {claim.claimant.age}y / {claim.claimant.relationship_to_insured}</td>
        </tr>
        <tr>
            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;"><strong>Hospital:</strong> {claim.incident_details.hospital_name or claim.incident_details.hospital_id}</td>
            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;"><strong>Admission:</strong> {claim.incident_details.admission_date[:10]}</td>
            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;"><strong>Discharge:</strong> {claim.incident_details.discharge_date[:10]}</td>
            <td style="padding: 8px 12px; border: 1px solid #e2e8f0;"><strong>Diagnosis:</strong> {claim.incident_details.diagnosis_description}</td>
        </tr>
    </table>

    <!-- Financial Reconciliation Waterfall -->
    <div style="margin-bottom: 18px;">
        <div style="font-weight: 700; font-size: 12px; color: #0f172a; margin-bottom: 8px; text-transform: uppercase;">1. Financial Waterfall Reconciliation</div>
        <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <thead>
                <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1; text-align: left;">
                    <th style="padding: 8px 10px;">Waterfall Component</th>
                    <th style="padding: 8px 10px;">Rule Explanation</th>
                    <th style="padding: 8px 10px; text-align: right;">Amount (INR)</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 10px;"><strong>Gross Invoiced Amount</strong></td>
                    <td style="padding: 6px 10px; color: #64748b;">Total billed charges submitted by provider</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace; font-weight: bold;">{format_inr(s.total_claimed)}</td>
                </tr>
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b91c1c;">
                    <td style="padding: 6px 10px;">(-) Non-Payable Consumables</td>
                    <td style="padding: 6px 10px;">IRDAI non-payable items (PPE, gloves, registration)</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.total_excluded)}</td>
                </tr>''' if s.total_excluded > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b91c1c;">
                    <td style="padding: 6px 10px;">(-) Daily Room Rent Breach</td>
                    <td style="padding: 6px 10px;">Room rent capped to daily limit of ₹{policy.sub_limits.daily_room_rent:,.2f}</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.total_sublimit_deduction)}</td>
                </tr>''' if s.total_sublimit_deduction > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b91c1c;">
                    <td style="padding: 6px 10px;">(-) Proportionate Deduction</td>
                    <td style="padding: 6px 10px;">Associated surgeon and visit charges scaled by room limit ratio</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.total_proportionate_deduction)}</td>
                </tr>''' if s.total_proportionate_deduction > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b91c1c;">
                    <td style="padding: 6px 10px;">(-) Procedure Specific Cap</td>
                    <td style="padding: 6px 10px;">Ailment sub-limit enforced per policy schedule</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.procedure_cap_deduction)}</td>
                </tr>''' if s.procedure_cap_deduction > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b45309;">
                    <td style="padding: 6px 10px;">(-) Policy Deductible Applied</td>
                    <td style="padding: 6px 10px;">Mandatory insured per-claim deductible applied</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.deductible_applied)}</td>
                </tr>''' if s.deductible_applied > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b45309;">
                    <td style="padding: 6px 10px;">(-) Policy Co-Payment ({policy.co_payment_percentage}%)</td>
                    <td style="padding: 6px 10px;">Agreed cost-sharing co-payment deducted from admissible sum</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.copay_applied)}</td>
                </tr>''' if s.copay_applied > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b91c1c;">
                    <td style="padding: 6px 10px;">(-) Balance Sum Insured Cap</td>
                    <td style="padding: 6px 10px;">Claimant available balance sum insured capped to ₹{policy.balance_sum_insured:,.2f}</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.balance_sum_insured_cap_deduction)}</td>
                </tr>''' if s.balance_sum_insured_cap_deduction > 0 else ''}
                <tr style="background: #f0fdf4; border-top: 2px solid #10b981; font-weight: bold; color: #047857;">
                    <td style="padding: 8px 10px;">Final Admissible Payable Settlement</td>
                    <td style="padding: 8px 10px;">Payable to Policyholder / Hospital</td>
                    <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-size: 13px;">{format_inr(s.calculated_settlement)}</td>
                </tr>
                <tr style="background: #fff1f2; font-weight: bold; color: #b91c1c;">
                    <td style="padding: 8px 10px;">Disallowed / Prevented Overpayment</td>
                    <td style="padding: 8px 10px;">Excess proposed over entitlement</td>
                    <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-size: 13px;">{format_inr(s.calculated_leakage_prevented)}</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Step 4 Arithmetic Proof -->
    {proof_html}

    <!-- Itemized Bill Breakdown -->
    <div style="margin-top: 20px;">
        <div style="font-weight: 700; font-size: 12px; color: #0f172a; margin-bottom: 8px; text-transform: uppercase;">2. Itemized Bill Line-Level Audit</div>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1; text-align: left; font-size: 11px;">
                    <th style="padding: 6px 10px;">Line</th>
                    <th style="padding: 6px 10px;">Category</th>
                    <th style="padding: 6px 10px;">Description & Rule Note</th>
                    <th style="padding: 6px 10px; text-align: right;">Billed ₹</th>
                    <th style="padding: 6px 10px; text-align: right;">Admissible ₹</th>
                    <th style="padding: 6px 10px; text-align: right;">Disallowed ₹</th>
                    <th style="padding: 6px 10px; text-align: center;">Status</th>
                </tr>
            </thead>
            <tbody>
                {line_rows}
            </tbody>
        </table>
    </div>

    <!-- Auditor Remarks & Signature Block -->
    <div style="margin-top: 24px; border-top: 2px solid #e2e8f0; padding-top: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div style="max-width: 60%;">
                <div style="font-weight: 700; font-size: 11px; text-transform: uppercase; color: #475569;">Adjudicator Comments & Regulatory Audit Notes</div>
                <p style="font-size: 11px; color: #334155; margin: 4px 0 0 0; background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                    {adj_notes}
                </p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 11px; font-weight: 700; color: #1e293b;">Certified Adjudicator</div>
                <div style="font-size: 11px; color: #059669; font-weight: 600;">{adj_by}</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 2px;">Azentio.ai Claims Audit Team</div>
                <div style="margin-top: 6px; font-size: 9px; color: #94a3b8; font-family: monospace;">DIGITALLY VERIFIED VIA AZENTIO ENGINE</div>
            </div>
        </div>
    </div>

    <!-- Customer Support & Grievance Notice -->
    <div style="margin-top: 20px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 12px; font-size: 10px; color: #64748b; text-align: center;">
        In accordance with IRDAI claims adjudication guidelines. For grievances or clarifications regarding this Explanation of Benefits, please reach out to claims-support@azentio.ai referencing Claim ID <strong>{claim.claim_id}</strong>.
    </div>

</body>
</html>
"""
    return html

