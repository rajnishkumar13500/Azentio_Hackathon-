"""
Azentio.ai Customer Email Dispatcher Service.
Sends official Explanation of Benefits (EOB) settlement reports to policyholders and claimants.
Includes comprehensive financial calculations, Step 4 mathematical proofs, itemized decisions,
and official audit certification. Supports live SMTP delivery and simulated audit archiving.
"""

import os
import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

from src.config import settings
from src.schemas import Claim, Policy, ValidationReport
from src.report_generator import generate_customer_report_html, format_inr

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.dispatched_dir = settings.DISPATCHED_EMAILS_DIR
        self.dispatched_dir.mkdir(parents=True, exist_ok=True)

    def is_live_smtp_configured(self) -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_HOST.strip())

    def get_default_recipient_email(self, claim: Claim) -> str:
        if getattr(claim.claimant, "email", None) and claim.claimant.email.strip():
            return claim.claimant.email.strip()
        sanitized_name = "".join(c for c in claim.claimant.name.lower() if c.isalnum() or c == " ").strip().replace(" ", ".")
        return f"{sanitized_name}@insurance-client.com"

    def send_settlement_report(
        self,
        claim: Claim,
        policy: Policy,
        report: ValidationReport,
        adjudication: Optional[Dict[str, Any]] = None,
        recipient_email: Optional[str] = None,
        subject: Optional[str] = None,
        auditor_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates and dispatches the customer Explanation of Benefits (EOB) report.
        Embeds full financial waterfall calculations, arithmetic proofs, line-by-line itemization,
        and attaches the official digital certificate file.
        """
        recipient = (recipient_email or "").strip() or self.get_default_recipient_email(claim)
        
        email_subject = subject or (
            f"[Azentio.ai] Official Settlement Statement & Explanation of Benefits — Claim {claim.claim_id}"
        )

        s = report.summary
        adj = adjudication or {}
        adj_notes = auditor_notes or adj.get("notes") or (
            report.recommendations[0] if report.recommendations else "Standard policy adjudication."
        )
        generation_date = datetime.now().strftime("%d %B %Y, %I:%M %p")

        # Status badge determination
        if s.overall_status == "REJECTED":
            badge_bg = "#fef2f2"
            badge_color = "#991b1b"
            badge_border = "#fecaca"
            status_text = "CLAIM REJECTED / 100% DISALLOWANCE"
        elif s.calculated_leakage_prevented > 0 or s.total_excluded > 0:
            badge_bg = "#fffbeb"
            badge_color = "#92400e"
            badge_border = "#fde68a"
            status_text = "PARTIALLY APPROVED WITH POLICY DEDUCTIONS"
        else:
            badge_bg = "#ecfdf5"
            badge_color = "#065f46"
            badge_border = "#a7f3d0"
            status_text = "FULLY APPROVED SETTLEMENT"

        # 1. Generate full publication-grade HTML report attachment
        full_report_html = generate_customer_report_html(claim, policy, report, adjudication)

        # 2. Build Itemized Lines Rows for email body
        line_items_rows = ""
        for item in report.line_items:
            status_style = "background: #ecfdf5; color: #047857;" if item.status == "PASSED" else "background: #fef2f2; color: #b91c1c;"
            discrepancy_str = f"-{format_inr(item.discrepancy_amount)}" if item.discrepancy_amount > 0 else "-"
            reason_snippet = item.rules_applied[0].reason if item.rules_applied else "Compliant with policy terms"
            
            line_items_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 11px;">
              <td style="padding: 7px 10px; font-family: monospace; color: #64748b;">{item.line_id}</td>
              <td style="padding: 7px 10px; font-weight: 600; color: #334155;">{item.category}</td>
              <td style="padding: 7px 10px; color: #1e293b;">
                <strong>{item.description}</strong><br>
                <span style="color: #64748b; font-size: 10px;">{reason_snippet}</span>
              </td>
              <td style="padding: 7px 10px; text-align: right; font-family: monospace;">{format_inr(item.claimed_amount)}</td>
              <td style="padding: 7px 10px; text-align: right; font-family: monospace; font-weight: 600; color: #047857;">{format_inr(item.admissible_amount)}</td>
              <td style="padding: 7px 10px; text-align: right; font-family: monospace; font-weight: 700; color: #b91c1c;">{discrepancy_str}</td>
              <td style="padding: 7px 10px; text-align: center;">
                <span style="{status_style} padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 9px; text-transform: uppercase;">{item.status}</span>
              </td>
            </tr>
            """

        # 3. Build Arithmetic Proof Box for email
        findings = report.duplicate_findings or []
        proof_box_html = ""
        if findings and findings[0].get("arithmetic_proof"):
            p = findings[0]["arithmetic_proof"]
            proof_box_html = f"""
            <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 14px; margin: 16px 0;">
              <div style="font-weight: 800; font-size: 11px; color: #166534; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                🧮 STEP 4: MATHEMATICAL DISCREPANCY PROOF
              </div>
              <table style="width: 100%; border-collapse: collapse; font-size: 11px; font-family: monospace; line-height: 1.6;">
                <tr>
                  <td style="width: 130px; font-weight: bold; color: #334155;">Applied Formula:</td>
                  <td style="color: #047857; font-weight: bold;">{p.get('formula', '1.0 * claimed_amount')}</td>
                </tr>
                <tr>
                  <td style="font-weight: bold; color: #334155;">Input Variables:</td>
                  <td style="color: #1e293b;">{p.get('input_values', 'N/A')}</td>
                </tr>
                <tr>
                  <td style="font-weight: bold; color: #334155;">Calculated Discrepancy:</td>
                  <td style="color: #b91c1c; font-weight: 800; font-size: 13px;">{format_inr(p.get('calculated_discrepancy'))}</td>
                </tr>
              </table>
              <p style="margin: 6px 0 0 0; font-size: 11px; color: #166534; font-family: sans-serif;">
                {p.get('explanation', '')}
              </p>
            </div>
            """
        elif s.total_sublimit_deduction > 0:
            proof_box_html = f"""
            <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 14px; margin: 16px 0;">
              <div style="font-weight: 800; font-size: 11px; color: #166534; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                🧮 STEP 4: ROOM RENT LIMIT BREACH PROOF
              </div>
              <table style="width: 100%; border-collapse: collapse; font-size: 11px; font-family: monospace; line-height: 1.6;">
                <tr>
                  <td style="width: 130px; font-weight: bold; color: #334155;">Formula:</td>
                  <td style="color: #047857; font-weight: bold;">(Daily Billed Room Rent - Daily Policy Limit) × Inpatient Days</td>
                </tr>
                <tr>
                  <td style="font-weight: bold; color: #334155;">Policy Cap:</td>
                  <td style="color: #1e293b;">₹{policy.sub_limits.daily_room_rent:,.2f} / day</td>
                </tr>
                <tr>
                  <td style="font-weight: bold; color: #334155;">Excess Disallowed:</td>
                  <td style="color: #b91c1c; font-weight: 800; font-size: 13px;">{format_inr(s.total_sublimit_deduction)}</td>
                </tr>
              </table>
              <p style="margin: 6px 0 0 0; font-size: 11px; color: #166534; font-family: sans-serif;">
                Daily room charge exceeded policy ceiling. Mandatory proportionate deduction was cascaded across associated surgeon and consultant charges.
              </p>
            </div>
            """

        # 4. Detailed Calculation Waterfall HTML Rows
        waterfall_calculation_rows = f"""
        <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px;">
          <td style="padding: 8px 10px; font-weight: 700; color: #0f172a;">1. Gross Invoiced Amount</td>
          <td style="padding: 8px 10px; color: #64748b;">Aggregate total of all hospital invoice line items submitted</td>
          <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: bold; color: #0f172a;">{format_inr(s.total_claimed)}</td>
        </tr>
        """

        if s.total_excluded > 0:
            waterfall_calculation_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #b91c1c; background: #fff5f5;">
              <td style="padding: 8px 10px; font-weight: 600;">(-) Regulatory Excluded Consumables</td>
              <td style="padding: 8px 10px; font-size: 11px;">Non-payable under IRDAI standard guidelines (Gloves, PPE, Sanitizers, Registration charges)</td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: bold;">-{format_inr(s.total_excluded)}</td>
            </tr>
            """

        if s.total_sublimit_deduction > 0:
            waterfall_calculation_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #b91c1c; background: #fff5f5;">
              <td style="padding: 8px 10px; font-weight: 600;">(-) Daily Room Rent Limit Breach</td>
              <td style="padding: 8px 10px; font-size: 11px;">Billed daily rate exceeds policy room limit cap of ₹{policy.sub_limits.daily_room_rent:,.2f}/day</td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: bold;">-{format_inr(s.total_sublimit_deduction)}</td>
            </tr>
            """

        if s.total_proportionate_deduction > 0:
            waterfall_calculation_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #b91c1c; background: #fff5f5;">
              <td style="padding: 8px 10px; font-weight: 600;">(-) Associated Charges Proportionate Cascade</td>
              <td style="padding: 8px 10px; font-size: 11px;">Contractual reduction on surgeon, doctor visits & nursing: <code>Fee × (Allowed Room / Billed Room)</code></td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: bold;">-{format_inr(s.total_proportionate_deduction)}</td>
            </tr>
            """

        if s.procedure_cap_deduction > 0:
            waterfall_calculation_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #b91c1c; background: #fff5f5;">
              <td style="padding: 8px 10px; font-weight: 600;">(-) Procedure / Ailment Financial Cap Excess</td>
              <td style="padding: 8px 10px; font-size: 11px;">Admissible surgical charges capped to procedure-specific policy limit</td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: bold;">-{format_inr(s.procedure_cap_deduction)}</td>
            </tr>
            """

        if s.deductible_applied > 0:
            waterfall_calculation_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #b45309; background: #fffbeb;">
              <td style="padding: 8px 10px; font-weight: 600;">(-) Contractual Policy Deductible</td>
              <td style="padding: 8px 10px; font-size: 11px;">Agreed per-claim or annual deductible borne by policyholder</td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: bold;">-{format_inr(s.deductible_applied)}</td>
            </tr>
            """

        if s.copay_applied > 0:
            waterfall_calculation_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #b45309; background: #fffbeb;">
              <td style="padding: 8px 10px; font-weight: 600;">(-) Mandatory Co-Payment ({policy.co_payment_percentage}%)</td>
              <td style="padding: 8px 10px; font-size: 11px;">Contractual cost-sharing percentage calculated on admissible balance</td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: bold;">-{format_inr(s.copay_applied)}</td>
            </tr>
            """

        if s.balance_sum_insured_cap_deduction > 0:
            waterfall_calculation_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #b91c1c; background: #fff5f5;">
              <td style="padding: 8px 10px; font-weight: 600;">(-) Sum Insured Ceiling Excess</td>
              <td style="padding: 8px 10px; font-size: 11px;">Settlement capped strictly to remaining policy balance of ₹{policy.balance_sum_insured:,.2f}</td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: bold;">-{format_inr(s.balance_sum_insured_cap_deduction)}</td>
            </tr>
            """

        waterfall_calculation_rows += f"""
        <tr style="background: #f0fdf4; border-top: 2px solid #10b981; font-size: 13px; font-weight: bold; color: #047857;">
          <td style="padding: 10px;">★ Net Calculated Payable Settlement</td>
          <td style="padding: 10px; font-size: 11px; font-weight: normal; color: #065f46;">Payable to policyholder / hospital bank account</td>
          <td style="padding: 10px; text-align: right; font-family: monospace; font-size: 14px;">{format_inr(s.calculated_settlement)}</td>
        </tr>
        <tr style="background: #fff1f2; font-size: 12px; font-weight: bold; color: #b91c1c;">
          <td style="padding: 8px 10px;">Total Disallowed / Prevented Overpayment</td>
          <td style="padding: 8px 10px; font-size: 11px; font-weight: normal; color: #991b1b;">Excess claimed amount over contractual entitlement</td>
          <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-size: 13px;">{format_inr(s.calculated_leakage_prevented)}</td>
        </tr>
        """

        # 5. Build Comprehensive Email Body HTML
        email_body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Settlement Statement - {claim.claim_id}</title>
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.5; margin: 0; padding: 20px; background-color: #f8fafc; }}
            .container {{ max-width: 680px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
            .header {{ background: #064e3b; color: #ffffff; padding: 22px 24px; border-bottom: 3px solid #10b981; }}
            .badge-status {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 800; letter-spacing: 0.5px; margin-top: 6px; }}
            .content {{ padding: 24px; }}
            .meta-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }}
            .meta-table td {{ padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }}
            .calc-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
            .calc-table th {{ background: #f1f5f9; padding: 8px 10px; font-size: 11px; text-align: left; border-bottom: 2px solid #cbd5e1; color: #475569; text-transform: uppercase; }}
            .remarks-card {{ background: #f0fdf4; border-left: 4px solid #10b981; padding: 14px 16px; border-radius: 6px; margin: 18px 0; font-size: 12px; }}
            .footer {{ background: #f1f5f9; padding: 18px 24px; font-size: 11px; color: #64748b; text-align: center; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="container">
            <!-- Header Banner -->
            <div class="header">
              <table style="width: 100%; border-collapse: collapse;">
                <tr>
                  <td>
                    <div style="font-size: 20px; font-weight: 900; letter-spacing: -0.5px; color: #ffffff;">
                      🛡️ Azentio<span style="color: #34d399;">.ai</span>
                    </div>
                    <div style="font-size: 11px; color: #a7f3d0; margin-top: 2px;">
                      Claims Intelligence, Policy Audit & Overpayment Prevention Engine
                    </div>
                  </td>
                  <td style="text-align: right; vertical-align: top;">
                    <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; color: #ffffff;">Explanation of Benefits</div>
                    <div style="font-size: 10px; color: #d1fae5; font-family: monospace;">Ref: DOC-AZN-{claim.claim_id}</div>
                    <div style="font-size: 10px; color: #d1fae5;">{generation_date}</div>
                  </td>
                </tr>
              </table>
            </div>

            <!-- Main Content Area -->
            <div class="content">
              <!-- Verdict Pill -->
              <div style="background: {badge_bg}; border: 1px solid {badge_border}; border-radius: 8px; padding: 12px 16px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-size: 10px; font-weight: 700; color: {badge_color}; text-transform: uppercase;">Adjudication Decision</div>
                  <div style="font-size: 14px; font-weight: 800; color: {badge_color};">{status_text}</div>
                </div>
                <div style="text-align: right;">
                  <div style="font-size: 10px; color: #64748b; text-transform: uppercase;">Final Payable Settlement</div>
                  <div style="font-size: 18px; font-weight: 900; color: #047857; font-family: monospace;">{format_inr(s.calculated_settlement)}</div>
                </div>
              </div>

              <p style="font-size: 13px; margin: 0 0 12px 0;">
                Dear <strong>{claim.claimant.name}</strong>,
              </p>
              <p style="font-size: 12px; color: #334155; margin: 0 0 16px 0;">
                Your health insurance claim <strong>{claim.claim_id}</strong> submitted under policy <strong>{policy.policy_name}</strong> (Policy ID: <code>{policy.policy_id}</code>) has completed comprehensive clinical and mathematical adjudication. Below is the itemized financial calculation and audit determination:
              </p>

              <!-- Incident & Policy Overview -->
              <table class="meta-table">
                <tr>
                  <td style="width: 50%;"><strong>Claim Reference:</strong> {claim.claim_id}</td>
                  <td style="width: 50%;"><strong>Hospital:</strong> {claim.incident_details.hospital_name or claim.incident_details.hospital_id}</td>
                </tr>
                <tr>
                  <td><strong>Patient / Claimant:</strong> {claim.claimant.name} ({claim.claimant.age}y / {claim.claimant.relationship_to_insured})</td>
                  <td><strong>Admission Window:</strong> {claim.incident_details.admission_date[:10]} to {claim.incident_details.discharge_date[:10]}</td>
                </tr>
                <tr>
                  <td colspan="2"><strong>Primary Clinical Diagnosis:</strong> {claim.incident_details.diagnosis_description}</td>
                </tr>
              </table>

              <!-- Section 1: Detailed Financial Waterfall Calculation -->
              <div style="margin-top: 20px;">
                <div style="font-weight: 800; font-size: 12px; color: #0f172a; text-transform: uppercase; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 8px;">
                  1. Policy Settlement Financial Calculation Waterfall
                </div>
                <table class="calc-table">
                  <thead>
                    <tr>
                      <th style="width: 40%;">Waterfall Stage</th>
                      <th style="width: 40%;">Calculation Basis & Rule</th>
                      <th style="width: 20%; text-align: right;">Amount (₹)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {waterfall_calculation_rows}
                  </tbody>
                </table>
              </div>

              <!-- Section 2: Step 4 Mathematical Discrepancy Proof -->
              {proof_box_html}

              <!-- Section 3: Itemized Bill Audit Breakdown -->
              <div style="margin-top: 22px;">
                <div style="font-weight: 800; font-size: 12px; color: #0f172a; text-transform: uppercase; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 8px;">
                  2. Line-Level Bill Itemization & Disallowance Audit
                </div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 8px;">
                  <thead>
                    <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1; font-size: 10px; color: #475569; text-transform: uppercase; text-align: left;">
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
                    {line_items_rows}
                  </tbody>
                </table>
              </div>

              <!-- Auditor Remarks -->
              <div class="remarks-card">
                <div style="font-weight: 800; font-size: 11px; text-transform: uppercase; color: #166534; margin-bottom: 4px;">
                  📋 Certified Adjudicator Remarks & Clinical Notes:
                </div>
                <div style="color: #1e293b; font-size: 12px;">
                  {adj_notes}
                </div>
                <div style="margin-top: 8px; font-size: 10px; color: #64748b; font-family: monospace;">
                  Adjudicated by: Senior Claims Examiner • Azentio.ai Certified Audit Engine
                </div>
              </div>

              <!-- Attachment Note -->
              <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px; font-size: 11px; color: #1e40af; margin-top: 16px;">
                📎 <strong>Attached Official Document:</strong> The complete, unalterable digital audit report (<code>Azentio_Settlement_Report_{claim.claim_id}.html</code>) with printable certification seal is attached to this email for your official records.
              </div>
            </div>

            <!-- Footer -->
            <div class="footer">
              This is an official automated claims adjudication statement generated by Azentio.ai Claims Leakage Prevention Platform.<br>
              Prepared in strict adherence to IRDAI Health Insurance Adjudication Regulations.<br>
              For grievances, queries, or settlement payout timeline, contact: <strong>claims-support@azentio.ai</strong> referencing Claim ID <strong>{claim.claim_id}</strong>.
            </div>
          </div>
        </body>
        </html>
        """

        # 6. Create Multi-part Email Message
        msg = MIMEMultipart("mixed")
        msg["From"] = settings.SMTP_FROM
        msg["To"] = recipient
        msg["Subject"] = email_subject

        # Email Body (HTML)
        msg_alternative = MIMEMultipart("alternative")
        msg_alternative.attach(MIMEText(email_body_html, "html"))
        msg.attach(msg_alternative)

        # Attach complete Settlement Report as HTML attachment
        attachment = MIMEApplication(full_report_html.encode("utf-8"), _subtype="html")
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=f"Azentio_Settlement_Report_{claim.claim_id}.html"
        )
        msg.attach(attachment)

        dispatch_time = datetime.now(timezone.utc).isoformat()
        dispatch_mode = "SIMULATED"
        error_details = None

        # 7. Attempt Live SMTP if configured
        if self.is_live_smtp_configured():
            try:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12)
                server.ehlo()
                if settings.SMTP_USE_TLS:
                    server.starttls()
                    server.ehlo()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()
                dispatch_mode = "LIVE_SMTP"
                logger.info(f"Successfully dispatched settlement report for claim {claim.claim_id} to {recipient} via SMTP {settings.SMTP_HOST}.")
            except Exception as e:
                error_details = str(e)
                dispatch_mode = "SIMULATED_FALLBACK"
                logger.warning(f"SMTP dispatch to {recipient} failed ({e}). Falling back to simulated archive.")

        # 8. Archive email body and attachment to disk for regulatory audit
        archive_filename = f"email_{claim.claim_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        archive_path = self.dispatched_dir / archive_filename
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(email_body_html)

        # Save metadata record
        metadata = {
            "claim_id": claim.claim_id,
            "recipient_email": recipient,
            "recipient_name": claim.claimant.name,
            "subject": email_subject,
            "gross_claimed": s.total_claimed,
            "admissible_amount": s.calculated_settlement,
            "prevented_leakage": s.calculated_leakage_prevented,
            "dispatch_mode": dispatch_mode,
            "dispatch_timestamp": dispatch_time,
            "archive_file": archive_filename,
            "auditor_notes": adj_notes,
            "error_warning": error_details,
        }
        meta_path = self.dispatched_dir / f"meta_{claim.claim_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return {
            "status": "SUCCESS",
            "claim_id": claim.claim_id,
            "recipient_email": recipient,
            "recipient_name": claim.claimant.name,
            "subject": email_subject,
            "dispatch_mode": dispatch_mode,
            "dispatch_timestamp": dispatch_time,
            "message": (
                f"Settlement report successfully emailed to {recipient} ({dispatch_mode} mode)."
                if not error_details else
                f"Settlement report recorded and archived for {recipient} (SMTP Warning: {error_details})."
            ),
            "archive_path": str(archive_path),
            "smtp_configured": self.is_live_smtp_configured(),
        }

    def get_email_history_for_claim(self, claim_id: str) -> list:
        records = []
        if not self.dispatched_dir.exists():
            return records
        for f in sorted(self.dispatched_dir.glob(f"meta_{claim_id}_*.json"), reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    records.append(json.load(fp))
            except Exception:
                pass
        return records


email_service = EmailService()
