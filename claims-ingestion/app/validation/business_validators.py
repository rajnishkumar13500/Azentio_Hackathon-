import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List
from app.domain.enums import ValidationSeverity
from app.validation.field_validators import ValidationErrorItem
from app.config import settings

class BusinessValidator:
    @staticmethod
    def validate_amounts(record_type: str, payload: Dict[str, Any]) -> List[ValidationErrorItem]:
        issues = []
        
        # Check all potential decimal fields
        decimal_fields = [
            "sum_insured", "requested_amount", "total_amount",
            "quantity", "unit_price", "line_amount",
            "approved_amount", "paid_amount", "amount",
            "sub_limit", "deductible", "copay_percentage"
        ]

        parsed_values: Dict[str, Decimal] = {}

        for f in decimal_fields:
            if f in payload and payload[f] is not None and str(payload[f]).strip() != "":
                raw_val = str(payload[f]).strip()
                try:
                    dec_val = Decimal(raw_val)
                    parsed_values[f] = dec_val

                    # Negative amount check (unless specifically allowed)
                    if f != "copay_percentage" and dec_val < Decimal("0"):
                        issues.append(ValidationErrorItem(
                            field_name=f,
                            error_code="NEGATIVE_AMOUNT",
                            severity=ValidationSeverity.ERROR,
                            message=f"Field '{f}' cannot be negative.",
                            received_value=raw_val
                        ))
                    
                    if f == "quantity" and dec_val <= Decimal("0"):
                        issues.append(ValidationErrorItem(
                            field_name="quantity",
                            error_code="INVALID_QUANTITY",
                            severity=ValidationSeverity.ERROR,
                            message="Quantity must be strictly greater than zero.",
                            received_value=raw_val
                        ))

                except (InvalidOperation, ValueError):
                    issues.append(ValidationErrorItem(
                        field_name=f,
                        error_code="INVALID_DECIMAL_FORMAT",
                        severity=ValidationSeverity.ERROR,
                        message=f"Field '{f}' is not a valid decimal number.",
                        received_value=raw_val
                    ))

        # Line item arithmetic: line_amount == quantity * unit_price
        if record_type == "INVOICE_LINE_ITEM":
            if "quantity" in parsed_values and "unit_price" in parsed_values and "line_amount" in parsed_values:
                expected = (parsed_values["quantity"] * parsed_values["unit_price"]).quantize(Decimal("0.01"))
                actual = parsed_values["line_amount"].quantize(Decimal("0.01"))
                diff = abs(expected - actual)
                if diff > Decimal(str(settings.AMOUNT_TOLERANCE)):
                    issues.append(ValidationErrorItem(
                        field_name="line_amount",
                        error_code="LINE_AMOUNT_MISMATCH",
                        severity=ValidationSeverity.ERROR,
                        message=f"Line amount ({actual}) does not match quantity × unit price ({expected}). Diff: {diff}",
                        received_value=str(actual)
                    ))

        return issues

    @staticmethod
    def validate_dates(record_type: str, payload: Dict[str, Any]) -> List[ValidationErrorItem]:
        issues = []
        date_fields = ["incident_date", "effective_from", "effective_to", "invoice_date", "settlement_date", "event_date"]
        parsed_dates: Dict[str, date] = {}

        for df in date_fields:
            if df in payload and payload[df] is not None and str(payload[df]).strip() != "":
                raw_val = str(payload[df]).strip()
                try:
                    dt = datetime.strptime(raw_val, "%Y-%m-%d").date()
                    parsed_dates[df] = dt
                except ValueError:
                    issues.append(ValidationErrorItem(
                        field_name=df,
                        error_code="INVALID_DATE_FORMAT",
                        severity=ValidationSeverity.ERROR,
                        message=f"Field '{df}' is not a valid date in YYYY-MM-DD format.",
                        received_value=raw_val
                    ))

        # Policy date consistency: effective_from <= effective_to
        if record_type == "POLICY":
            if "effective_from" in parsed_dates and "effective_to" in parsed_dates:
                if parsed_dates["effective_from"] > parsed_dates["effective_to"]:
                    issues.append(ValidationErrorItem(
                        field_name="effective_to",
                        error_code="INVALID_POLICY_PERIOD",
                        severity=ValidationSeverity.ERROR,
                        message=f"Policy effective_from ({parsed_dates['effective_from']}) cannot be after effective_to ({parsed_dates['effective_to']}).",
                        received_value=str(parsed_dates["effective_to"])
                    ))

        return issues
