from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.persistence.database import get_db
from app.persistence.models.claim_models import Claim, Policy, Invoice, InvoiceLineItem, Settlement, ClaimHistory

router = APIRouter(prefix="/claims", tags=["Claims"])

@router.get("/{claim_id}")
def get_claim(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve an imported claim from the canonical operational database."""
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found in canonical database.")

    policy = claim.policy
    invoices_data = []
    for inv in claim.invoices:
        lines = [
            {
                "line_item_id": li.line_item_id,
                "service_code": li.service_code,
                "description": li.description,
                "category": li.category,
                "quantity": float(li.quantity),
                "unit_price": float(li.unit_price),
                "line_amount": float(li.line_amount)
            }
            for li in inv.line_items
        ]
        invoices_data.append({
            "invoice_id": inv.invoice_id,
            "invoice_reference": inv.invoice_reference,
            "invoice_date": str(inv.invoice_date),
            "provider_id": inv.provider_id,
            "total_amount": float(inv.total_amount),
            "currency": inv.currency,
            "line_items": lines
        })

    settlements_data = [
        {
            "settlement_id": s.settlement_id,
            "approved_amount": float(s.approved_amount),
            "paid_amount": float(s.paid_amount),
            "settlement_date": str(s.settlement_date),
            "settlement_status": s.settlement_status,
            "currency": s.currency
        }
        for s in claim.settlements
    ]

    history_data = [
        {
            "history_id": h.history_id,
            "event_type": h.event_type,
            "event_date": str(h.event_date),
            "event_description": h.event_description,
            "amount": float(h.amount) if h.amount else None,
            "source_reference": h.source_reference
        }
        for h in claim.history_events
    ]

    return {
        "claim_id": claim.claim_id,
        "policy": {
            "policy_id": policy.policy_id if policy else None,
            "policy_number": policy.policy_number if policy else None,
            "effective_from": str(policy.effective_from) if policy else None,
            "effective_to": str(policy.effective_to) if policy else None,
            "sum_insured": float(policy.sum_insured) if policy else None,
            "currency": policy.currency if policy else "INR"
        } if policy else None,
        "claimant_id": claim.claimant_id,
        "claimant_name": claim.claimant_name,
        "incident_date": str(claim.incident_date),
        "claim_type": claim.claim_type,
        "requested_amount": float(claim.requested_amount),
        "currency": claim.currency,
        "claim_status": claim.claim_status,
        "created_at": str(claim.created_at),
        "invoices": invoices_data,
        "settlements": settlements_data,
        "history": history_data
    }
