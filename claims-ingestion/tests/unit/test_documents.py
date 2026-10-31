import os
import pytest
from app.ingestion.documents.field_extractor import DocumentFieldExtractor
from app.ingestion.documents.tesseract_provider import TesseractProvider
from app.ingestion.documents.pdf_extractor import PDFExtractor

def test_document_field_extractor():
    sample_text = """
    CITY CARE HOSPITAL
    Tax Invoice / Bill No: INV-DOC-992
    Claim Ref: CLM-1001
    Date: 2024-03-18
    Bed Charges 2 5000.00 10000.00
    Total Amount: 10000.00
    """
    fields = DocumentFieldExtractor.extract_candidate_fields(sample_text)
    assert fields["invoice_reference"] in ["INV-DOC-992", "INV-DOC-992"]
    assert fields["claim_id"] in ["CLM-1001", "CLM-1001"]
    assert fields["total_amount"] == "10000.00"
    assert "CITY CARE HOSPITAL" in fields["provider_name"]

def test_pdf_extractor_sample():
    doc_path = "/Users/meherchand/.gemini/antigravity/scratch/claims-ingestion/sample_data/documents/hospital_bill.pdf"
    if os.path.exists(doc_path):
        extractor = PDFExtractor()
        results = extractor.extract_text_and_pages(doc_path)
        assert len(results) > 0
        assert results[0]["page"] == 1
