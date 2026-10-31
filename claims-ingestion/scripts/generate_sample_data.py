import os
import csv
import json
import openpyxl
from decimal import Decimal

BASE_SAMPLE_DIR = "/Users/meherchand/.gemini/antigravity/scratch/claims-ingestion/sample_data"

def create_small_dataset():
    small_dir = os.path.join(BASE_SAMPLE_DIR, "small")
    os.makedirs(small_dir, exist_ok=True)

    # 1. Policies CSV
    pol_file = os.path.join(small_dir, "policies.csv")
    with open(pol_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["policy_number", "effective_from", "effective_to", "sum_insured", "currency"])
        writer.writerow(["POL-2024-001", "2024-01-01", "2024-12-31", "500000.00", "INR"])
        writer.writerow(["POL-2024-002", "2024-06-01", "2025-05-31", "1000000.00", "INR"])
        # Intentionally invalid policy period (effective_from > effective_to)
        writer.writerow(["POL-2024-ERR", "2024-12-31", "2024-01-01", "300000.00", "INR"])
        # Blank row to test explicit skipped handling
        writer.writerow(["", "", "", "", ""])

    # 2. Claims CSV
    claims_file = os.path.join(small_dir, "claims.csv")
    with open(claims_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["claim_id", "policy_number", "claimant_id", "claimant_name", "incident_date", "claim_type", "requested_amount", "currency"])
        # Valid Cashless Claim
        writer.writerow(["CLM-1001", "POL-2024-001", "MEM-001", "Aarav Sharma", "2024-03-15", "CASHLESS", "65000.00", "INR"])
        # Valid Reimbursement Claim
        writer.writerow(["CLM-1002", "POL-2024-001", "MEM-002", "Priya Patel", "2024-04-10", "REIMBURSEMENT", "42000.00", "INR"])
        # Valid Claim with legitimate warning (existing policy in DB test case or date warning)
        writer.writerow(["CLM-1003", "POL-2024-002", "MEM-003", "Rahul Verma", "2024-07-20", "CASHLESS", "125000.00", "INR"])
        # Missing Mandatory Claimant Name (Error)
        writer.writerow(["CLM-1004", "POL-2024-001", "MEM-004", "", "2024-05-01", "REIMBURSEMENT", "15000.00", "INR"])
        # Negative Amount (Error)
        writer.writerow(["CLM-1005", "POL-2024-001", "MEM-005", "Sunita Rao", "2024-05-12", "REIMBURSEMENT", "-5000.00", "INR"])
        # Unknown Policy Reference (Error)
        writer.writerow(["CLM-1006", "POL-UNKNOWN-999", "MEM-006", "Vikram Singh", "2024-05-18", "CASHLESS", "30000.00", "INR"])
        # Duplicate Claim ID in bundle (CLM-1001 duplicate)
        writer.writerow(["CLM-1001", "POL-2024-001", "MEM-007", "Duplicate Record", "2024-03-15", "CASHLESS", "65000.00", "INR"])
        # Incident Date after Policy Expiry (Error)
        writer.writerow(["CLM-1007", "POL-2024-001", "MEM-008", "Deepak Gupta", "2025-06-01", "CASHLESS", "40000.00", "INR"])

    # 3. Invoices & Line Items (Excel .xlsx)
    inv_file = os.path.join(small_dir, "invoices_and_lines.xlsx")
    wb = openpyxl.Workbook()
    # Sheet 1: Invoices
    ws_inv = wb.active
    ws_inv.title = "Invoices"
    ws_inv.append(["invoice_id", "claim_id", "provider_id", "invoice_reference", "invoice_date", "total_amount", "currency"])
    ws_inv.append(["INV-001", "CLM-1001", "PROV-HOSP-01", "BILL-2024-101", "2024-03-16", "65000.00", "INR"])
    # Invoice with total amount mismatch vs line items
    ws_inv.append(["INV-002", "CLM-1002", "PROV-HOSP-02", "BILL-2024-102", "2024-04-12", "50000.00", "INR"])  # Lines will sum to 42000
    # Duplicate invoice reference
    ws_inv.append(["INV-003", "CLM-1003", "PROV-HOSP-01", "BILL-2024-101", "2024-07-21", "25000.00", "INR"])

    # Sheet 2: LineItems
    ws_lines = wb.create_sheet(title="LineItems")
    ws_lines.append(["line_item_id", "invoice_id", "service_code", "description", "category", "quantity", "unit_price", "line_amount"])
    # INV-001 lines (sums to 65000)
    ws_lines.append(["LIT-001", "INV-001", "ROOM-01", "Deluxe Room Bed Charges", "ROOM_RENT", "3", "7000.00", "21000.00"])
    ws_lines.append(["LIT-002", "INV-001", "SURG-01", "Surgeon Consultation & Procedure", "SURGERY", "1", "35000.00", "35000.00"])
    ws_lines.append(["LIT-003", "INV-001", "PHARM-01", "Prescribed Inpatient Medication", "PHARMACY", "1", "9000.00", "9000.00"])

    # INV-002 lines (sums to 42000, mismatching invoice header of 50000)
    ws_lines.append(["LIT-004", "INV-002", "ROOM-02", "Standard Room Charges", "ROOM_RENT", "2", "6000.00", "12000.00"])
    ws_lines.append(["LIT-005", "INV-002", "SURG-02", "Minor Surgical Assistance", "SURGERY", "1", "30000.00", "30000.00"])
    # Line item with arithmetic mismatch (qty=2, price=1000, but line_amount=5000)
    ws_lines.append(["LIT-006", "INV-003", "MISC-01", "Administrative Processing Fee", "MISC", "2", "1000.00", "5000.00"])

    wb.save(inv_file)

    # 4. Providers & Settlements JSON
    extra_json = os.path.join(small_dir, "settlements_and_providers.json")
    json_data = {
        "providers": [
            {
                "provider_id": "PROV-HOSP-01",
                "provider_name": "Apollo City Hospital",
                "provider_code": "APOLLO-01",
                "provider_type": "TERTIARY_CARE",
                "address": "42 Bannerghatta Road, Bangalore"
            },
            {
                "provider_id": "PROV-HOSP-02",
                "provider_name": "Fortis Multispeciality",
                "provider_code": "FORTIS-02",
                "provider_type": "SECONDARY_CARE",
                "address": "15 Cunningham Road, Bangalore"
            }
        ],
        "settlements": [
            {
                "settlement_id": "SET-001",
                "claim_id": "CLM-1001",
                "approved_amount": "55000.00",
                "paid_amount": "55000.00",
                "settlement_date": "2024-03-20",
                "settlement_status": "PAID",
                "currency": "INR"
            },
            {
                # Unknown claim reference test case
                "settlement_id": "SET-002",
                "claim_id": "CLM-UNKNOWN-888",
                "approved_amount": "10000.00",
                "paid_amount": "10000.00",
                "settlement_date": "2024-04-15",
                "settlement_status": "PAID",
                "currency": "INR"
            }
        ],
        "history": [
            {
                "claim_id": "CLM-1001",
                "event_type": "ADMISSION",
                "event_date": "2024-03-15",
                "event_description": "Patient admitted for elective procedure."
            },
            {
                "claim_id": "CLM-1001",
                "event_type": "SETTLEMENT",
                "event_date": "2024-03-20",
                "event_description": "Initial settlement processed after policy deductible deduction.",
                "amount": "55000.00"
            }
        ]
    }
    with open(extra_json, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    print("Small synthetic dataset generated successfully.")

def create_large_dataset():
    large_dir = os.path.join(BASE_SAMPLE_DIR, "large")
    os.makedirs(large_dir, exist_ok=True)

    # 1. Policies CSV (10 policies)
    pol_file = os.path.join(large_dir, "policies.csv")
    with open(pol_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["policy_number", "effective_from", "effective_to", "sum_insured", "currency"])
        for i in range(1, 11):
            writer.writerow([f"POL-2024-{i:03d}", "2024-01-01", "2024-12-31", f"{i * 200000}.00", "INR"])

    # 2. Claims CSV (50 claims)
    claims_file = os.path.join(large_dir, "claims.csv")
    with open(claims_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["claim_id", "policy_number", "claimant_id", "claimant_name", "incident_date", "claim_type", "requested_amount", "currency"])
        for i in range(1, 51):
            pol_idx = ((i - 1) % 10) + 1
            claim_type = "CASHLESS" if i % 2 == 0 else "REIMBURSEMENT"
            amt = f"{(i * 3500) + 12000}.00"
            writer.writerow([f"CLM-{2000+i}", f"POL-2024-{pol_idx:03d}", f"MEM-{100+i}", f"Patient {i}", "2024-05-10", claim_type, amt, "INR"])

    # 3. Invoices & Line Items JSON
    inv_file = os.path.join(large_dir, "invoices.json")
    invoices = []
    line_items = []
    for i in range(1, 51):
        inv_id = f"INV-L-{i:03d}"
        claim_id = f"CLM-{2000+i}"
        total = (i * 3500) + 12000
        invoices.append({
            "invoice_id": inv_id,
            "claim_id": claim_id,
            "provider_id": "PROV-HOSP-01",
            "invoice_reference": f"BILL-L-{i:04d}",
            "invoice_date": "2024-05-11",
            "total_amount": f"{total}.00",
            "currency": "INR"
        })
        line_items.append({
            "line_item_id": f"LIT-L-{i:03d}",
            "invoice_id": inv_id,
            "service_code": "GEN-01",
            "description": f"Hospitalization & Clinical Care {i}",
            "quantity": "1",
            "unit_price": f"{total}.00",
            "line_amount": f"{total}.00"
        })

    with open(inv_file, "w", encoding="utf-8") as f:
        json.dump({"invoices": invoices, "line_items": line_items}, f, indent=2)

    print("Large synthetic dataset generated successfully.")

if __name__ == "__main__":
    create_small_dataset()
    create_large_dataset()
