import pytest
from app.validation.field_validators import FieldValidator
from app.validation.business_validators import BusinessValidator
from app.domain.enums import ValidationSeverity

def test_mandatory_claim_id_missing():
    payload = {
        "claimant_name": "John Doe",
        "incident_date": "2024-05-10",
        "requested_amount": "5000.00",
        "claim_type": "CASHLESS"
    }
    issues = FieldValidator.validate_mandatory("CLAIM", payload)
    assert any(i.error_code == "MANDATORY_FIELD_MISSING" and i.field_name == "claim_id" for i in issues)

def test_negative_amount_validation():
    payload = {
        "requested_amount": "-1500.00"
    }
    issues = BusinessValidator.validate_amounts("CLAIM", payload)
    assert any(i.error_code == "NEGATIVE_AMOUNT" for i in issues)

def test_invalid_quantity_validation():
    payload = {
        "quantity": "0",
        "unit_price": "100.00",
        "line_amount": "0.00"
    }
    issues = BusinessValidator.validate_amounts("INVOICE_LINE_ITEM", payload)
    assert any(i.error_code == "INVALID_QUANTITY" for i in issues)

def test_line_amount_arithmetic_mismatch():
    payload = {
        "quantity": "3",
        "unit_price": "200.00",
        "line_amount": "1000.00"  # Expected 600.00
    }
    issues = BusinessValidator.validate_amounts("INVOICE_LINE_ITEM", payload)
    assert any(i.error_code == "LINE_AMOUNT_MISMATCH" for i in issues)

def test_policy_effective_period_validation():
    payload = {
        "effective_from": "2024-12-31",
        "effective_to": "2024-01-01"
    }
    issues = BusinessValidator.validate_dates("POLICY", payload)
    assert any(i.error_code == "INVALID_POLICY_PERIOD" for i in issues)
