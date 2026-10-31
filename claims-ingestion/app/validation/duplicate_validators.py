from typing import Dict, Any, List, Set, Tuple
from sqlalchemy.orm import Session
from app.domain.enums import ValidationSeverity
from app.validation.field_validators import ValidationErrorItem
from app.persistence.models.claim_models import Claim, Invoice, Settlement, Policy

class DuplicateValidator:
    @staticmethod
    def check_duplicate_records(
        db: Session,
        all_staged_records: List[Dict[str, Any]]
    ) -> Dict[str, List[ValidationErrorItem]]:
        """
        Scans all staged records for duplicates within bundle and against operational database.
        Returns mapping: staging_record_id -> List[ValidationErrorItem]
        """
        results: Dict[str, List[ValidationErrorItem]] = {}
        
        seen_claim_ids: Dict[str, str] = {}  # claim_id -> staging_record_id
        seen_invoices: Dict[Tuple[str, str], str] = {}  # (provider_id, invoice_reference) -> staging_record_id
        seen_settlement_ids: Dict[str, str] = {}  # settlement_id -> staging_record_id
        seen_policy_numbers: Dict[str, str] = {}  # policy_number -> staging_record_id

        for record in all_staged_records:
            rec_id = record.get("staging_record_id")
            rec_type = record.get("record_type")
            payload = record.get("normalised_payload", {})
            issues: List[ValidationErrorItem] = []

            # 1. Claim Duplicates
            if rec_type == "CLAIM":
                cid = payload.get("claim_id")
                if cid:
                    cid_str = str(cid).strip()
                    if cid_str in seen_claim_ids:
                        prior_id = seen_claim_ids[cid_str]
                        issues.append(ValidationErrorItem(
                            field_name="claim_id",
                            error_code="DUPLICATE_CLAIM_IN_BUNDLE",
                            severity=ValidationSeverity.ERROR,
                            message=f"Duplicate claim ID '{cid_str}' found in current import bundle (first seen in record {prior_id}).",
                            received_value=cid_str
                        ))
                    else:
                        seen_claim_ids[cid_str] = rec_id
                        # Check database
                        existing_claim = db.query(Claim).filter(Claim.claim_id == cid_str).first()
                        if existing_claim:
                            issues.append(ValidationErrorItem(
                                field_name="claim_id",
                                error_code="DUPLICATE_CLAIM_IN_DATABASE",
                                severity=ValidationSeverity.ERROR,
                                message=f"Claim ID '{cid_str}' already exists in canonical database.",
                                received_value=cid_str
                            ))

            # 2. Invoice Duplicates (provider + invoice_reference or invoice_id)
            elif rec_type == "INVOICE":
                prov = payload.get("provider_id") or payload.get("provider_code") or "DEFAULT_PROV"
                inv_ref = payload.get("invoice_reference")
                inv_id = payload.get("invoice_id")
                
                if inv_ref:
                    key = (str(prov).strip(), str(inv_ref).strip())
                    if key in seen_invoices:
                        prior_id = seen_invoices[key]
                        issues.append(ValidationErrorItem(
                            field_name="invoice_reference",
                            error_code="DUPLICATE_INVOICE_IN_BUNDLE",
                            severity=ValidationSeverity.ERROR,
                            message=f"Duplicate invoice reference '{inv_ref}' for provider '{prov}' in bundle (first seen in {prior_id}).",
                            received_value=str(inv_ref)
                        ))
                    else:
                        seen_invoices[key] = rec_id
                        # Check database
                        existing_inv = db.query(Invoice).filter(
                            Invoice.invoice_reference == str(inv_ref)
                        ).first()
                        if existing_inv:
                            issues.append(ValidationErrorItem(
                                field_name="invoice_reference",
                                error_code="DUPLICATE_INVOICE_IN_DATABASE",
                                severity=ValidationSeverity.ERROR,
                                message=f"Invoice reference '{inv_ref}' already exists in database.",
                                received_value=str(inv_ref)
                            ))

            # 3. Settlement Duplicates
            elif rec_type == "SETTLEMENT":
                sid = payload.get("settlement_id")
                if sid:
                    sid_str = str(sid).strip()
                    if sid_str in seen_settlement_ids:
                        prior_id = seen_settlement_ids[sid_str]
                        issues.append(ValidationErrorItem(
                            field_name="settlement_id",
                            error_code="DUPLICATE_SETTLEMENT_IN_BUNDLE",
                            severity=ValidationSeverity.ERROR,
                            message=f"Duplicate settlement ID '{sid_str}' in bundle (first seen in {prior_id}).",
                            received_value=sid_str
                        ))
                    else:
                        seen_settlement_ids[sid_str] = rec_id
                        existing_settle = db.query(Settlement).filter(Settlement.settlement_id == sid_str).first()
                        if existing_settle:
                            issues.append(ValidationErrorItem(
                                field_name="settlement_id",
                                error_code="DUPLICATE_SETTLEMENT_IN_DATABASE",
                                severity=ValidationSeverity.ERROR,
                                message=f"Settlement ID '{sid_str}' already exists in database.",
                                received_value=sid_str
                            ))

            # 4. Policy Duplicates
            elif rec_type == "POLICY":
                pnum = payload.get("policy_number")
                if pnum:
                    pnum_str = str(pnum).strip()
                    if pnum_str in seen_policy_numbers:
                        prior_id = seen_policy_numbers[pnum_str]
                        issues.append(ValidationErrorItem(
                            field_name="policy_number",
                            error_code="DUPLICATE_POLICY_IN_BUNDLE",
                            severity=ValidationSeverity.ERROR,
                            message=f"Duplicate policy number '{pnum_str}' in bundle (first seen in {prior_id}).",
                            received_value=pnum_str
                        ))
                    else:
                        seen_policy_numbers[pnum_str] = rec_id
                        existing_pol = db.query(Policy).filter(Policy.policy_number == pnum_str).first()
                        if existing_pol:
                            issues.append(ValidationErrorItem(
                                field_name="policy_number",
                                error_code="DUPLICATE_POLICY_IN_DATABASE",
                                severity=ValidationSeverity.WARNING,
                                message=f"Policy number '{pnum_str}' already exists in database. Existing policy will be reused.",
                                received_value=pnum_str
                            ))

            if issues:
                results[rec_id] = issues

        return results
