from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Set, Tuple
from sqlalchemy.orm import Session
from app.domain.enums import ValidationSeverity
from app.validation.field_validators import ValidationErrorItem
from app.persistence.models.claim_models import Policy, Claim, Invoice
from app.config import settings

class ReferentialValidator:
    @staticmethod
    def validate_references(
        db: Session,
        staged_records_by_type: Dict[str, List[Dict[str, Any]]],
        record_type: str,
        payload: Dict[str, Any]
    ) -> List[ValidationErrorItem]:
        issues = []

        # 1. Claim -> Policy reference
        if record_type == "CLAIM":
            pol_num = payload.get("policy_number")
            pol_id = payload.get("policy_id")
            
            if not pol_num and not pol_id:
                issues.append(ValidationErrorItem(
                    field_name="policy_number",
                    error_code="MISSING_POLICY_REFERENCE",
                    severity=ValidationSeverity.ERROR,
                    message="Claim must reference a policy number or policy ID.",
                    received_value=None
                ))
            else:
                # Check within staged bundle
                staged_policies = staged_records_by_type.get("POLICY", [])
                matched_in_bundle = None
                for p in staged_policies:
                    p_norm = p.get("normalised_payload", {})
                    if pol_num and str(p_norm.get("policy_number")) == str(pol_num):
                        matched_in_bundle = p_norm
                        break
                    if pol_id and str(p_norm.get("policy_id")) == str(pol_id):
                        matched_in_bundle = p_norm
                        break

                # Check in DB if not in bundle
                matched_in_db = None
                if not matched_in_bundle:
                    q = db.query(Policy)
                    if pol_num:
                        matched_in_db = q.filter(Policy.policy_number == str(pol_num)).first()
                    elif pol_id:
                        matched_in_db = q.filter(Policy.policy_id == str(pol_id)).first()

                if not matched_in_bundle and not matched_in_db:
                    issues.append(ValidationErrorItem(
                        field_name="policy_number",
                        error_code="UNRESOLVED_POLICY_REFERENCE",
                        severity=ValidationSeverity.ERROR,
                        message=f"Referenced policy '{pol_num or pol_id}' does not exist in bundle or database.",
                        received_value=str(pol_num or pol_id)
                    ))
                else:
                    # Validate incident date is within policy coverage dates
                    inc_date_str = payload.get("incident_date")
                    if inc_date_str:
                        try:
                            inc_date = datetime.strptime(str(inc_date_str), "%Y-%m-%d").date()
                            eff_from = None
                            eff_to = None
                            if matched_in_bundle:
                                if matched_in_bundle.get("effective_from"):
                                    eff_from = datetime.strptime(str(matched_in_bundle["effective_from"]), "%Y-%m-%d").date()
                                if matched_in_bundle.get("effective_to"):
                                    eff_to = datetime.strptime(str(matched_in_bundle["effective_to"]), "%Y-%m-%d").date()
                            elif matched_in_db:
                                eff_from = matched_in_db.effective_from
                                eff_to = matched_in_db.effective_to

                            if eff_from and inc_date < eff_from:
                                issues.append(ValidationErrorItem(
                                    field_name="incident_date",
                                    error_code="INCIDENT_BEFORE_POLICY_START",
                                    severity=ValidationSeverity.ERROR,
                                    message=f"Incident date ({inc_date}) is prior to policy start ({eff_from}).",
                                    received_value=str(inc_date)
                                ))
                            if eff_to and inc_date > eff_to:
                                issues.append(ValidationErrorItem(
                                    field_name="incident_date",
                                    error_code="INCIDENT_AFTER_POLICY_EXPIRY",
                                    severity=ValidationSeverity.ERROR,
                                    message=f"Incident date ({inc_date}) is after policy expiration ({eff_to}).",
                                    received_value=str(inc_date)
                                ))
                        except (ValueError, TypeError):
                            pass

        # 2. Invoice -> Claim reference
        elif record_type == "INVOICE":
            cid = payload.get("claim_id")
            if cid:
                staged_claims = staged_records_by_type.get("CLAIM", [])
                in_bundle = any(str(c.get("normalised_payload", {}).get("claim_id")) == str(cid) for c in staged_claims)
                in_db = False if in_bundle else (db.query(Claim).filter(Claim.claim_id == str(cid)).first() is not None)
                if not in_bundle and not in_db:
                    issues.append(ValidationErrorItem(
                        field_name="claim_id",
                        error_code="UNRESOLVED_CLAIM_REFERENCE",
                        severity=ValidationSeverity.ERROR,
                        message=f"Referenced claim '{cid}' does not exist in bundle or database.",
                        received_value=str(cid)
                    ))

        # 3. Invoice Line Item -> Invoice reference
        elif record_type == "INVOICE_LINE_ITEM":
            inv_id = payload.get("invoice_id")
            inv_ref = payload.get("invoice_reference")
            if not inv_id and not inv_ref:
                issues.append(ValidationErrorItem(
                    field_name="invoice_id",
                    error_code="MISSING_INVOICE_REFERENCE",
                    severity=ValidationSeverity.ERROR,
                    message="Invoice line item must reference an invoice ID or invoice reference.",
                    received_value=None
                ))
            else:
                staged_invoices = staged_records_by_type.get("INVOICE", [])
                in_bundle = any(
                    (inv_id and str(i.get("normalised_payload", {}).get("invoice_id")) == str(inv_id)) or
                    (inv_ref and str(i.get("normalised_payload", {}).get("invoice_reference")) == str(inv_ref))
                    for i in staged_invoices
                )
                in_db = False
                if not in_bundle:
                    q = db.query(Invoice)
                    if inv_id:
                        in_db = q.filter(Invoice.invoice_id == str(inv_id)).first() is not None
                    elif inv_ref:
                        in_db = q.filter(Invoice.invoice_reference == str(inv_ref)).first() is not None
                
                if not in_bundle and not in_db:
                    issues.append(ValidationErrorItem(
                        field_name="invoice_id",
                        error_code="UNRESOLVED_INVOICE_REFERENCE",
                        severity=ValidationSeverity.ERROR,
                        message=f"Referenced invoice '{inv_id or inv_ref}' does not exist in bundle or database.",
                        received_value=str(inv_id or inv_ref)
                    ))

        # 4. Settlement -> Claim reference
        elif record_type == "SETTLEMENT":
            cid = payload.get("claim_id")
            if cid:
                staged_claims = staged_records_by_type.get("CLAIM", [])
                in_bundle = any(str(c.get("normalised_payload", {}).get("claim_id")) == str(cid) for c in staged_claims)
                in_db = False if in_bundle else (db.query(Claim).filter(Claim.claim_id == str(cid)).first() is not None)
                if not in_bundle and not in_db:
                    issues.append(ValidationErrorItem(
                        field_name="claim_id",
                        error_code="UNRESOLVED_CLAIM_REFERENCE",
                        severity=ValidationSeverity.ERROR,
                        message=f"Settlement referenced claim '{cid}' which does not exist in bundle or database.",
                        received_value=str(cid)
                    ))

        # 5. Claim History -> Claim reference
        elif record_type == "CLAIM_HISTORY":
            cid = payload.get("claim_id")
            if cid:
                staged_claims = staged_records_by_type.get("CLAIM", [])
                in_bundle = any(str(c.get("normalised_payload", {}).get("claim_id")) == str(cid) for c in staged_claims)
                in_db = False if in_bundle else (db.query(Claim).filter(Claim.claim_id == str(cid)).first() is not None)
                if not in_bundle and not in_db:
                    issues.append(ValidationErrorItem(
                        field_name="claim_id",
                        error_code="UNRESOLVED_CLAIM_REFERENCE",
                        severity=ValidationSeverity.ERROR,
                        message=f"Claim history referenced claim '{cid}' which does not exist in bundle or database.",
                        received_value=str(cid)
                    ))

        return issues

    @staticmethod
    def validate_invoice_totals_cross_check(
        staged_invoices: List[Dict[str, Any]],
        staged_lines: List[Dict[str, Any]]
    ) -> Dict[str, List[ValidationErrorItem]]:
        """
        Cross-checks invoice total_amount against sum of corresponding line items.
        Returns a mapping of invoice_id -> list of ValidationErrorItems.
        """
        results: Dict[str, List[ValidationErrorItem]] = {}
        
        # Group lines by invoice_id and invoice_reference
        lines_by_inv_id: Dict[str, Decimal] = {}
        for l in staged_lines:
            payload = l.get("normalised_payload", {})
            inv_id = payload.get("invoice_id") or payload.get("invoice_reference")
            line_amt = payload.get("line_amount")
            if inv_id and line_amt:
                try:
                    amt = Decimal(str(line_amt))
                    lines_by_inv_id[str(inv_id)] = lines_by_inv_id.get(str(inv_id), Decimal("0")) + amt
                except Exception:
                    pass

        for inv in staged_invoices:
            inv_payload = inv.get("normalised_payload", {})
            inv_id = inv_payload.get("invoice_id")
            inv_ref = inv_payload.get("invoice_reference")
            rec_id = inv.get("staging_record_id")
            
            total_amt_str = inv_payload.get("total_amount")
            if not total_amt_str:
                continue

            try:
                total_amt = Decimal(str(total_amt_str))
            except Exception:
                continue

            # Find matching sum of lines
            sum_lines = lines_by_inv_id.get(str(inv_id)) or lines_by_inv_id.get(str(inv_ref))
            if sum_lines is not None:
                diff = abs(total_amt - sum_lines)
                if diff > Decimal(str(settings.AMOUNT_TOLERANCE)):
                    results[rec_id] = [ValidationErrorItem(
                        field_name="total_amount",
                        error_code="INVOICE_TOTAL_MISMATCH",
                        severity=ValidationSeverity.ERROR,
                        message=f"Invoice total amount ({total_amt}) does not match sum of its line items ({sum_lines}). Diff: {diff}",
                        received_value=str(total_amt)
                    )]

        return results
