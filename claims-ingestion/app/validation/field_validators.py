from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.domain.enums import ValidationSeverity, ClaimType

class ValidationErrorItem(BaseModel):
    field_name: Optional[str] = None
    error_code: str
    severity: ValidationSeverity
    message: str
    received_value: Optional[str] = None

class FieldValidator:
    MANDATORY_FIELDS = {
        "CLAIM": [
            ("claim_id", "Claim ID is required."),
            ("claimant_name", "Claimant name is required."),
            ("incident_date", "Incident date is required."),
            ("requested_amount", "Requested amount is required."),
            ("claim_type", "Claim type is required."),
        ],
        "POLICY": [
            ("policy_number", "Policy number is required."),
            ("effective_from", "Policy effective from date is required."),
            ("effective_to", "Policy effective to date is required."),
            ("sum_insured", "Policy sum insured is required."),
        ],
        "INVOICE": [
            ("invoice_id", "Invoice ID is required."),
            ("claim_id", "Claim ID is required on invoice."),
            ("invoice_reference", "Invoice reference/number is required."),
            ("invoice_date", "Invoice date is required."),
            ("total_amount", "Invoice total amount is required."),
        ],
        "INVOICE_LINE_ITEM": [
            ("line_item_id", "Line item ID is required."),
            ("description", "Line item description is required."),
            ("quantity", "Quantity is required."),
            ("unit_price", "Unit price is required."),
            ("line_amount", "Line amount is required."),
        ],
        "PROVIDER": [
            ("provider_id", "Provider ID is required."),
            ("provider_name", "Provider name is required."),
        ],
        "SETTLEMENT": [
            ("settlement_id", "Settlement ID is required."),
            ("claim_id", "Claim ID is required."),
            ("approved_amount", "Approved amount is required."),
            ("paid_amount", "Paid amount is required."),
            ("settlement_date", "Settlement date is required."),
            ("settlement_status", "Settlement status is required."),
        ],
        "CLAIM_HISTORY": [
            ("claim_id", "Claim ID is required."),
            ("event_type", "Event type is required."),
            ("event_date", "Event date is required."),
            ("event_description", "Event description is required."),
        ],
    }

    @staticmethod
    def validate_mandatory(record_type: str, payload: Dict[str, Any]) -> List[ValidationErrorItem]:
        issues = []
        rules = FieldValidator.MANDATORY_FIELDS.get(record_type, [])
        for field, msg in rules:
            val = payload.get(field)
            if val is None or str(val).strip() == "":
                issues.append(ValidationErrorItem(
                    field_name=field,
                    error_code="MANDATORY_FIELD_MISSING",
                    severity=ValidationSeverity.ERROR,
                    message=msg,
                    received_value=str(val) if val is not None else None
                ))
        return issues

    @staticmethod
    def validate_claim_type(payload: Dict[str, Any]) -> List[ValidationErrorItem]:
        issues = []
        c_type = payload.get("claim_type")
        if c_type:
            valid_types = {t.value for t in ClaimType}
            if str(c_type).upper() not in valid_types:
                issues.append(ValidationErrorItem(
                    field_name="claim_type",
                    error_code="UNSUPPORTED_CLAIM_TYPE",
                    severity=ValidationSeverity.ERROR,
                    message=f"Claim type '{c_type}' is unsupported. Must be one of: {list(valid_types)}",
                    received_value=str(c_type)
                ))
        return issues
