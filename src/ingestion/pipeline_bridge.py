"""Map canonical claims-ingestion DB records into studio Claim objects."""

from typing import Any, Optional

from src.schemas import Claim, Claimant, IncidentDetails, LineItem, PriorClaimRecord


def _as_date_str(value: Any) -> str:
    if value is None:
        return "2024-01-01"
    return str(value)[:10]


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def map_pipeline_claim_to_studio(db_claim: Any) -> Claim:
    """Convert a SQLAlchemy canonical Claim into the leakage-studio Claim schema."""
    policy = getattr(db_claim, "policy", None)
    policy_id = "POL-COMPREHENSIVE-01"
    if policy is not None:
        raw_policy = str(policy.policy_number or policy.policy_id or "")
        if raw_policy.startswith("POL-COMPREHENSIVE") or raw_policy.startswith("POL-BASIC"):
            policy_id = raw_policy

    invoices = list(getattr(db_claim, "invoices", None) or [])
    first_invoice = invoices[0] if invoices else None
    provider = getattr(first_invoice, "provider", None) if first_invoice else None
    hospital_id = getattr(provider, "provider_id", None) or "HOSP-001"
    hospital_name = getattr(provider, "provider_name", None) or hospital_id

    line_items = []
    for inv in invoices:
        for idx, li in enumerate(list(getattr(inv, "line_items", None) or []), start=1):
            qty = _as_float(li.quantity, 1.0) or 1.0
            unit_price = _as_float(li.unit_price)
            total = _as_float(li.line_amount, qty * unit_price)
            line_items.append(
                LineItem(
                    line_id=str(li.line_item_id or f"L{idx}"),
                    category=(li.category or "GENERAL").upper(),
                    item_code=li.service_code or f"ITEM-{idx:02d}",
                    description=li.description or "Imported line item",
                    quantity=qty,
                    unit_price=unit_price,
                    total_amount=total,
                    service_date=_as_date_str(getattr(inv, "invoice_date", None)),
                )
            )

    requested = _as_float(db_claim.requested_amount)
    if not line_items and requested > 0:
        line_items.append(
            LineItem(
                line_id="L1",
                category="GENERAL",
                item_code="ITEM-01",
                description="Imported claim amount",
                quantity=1.0,
                unit_price=requested,
                total_amount=requested,
                service_date=_as_date_str(db_claim.incident_date),
            )
        )

    proposed = requested
    settlements = list(getattr(db_claim, "settlements", None) or [])
    if settlements:
        proposed = _as_float(settlements[0].approved_amount, requested)

    history = []
    for h in list(getattr(db_claim, "history_events", None) or []):
        history.append(
            PriorClaimRecord(
                previous_claim_id=str(h.history_id or db_claim.claim_id),
                admission_date=_as_date_str(h.event_date),
                diagnosis=h.event_description or h.event_type or "Prior event",
                hospital_name=hospital_name,
                paid_amount=_as_float(h.amount),
                settlement_status=h.event_type or "RECORDED",
                invoice_number=h.source_reference,
            )
        )

    invoice_number: Optional[str] = getattr(first_invoice, "invoice_reference", None)
    invoice_date: Optional[str] = _as_date_str(getattr(first_invoice, "invoice_date", None)) if first_invoice else None

    return Claim(
        claim_id=db_claim.claim_id,
        case_title=f"Pipeline import {db_claim.claim_id}",
        policy_id=str(policy_id),
        claimant=Claimant(
            claimant_id=db_claim.claimant_id or "C-001",
            name=db_claim.claimant_name or "Unknown Claimant",
            relationship_to_insured="SELF",
            age=35,
        ),
        incident_details=IncidentDetails(
            admission_date=_as_date_str(db_claim.incident_date),
            discharge_date=_as_date_str(db_claim.incident_date),
            hospital_id=str(hospital_id),
            hospital_name=hospital_name,
            diagnosis_description=f"{db_claim.claim_type or 'CLAIM'} via ingestion pipeline",
            policy_tenure_months=12,
            is_pre_existing=False,
            proposed_settlement_amount=proposed,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
        ),
        line_items=line_items,
        claim_history=history,
    )
