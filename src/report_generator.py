"""
Azentio.ai Customer Settlement Report & Explanation of Benefits (EOB) Generator.
Generates an official, publication-quality printable and downloadable HTML audit document
with embedded direct customer email dispatch capabilities.
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

    # Determine default customer recipient email
    claimant_email = getattr(claim.claimant, "email", None)
    if not claimant_email or not claimant_email.strip():
        sanitized_name = "".join(c for c in claim.claimant.name.lower() if c.isalnum() or c == " ").strip().replace(" ", ".")
        claimant_email = f"{sanitized_name}@insurance-client.com"

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
        .action-bar-top {{
            position: fixed;
            top: 15px;
            right: 15px;
            display: flex;
            gap: 10px;
            z-index: 1000;
        }}
        .btn-top {{
            border: none;
            padding: 10px 16px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 12px;
            cursor: pointer;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }}
        .print-btn {{
            background: #059669;
            color: #fff;
        }}
        .print-btn:hover {{ background: #047857; }}
        .email-btn {{
            background: #2563eb;
            color: #fff;
        }}
        .email-btn:hover {{ background: #1d4ed8; }}
        
        /* Modal Styles */
        .email-modal-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(2px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2000;
        }}
        .email-modal-card {{
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            width: 100%;
            max-width: 480px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
            animation: modalFadeIn 0.2s ease-out;
        }}
        @keyframes modalFadeIn {{
            from {{ opacity: 0; transform: scale(0.96); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        .email-modal-header {{
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            padding: 14px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        
        @media print {{
            .action-bar-top, .email-modal-overlay {{ display: none !important; }}
            body {{ padding: 0; }}
        }}
    </style>
</head>
<body>

    <!-- Top Action Ribbon -->
    <div class="action-bar-top">
        <button onclick="window.print()" class="btn-top print-btn">
            <span>🖨️</span>
            <span>Print / Save as PDF</span>
        </button>
        <button onclick="openEmailModal()" class="btn-top email-btn" id="btnEmailReportTrigger">
            <span>📧</span>
            <span>Send Email to Customer</span>
        </button>
    </div>

    <!-- Email Dispatch Modal -->
    <div id="emailModal" class="email-modal-overlay">
        <div class="email-modal-card">
            <div class="email-modal-header">
                <div style="font-weight: 700; font-size: 14px; color: #064e3b; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 16px;">📧</span>
                    <span>Send Settlement Report to Policyholder</span>
                </div>
                <button onclick="closeEmailModal()" style="background: none; border: none; font-size: 18px; cursor: pointer; color: #64748b; line-height: 1;">✕</button>
            </div>
            <div style="padding: 18px 20px;">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-size: 11px; font-weight: 700; color: #475569; margin-bottom: 4px;">Policyholder / Claimant Name</label>
                    <input type="text" id="reportEmailRecipientName" value="{claim.claimant.name}" readonly style="width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; background: #f8fafc; color: #334155;">
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-size: 11px; font-weight: 700; color: #475569; margin-bottom: 4px;">Destination Customer Email Address <span style="color: #dc2626;">*</span></label>
                    <input type="email" id="reportEmailRecipient" value="{claimant_email}" placeholder="customer@example.com" style="width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; outline: none; font-family: monospace;">
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-size: 11px; font-weight: 700; color: #475569; margin-bottom: 4px;">Email Subject</label>
                    <input type="text" id="reportEmailSubject" value="[Azentio.ai] Official Settlement Statement & Explanation of Benefits — Claim {claim.claim_id}" style="width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px;">
                </div>
                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-size: 11px; font-weight: 700; color: #475569; margin-bottom: 4px;">Auditor Remarks / Notes Included in Message</label>
                    <textarea id="reportEmailNotes" rows="2" style="width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; resize: vertical;">{adj_notes}</textarea>
                </div>
                <div id="reportEmailStatusAlert" style="display: none; padding: 10px 12px; border-radius: 6px; font-size: 11px; margin-bottom: 12px;"></div>
                <p style="font-size: 11px; color: #64748b; margin: 0;">
                    Attaches the complete official Explanation of Benefits (EOB) HTML audit certificate and financial waterfall.
                </p>
            </div>
            <div style="background: #f8fafc; padding: 12px 20px; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 10px;">
                <button onclick="closeEmailModal()" style="padding: 8px 14px; background: #e2e8f0; color: #475569; border: none; border-radius: 6px; font-weight: 600; font-size: 12px; cursor: pointer;">Cancel</button>
                <button id="btnSendReportEmailSubmit" onclick="executeReportEmailDispatch()" style="padding: 8px 18px; background: #059669; color: #fff; border: none; border-radius: 6px; font-weight: 700; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                    <span>Send Email Now</span>
                </button>
            </div>
        </div>
    </div>

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

    <!-- Financial Waterfall Summary Table -->
    <div style="margin-bottom: 20px;">
        <div style="font-weight: 700; font-size: 12px; color: #0f172a; margin-bottom: 8px; text-transform: uppercase;">1. Policy Settlement Financial Waterfall</div>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1; text-align: left; font-size: 11px;">
                    <th style="padding: 6px 10px;">Waterfall Stage</th>
                    <th style="padding: 6px 10px;">Calculation Basis</th>
                    <th style="padding: 6px 10px; text-align: right;">Amount (₹)</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 10px; font-weight: 600;">Total Invoiced / Claimed</td>
                    <td style="padding: 6px 10px;">Sum of all itemized charges submitted</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">{format_inr(s.total_claimed)}</td>
                </tr>
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b91c1c;">
                    <td style="padding: 6px 10px;">(-) Non-Payable Consumables & Admin</td>
                    <td style="padding: 6px 10px;">Disallowed under IRDAI Non-Payable Schedule (PPE, Gloves, etc.)</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.total_excluded)}</td>
                </tr>''' if s.total_excluded > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b91c1c;">
                    <td style="padding: 6px 10px;">(-) Daily Room Rent Sub-Limit Excess</td>
                    <td style="padding: 6px 10px;">Excess daily room rent above policy cap of ₹{policy.sub_limits.daily_room_rent:,.2f}/day</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.total_sublimit_deduction)}</td>
                </tr>''' if s.total_sublimit_deduction > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b91c1c;">
                    <td style="padding: 6px 10px;">(-) Proportionate Associated Charges Cascade</td>
                    <td style="padding: 6px 10px;">Mandatory proportionate scaling on surgeon, doctor and nursing fees</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.total_proportionate_deduction)}</td>
                </tr>''' if s.total_proportionate_deduction > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b91c1c;">
                    <td style="padding: 6px 10px;">(-) Procedure-Specific Financial Sub-Limit</td>
                    <td style="padding: 6px 10px;">Cap applied to procedure per policy terms</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.procedure_cap_deduction)}</td>
                </tr>''' if s.procedure_cap_deduction > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b45309;">
                    <td style="padding: 6px 10px;">(-) Policy Deductible Applied</td>
                    <td style="padding: 6px 10px;">Standard contractual deductible</td>
                    <td style="padding: 6px 10px; text-align: right; font-family: monospace;">-{format_inr(s.deductible_applied)}</td>
                </tr>''' if s.deductible_applied > 0 else ''}
                {f'''<tr style="border-bottom: 1px solid #e2e8f0; color: #b45309;">
                    <td style="padding: 6px 10px;">(-) Mandatory Co-Payment ({policy.co_payment_percentage}%)</td>
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

    <!-- Interactive Client Scripts for Direct Email Dispatch -->
    <script>
    function openEmailModal() {{
        document.getElementById('emailModal').style.display = 'flex';
        document.getElementById('reportEmailStatusAlert').style.display = 'none';
        const submitBtn = document.getElementById('btnSendReportEmailSubmit');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span>Send Email Now</span>';
    }}

    function closeEmailModal() {{
        document.getElementById('emailModal').style.display = 'none';
    }}

    async function executeReportEmailDispatch() {{
        const recipientInput = document.getElementById('reportEmailRecipient');
        const email = recipientInput.value.trim();
        if (!email || !email.includes('@')) {{
            alert('Please provide a valid recipient email address.');
            recipientInput.focus();
            return;
        }}

        const submitBtn = document.getElementById('btnSendReportEmailSubmit');
        const alertBox = document.getElementById('reportEmailStatusAlert');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>⏳ Dispatching...</span>';
        alertBox.style.display = 'none';

        try {{
            const res = await fetch('/api/v1/claims/{claim.claim_id}/send-email', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    recipient_email: email,
                    recipient_name: document.getElementById('reportEmailRecipientName').value.trim(),
                    subject: document.getElementById('reportEmailSubject').value.trim(),
                    notes: document.getElementById('reportEmailNotes').value.trim()
                }})
            }});

            const data = await res.json();
            if (!res.ok) {{
                throw new Error(data.detail || 'Email transmission was rejected by server.');
            }}

            alertBox.style.display = 'block';
            alertBox.style.background = '#ecfdf5';
            alertBox.style.color = '#065f46';
            alertBox.style.border = '1px solid #a7f3d0';
            alertBox.innerHTML = '<strong>✔ Success:</strong> ' + (data.message || 'Settlement report emailed successfully.');
            submitBtn.innerHTML = '<span>✔ Email Dispatched</span>';

            // Also update the trigger button in top ribbon
            const triggerBtn = document.getElementById('btnEmailReportTrigger');
            if (triggerBtn) {{
                triggerBtn.style.background = '#059669';
                triggerBtn.innerHTML = '<span>✔</span><span>Email Sent to Customer</span>';
            }}

            setTimeout(() => {{
                closeEmailModal();
            }}, 2200);

        }} catch (err) {{
            alertBox.style.display = 'block';
            alertBox.style.background = '#fef2f2';
            alertBox.style.color = '#991b1b';
            alertBox.style.border = '1px solid #fecaca';
            alertBox.innerHTML = '<strong>Transmission Error:</strong> ' + err.message;
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>Retry Dispatch</span>';
        }}
    }}

    // Close modal on escape key or backdrop click
    window.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') closeEmailModal();
    }});
    document.getElementById('emailModal').addEventListener('click', function(e) {{
        if (e.target === this) closeEmailModal();
    }});
    </script>

</body>
</html>
"""
    return html
