"""
Unit and Integration Tests for Document and Invoice Analysis Engine (Level 2 Step 2).
"""

import json
from pathlib import Path
import pytest
from src.investigation import document_analyzer, VarianceType

STEP2_DIR = Path(__file__).resolve().parent.parent / "data" / "jury_examples" / "Step_2_Document_Analysis"


@pytest.fixture
def hospital_invoice_text():
    with open(STEP2_DIR / "hospital_tax_invoice_saket.txt", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def discharge_summary_text():
    with open(STEP2_DIR / "clinical_discharge_summary.txt", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def sample_claim_record():
    with open(STEP2_DIR / "claim_for_document_audit.json", "r", encoding="utf-8") as f:
        return json.load(f)[0]


def test_document_extraction_invoice(hospital_invoice_text):
    doc_data = document_analyzer.parse_document("hospital_tax_invoice_saket.txt", hospital_invoice_text)
    assert doc_data["document_type"] == "HOSPITAL_TAX_INVOICE"
    assert doc_data["invoice_number"] == "INV-MAX-2026-881"
    assert doc_data["total_invoiced_amount"] == 135000.0
    assert "Vivek Singhania" in doc_data["patient_name"]
    assert str(doc_data["admission_date"]) == "2026-08-10"
    assert str(doc_data["discharge_date"]) == "2026-08-14"
    assert len(doc_data["line_items"]) == 7

    # Verify source citation
    assert doc_data["total_amount_cite"] is not None
    assert doc_data["total_amount_cite"].line_number is not None
    assert "135,000.00" in doc_data["total_amount_cite"].raw_quote


def test_document_extraction_discharge_summary(discharge_summary_text):
    doc_data = document_analyzer.parse_document("clinical_discharge_summary.txt", discharge_summary_text)
    assert doc_data["document_type"] == "CLINICAL_DISCHARGE_SUMMARY"
    assert "Vivek Singhania" in doc_data["patient_name"]
    assert str(doc_data["admission_date"]) == "2026-08-10"
    assert str(doc_data["discharge_date"]) == "2026-08-13"
    assert "Appendicitis" in doc_data["diagnosis"]
    assert doc_data["icd10_code"] == "K35.8"


def test_reconciliation_total_amount_and_rate_inflation(sample_claim_record, hospital_invoice_text):
    report = document_analyzer.compare(
        sample_claim_record, "hospital_tax_invoice_saket.txt", hospital_invoice_text
    )

    assert report.total_variances_detected >= 3
    assert report.summary_verdict == "CRITICAL_DISCREPANCY_DETECTED"

    # 1. Total amount mismatch: 145,000 claimed vs 135,000 invoiced = 10,000 variance
    amt_diff = next(
        fc for fc in report.field_comparisons if fc.variance_type == VarianceType.TOTAL_AMOUNT_MISMATCH
    )
    assert amt_diff.variance_amount == 10000.0
    assert amt_diff.severity == "CRITICAL"
    assert "135,000.00" in amt_diff.source_citation.raw_quote

    # 2. Rate inflation: Surgeon fee 80,000 claimed vs 70,000 on bill = 10,000 excess
    surg_line = next(
        lr for lr in report.line_item_reconciliations if lr.claim_line_id == "L2"
    )
    assert surg_line.status == "RATE_INFLATED"
    assert surg_line.discrepancy_amount == 10000.0
    assert surg_line.claim_unit_rate == 80000.0
    assert surg_line.document_unit_rate == 70000.0
    assert surg_line.source_citation.line_number is not None

    # 3. Unsubstantiated line item: L7 Rehab session 10,000 not on hospital bill
    rehab_line = next(
        lr for lr in report.line_item_reconciliations if lr.claim_line_id == "L7"
    )
    assert rehab_line.status == "UNSUBSTANTIATED_IN_CLAIM"
    assert rehab_line.discrepancy_amount == 10000.0
    assert "NOT FOUND" in rehab_line.source_citation.raw_quote


def test_reconciliation_discharge_date_variance(sample_claim_record, discharge_summary_text):
    report = document_analyzer.compare(
        sample_claim_record, "clinical_discharge_summary.txt", discharge_summary_text
    )

    date_diff = next(
        fc for fc in report.field_comparisons if fc.variance_type == VarianceType.DATE_MISMATCH
    )
    assert date_diff.claim_value == "2026-08-14"
    assert date_diff.document_value == "2026-08-13"
    assert date_diff.severity == "HIGH"
    assert "Discharge Date: 2026-08-13" in date_diff.source_citation.raw_quote

