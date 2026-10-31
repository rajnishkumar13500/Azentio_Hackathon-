import os
import tempfile
import pytest
import openpyxl
from app.ingestion.parsers.csv_parser import CSVParser
from app.ingestion.parsers.excel_parser import ExcelParser
from app.ingestion.parsers.json_parser import JSONParser

def test_csv_parser_valid():
    parser = CSVParser()
    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f:
        f.write("claim_id,policy_number,claimant_name,incident_date,requested_amount\n")
        f.write("CLM-001,POL-100,Ravi Kumar,2024-05-01,15000.00\n")
        f.write("CLM-002,POL-100,Anita Roy,2024-05-02,25000.00\n")
        f.flush()
        
        res = parser.parse(f.name, "claims.csv")
        assert res.success is True
        assert len(res.records) == 2
        assert res.records[0].raw_payload["claim_id"] == "CLM-001"
        assert res.records[1].raw_payload["claimant_name"] == "Anita Roy"
    os.remove(f.name)

def test_csv_parser_empty_and_blank_rows():
    parser = CSVParser()
    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f:
        f.write("claim_id,policy_number\n")
        f.write("CLM-001,POL-100\n")
        f.write("  ,  \n")  # Blank row
        f.flush()

        res = parser.parse(f.name, "claims.csv")
        assert res.success is True
        assert len(res.records) == 2
        assert res.records[1].is_skipped is True
        assert "Blank" in res.records[1].skip_reason
    os.remove(f.name)

def test_excel_parser_multiple_sheets():
    parser = ExcelParser()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "Claims"
        ws1.append(["claim_id", "policy_number", "requested_amount"])
        ws1.append(["CLM-001", "POL-100", "50000.00"])

        ws2 = wb.create_sheet(title="Invoices")
        ws2.append(["invoice_id", "claim_id", "total_amount"])
        ws2.append(["INV-001", "CLM-001", "50000.00"])
        wb.save(f.name)

        res = parser.parse(f.name, "bundle.xlsx")
        assert res.success is True
        assert len(res.records) == 2
        assert any(r.record_type_hint == "CLAIM" for r in res.records)
        assert any(r.record_type_hint == "INVOICE" for r in res.records)
    os.remove(f.name)

def test_json_parser_array_and_collections():
    parser = JSONParser()
    # Test array
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f:
        f.write('[{"claim_id": "CLM-01", "requested_amount": "10000.00"}]')
        f.flush()
        res_arr = parser.parse(f.name, "claims.json")
        assert res_arr.success is True
        assert len(res_arr.records) == 1
    os.remove(f.name)

    # Test collections object
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f:
        f.write('{"claims": [{"claim_id": "CLM-02"}], "providers": [{"provider_id": "PRV-01", "provider_name": "Apollo"}]}')
        f.flush()
        res_obj = parser.parse(f.name, "bundle.json")
        assert res_obj.success is True
        assert len(res_obj.records) == 2
        assert "CLAIM" in res_obj.detected_record_types
        assert "PROVIDER" in res_obj.detected_record_types
    os.remove(f.name)
