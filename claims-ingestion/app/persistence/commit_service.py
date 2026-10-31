import json
import uuid
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.domain.enums import ImportJobStatus, StagingRecordStatus
from app.domain.schemas.import_schemas import CommitRequest, CommitResponse
from app.persistence.models.import_models import ImportJob, StagingRecord
from app.persistence.models.claim_models import (
    Policy, PolicyCoverage, PolicyExclusion, PolicyBenefit,
    Provider, Claim, Invoice, InvoiceLineItem,
    ClaimHistory, Settlement, ClaimDocument
)
from app.audit.audit_service import AuditService

class CommitService:
    @staticmethod
    def commit_import(
        db: Session,
        import_id: str,
        commit_request: CommitRequest,
        actor: str = "user"
    ) -> CommitResponse:
        job = db.query(ImportJob).filter(ImportJob.import_id == import_id).first()
        if not job:
            raise ValueError(f"Import job {import_id} not found")

        # Idempotency check: if job is already completed
        if job.status in [ImportJobStatus.COMPLETED.value, ImportJobStatus.COMPLETED_WITH_REJECTIONS.value]:
            return CommitResponse(
                import_id=import_id,
                status=job.status,
                imported_records=job.imported_records,
                rejected_records=job.failed_records,
                failed_records=0,
                message="Import job was already committed. Idempotent response returned.",
                details={"completed_at": str(job.completed_at)}
            )

        if not commit_request.confirm:
            raise ValueError("Explicit user confirmation (confirm=True) is required to commit.")

        # Ensure job is ready
        valid_statuses = [
            ImportJobStatus.READY_TO_COMMIT.value,
            ImportJobStatus.VALIDATION_COMPLETED.value
        ]
        if job.status not in valid_statuses:
            raise ValueError(f"Cannot commit import in status '{job.status}'. Must run validation first.")

        # Lock in commit token for retry safety
        commit_token = commit_request.commit_token or str(uuid.uuid4())
        if job.commit_token and job.commit_token != commit_token:
            raise ValueError("Import job already has an active commit operation with a different token.")
        job.commit_token = commit_token
        job.status = ImportJobStatus.COMMITTING.value
        db.commit()

        # Fetch all staging records
        query = db.query(StagingRecord).filter(StagingRecord.import_id == import_id)
        if commit_request.include_record_ids:
            query = query.filter(StagingRecord.staging_record_id.in_(commit_request.include_record_ids))
        if commit_request.exclude_record_ids:
            query = query.filter(~StagingRecord.staging_record_id.in_(commit_request.exclude_record_ids))

        records = query.all()

        # Filter eligible records
        eligible_records: List[StagingRecord] = []
        rejected_records: List[StagingRecord] = []

        warning_count = 0
        for r in records:
            if r.processing_status == StagingRecordStatus.VALID.value and commit_request.include_valid:
                eligible_records.append(r)
            elif r.processing_status == StagingRecordStatus.WARNING.value:
                warning_count += 1
                if commit_request.include_reviewed_warnings:
                    eligible_records.append(r)
                else:
                    rejected_records.append(r)
            else:
                # INVALID, DUPLICATE, PENDING_REVIEW, SKIPPED are never committed
                rejected_records.append(r)

        # Check warnings acknowledgment
        if warning_count > 0 and commit_request.acknowledged_warning_count < warning_count:
            job.status = ImportJobStatus.VALIDATION_COMPLETED.value
            db.commit()
            raise ValueError(
                f"Commit blocked: {warning_count} records have warnings, but only {commit_request.acknowledged_warning_count} were acknowledged."
            )

        # Transactional commit
        imported_count = 0
        try:
            # Group eligible records by type
            by_type: Dict[str, List[StagingRecord]] = {}
            for r in eligible_records:
                by_type.setdefault(r.record_type, []).append(r)

            # 1. Insert Providers
            for r in by_type.get("PROVIDER", []):
                p = json.loads(r.normalised_payload)
                prov_id = p.get("provider_id")
                if not db.query(Provider).filter(Provider.provider_id == prov_id).first():
                    prov = Provider(
                        provider_id=prov_id,
                        provider_name=p.get("provider_name"),
                        provider_code=p.get("provider_code"),
                        provider_type=p.get("provider_type"),
                        address=p.get("address"),
                        created_at=datetime.utcnow()
                    )
                    db.add(prov)
                    imported_count += 1

            # 2. Insert Policies
            policy_id_map: Dict[str, str] = {}  # policy_number -> policy_id
            for r in by_type.get("POLICY", []):
                p = json.loads(r.normalised_payload)
                p_num = p.get("policy_number")
                existing = db.query(Policy).filter(Policy.policy_number == p_num).first()
                if existing:
                    policy_id_map[p_num] = existing.policy_id
                else:
                    pol = Policy(
                        policy_id=p.get("policy_id") or str(uuid.uuid4()),
                        policy_number=p_num,
                        effective_from=datetime.strptime(p["effective_from"], "%Y-%m-%d").date(),
                        effective_to=datetime.strptime(p["effective_to"], "%Y-%m-%d").date(),
                        sum_insured=Decimal(str(p["sum_insured"])),
                        currency=p.get("currency", "INR"),
                        created_at=datetime.utcnow()
                    )
                    db.add(pol)
                    policy_id_map[p_num] = pol.policy_id
                    imported_count += 1

            # Flush to ensure policies exist for FK constraints
            db.flush()

            # 3. Insert Claims
            claim_ids_seen = set()
            for r in by_type.get("CLAIM", []):
                p = json.loads(r.normalised_payload)
                cid = p.get("claim_id")
                
                # Resolve policy ID
                pol_ref = p.get("policy_number") or p.get("policy_id")
                pol_id = policy_id_map.get(pol_ref)
                if not pol_id:
                    # Look up in DB
                    db_pol = db.query(Policy).filter(
                        (Policy.policy_number == pol_ref) | (Policy.policy_id == pol_ref)
                    ).first()
                    if db_pol:
                        pol_id = db_pol.policy_id
                    else:
                        raise ValueError(f"Referenced policy '{pol_ref}' could not be resolved for claim '{cid}'.")

                existing_claim = db.query(Claim).filter(Claim.claim_id == cid).first()
                if not existing_claim and cid not in claim_ids_seen:
                    claim = Claim(
                        claim_id=cid,
                        policy_id=pol_id,
                        claimant_id=p.get("claimant_id") or "UNKNOWN",
                        claimant_name=p.get("claimant_name"),
                        incident_date=datetime.strptime(p["incident_date"], "%Y-%m-%d").date(),
                        claim_type=p.get("claim_type", "REIMBURSEMENT"),
                        requested_amount=Decimal(str(p["requested_amount"])),
                        currency=p.get("currency", "INR"),
                        claim_status="IMPORTED",
                        created_at=datetime.utcnow()
                    )
                    db.add(claim)
                    claim_ids_seen.add(cid)
                    imported_count += 1

            db.flush()

            # 4. Insert Invoices
            inv_ids_seen = set()
            for r in by_type.get("INVOICE", []):
                p = json.loads(r.normalised_payload)
                inv_id = p.get("invoice_id")
                cid = p.get("claim_id")
                prov_id = p.get("provider_id") or p.get("provider_code")

                existing_inv = db.query(Invoice).filter(Invoice.invoice_id == inv_id).first()
                parent_claim = db.query(Claim).filter(Claim.claim_id == cid).first()
                if not parent_claim:
                    continue
                if prov_id and not db.query(Provider).filter(Provider.provider_id == prov_id).first():
                    prov_id = None
                if not existing_inv and inv_id not in inv_ids_seen:
                    invoice = Invoice(
                        invoice_id=inv_id,
                        claim_id=cid,
                        provider_id=prov_id,
                        invoice_reference=p.get("invoice_reference"),
                        invoice_date=datetime.strptime(p["invoice_date"], "%Y-%m-%d").date(),
                        total_amount=Decimal(str(p["total_amount"])),
                        currency=p.get("currency", "INR"),
                        created_at=datetime.utcnow()
                    )
                    db.add(invoice)
                    inv_ids_seen.add(inv_id)
                    imported_count += 1

            db.flush()

            # 5. Insert Invoice Line Items
            for r in by_type.get("INVOICE_LINE_ITEM", []):
                p = json.loads(r.normalised_payload)
                lid = p.get("line_item_id")
                inv_ref = p.get("invoice_id") or p.get("invoice_reference")

                # Resolve invoice ID if needed
                resolved_inv_id = inv_ref
                db_inv = db.query(Invoice).filter(
                    (Invoice.invoice_id == inv_ref) | (Invoice.invoice_reference == inv_ref)
                ).first()
                if not db_inv:
                    continue
                resolved_inv_id = db_inv.invoice_id

                existing_line = db.query(InvoiceLineItem).filter(InvoiceLineItem.line_item_id == lid).first()
                if not existing_line:
                    line = InvoiceLineItem(
                        line_item_id=lid,
                        invoice_id=resolved_inv_id,
                        service_code=p.get("service_code"),
                        description=p.get("description"),
                        category=p.get("category"),
                        quantity=Decimal(str(p["quantity"])),
                        unit_price=Decimal(str(p["unit_price"])),
                        line_amount=Decimal(str(p["line_amount"])),
                        created_at=datetime.utcnow()
                    )
                    db.add(line)
                    imported_count += 1

            # 6. Insert Settlements
            for r in by_type.get("SETTLEMENT", []):
                p = json.loads(r.normalised_payload)
                sid = p.get("settlement_id")
                cid = p.get("claim_id")
                existing_settle = db.query(Settlement).filter(Settlement.settlement_id == sid).first()
                parent_claim = db.query(Claim).filter(Claim.claim_id == cid).first()
                if not parent_claim:
                    continue
                if not existing_settle:
                    settle = Settlement(
                        settlement_id=sid,
                        claim_id=cid,
                        approved_amount=Decimal(str(p["approved_amount"])),
                        paid_amount=Decimal(str(p["paid_amount"])),
                        settlement_date=datetime.strptime(p["settlement_date"], "%Y-%m-%d").date(),
                        settlement_status=p.get("settlement_status", "PAID"),
                        currency=p.get("currency", "INR"),
                        created_at=datetime.utcnow()
                    )
                    db.add(settle)
                    imported_count += 1

            # 7. Insert Claim History
            for r in by_type.get("CLAIM_HISTORY", []):
                p = json.loads(r.normalised_payload)
                cid = p.get("claim_id")
                parent_claim = db.query(Claim).filter(Claim.claim_id == cid).first()
                if not parent_claim:
                    continue
                amt = Decimal(str(p["amount"])) if p.get("amount") else None
                hist = ClaimHistory(
                    history_id=p.get("history_id") or str(uuid.uuid4()),
                    claim_id=cid,
                    event_type=p.get("event_type"),
                    event_date=datetime.strptime(p["event_date"], "%Y-%m-%d").date(),
                    event_description=p.get("event_description"),
                    amount=amt,
                    source_reference=p.get("source_reference"),
                    created_at=datetime.utcnow()
                )
                db.add(hist)
                imported_count += 1

            # Update job status
            job.imported_records = imported_count
            job.failed_records = len(rejected_records)
            job.completed_at = datetime.utcnow()
            if len(rejected_records) > 0:
                job.status = ImportJobStatus.COMPLETED_WITH_REJECTIONS.value
            else:
                job.status = ImportJobStatus.COMPLETED.value

            AuditService.log_event(
                db=db,
                import_id=import_id,
                event_type="IMPORT_COMMITTED",
                actor=actor,
                event_details={
                    "imported_records": imported_count,
                    "rejected_records": len(rejected_records),
                    "commit_token": commit_token
                }
            )

            db.commit()

            return CommitResponse(
                import_id=import_id,
                status=job.status,
                imported_records=imported_count,
                rejected_records=len(rejected_records),
                failed_records=0,
                message="Data successfully committed to operational database.",
                details={
                    "imported": imported_count,
                    "rejected": len(rejected_records),
                    "commit_token": commit_token
                }
            )

        except Exception as e:
            db.rollback()
            job.status = ImportJobStatus.FAILED.value
            job.failure_reason = str(e)
            AuditService.log_event(
                db=db,
                import_id=import_id,
                event_type="COMMIT_FAILED",
                actor=actor,
                event_details={"error": str(e)}
            )
            db.commit()
            raise RuntimeError(f"Database transaction rolled back due to error: {str(e)}")
