"""
Synthetic Claims Data Generator for Claims Leakage & Duplicate Detection
Generates realistic datasets covering:
1. Exact duplicate claims
2. Duplicate line items (Intra-claim & Cross-claim)
3. Near-duplicate claims & line items (typos, date shifts, minor price shifts)
4. Legitimate repeat services (physiotherapy, dialysis - valid lookalikes)
5. Clean, valid claims
"""

import json
import csv
import os
import random
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "synthetic")
os.makedirs(DATA_DIR, exist_ok=True)

def create_dataset():
    random.seed(42)

    policies = [
        {
            "policy_number": "POL-HLTH-1001",
            "policy_type": "COMPREHENSIVE_HEALTH",
            "claimant_id": "CUST-5001",
            "claimant_name": "Aarav Sharma",
            "sum_insured": 500000.0,
            "deductible": 5000.0,
            "copay_percentage": 10.0,
            "daily_room_rent_limit": 5000.0,
            "icu_limit": 10000.0,
            "effective_start_date": "2024-01-01",
            "effective_end_date": "2024-12-31"
        },
        {
            "policy_number": "POL-HLTH-1002",
            "policy_type": "FAMILY_FLOATER",
            "claimant_id": "CUST-5002",
            "claimant_name": "Priya Patel",
            "sum_insured": 1000000.0,
            "deductible": 0.0,
            "copay_percentage": 0.0,
            "daily_room_rent_limit": 8000.0,
            "icu_limit": 15000.0,
            "effective_start_date": "2024-01-01",
            "effective_end_date": "2024-12-31"
        },
        {
            "policy_number": "POL-HLTH-1003",
            "policy_type": "SENIOR_CITIZEN_HEALTH",
            "claimant_id": "CUST-5003",
            "claimant_name": "Ramesh Verma",
            "sum_insured": 300000.0,
            "deductible": 10000.0,
            "copay_percentage": 20.0,
            "daily_room_rent_limit": 3000.0,
            "icu_limit": 6000.0,
            "effective_start_date": "2024-01-01",
            "effective_end_date": "2024-12-31"
        },
        {
            "policy_number": "POL-HLTH-1004",
            "policy_type": "CORPORATE_GROUP_HEALTH",
            "claimant_id": "CUST-5004",
            "claimant_name": "Neha Gupta",
            "sum_insured": 750000.0,
            "deductible": 0.0,
            "copay_percentage": 5.0,
            "daily_room_rent_limit": 7000.0,
            "icu_limit": 12000.0,
            "effective_start_date": "2024-01-01",
            "effective_end_date": "2024-12-31"
        }
    ]

    claims = []
    line_items = []
    ground_truth = []

    # -------------------------------------------------------------
    # Scenario 0: Baseline Settled Historical Claims
    # -------------------------------------------------------------
    # Claim H1: Prior settled claim for Aarav Sharma
    h1_claim = {
        "claim_id": "CLM-HIST-001",
        "policy_number": "POL-HLTH-1001",
        "claimant_id": "CUST-5001",
        "claimant_name": "Aarav Sharma",
        "incident_date": "2024-08-10",
        "claim_submission_date": "2024-08-15",
        "claim_type": "HEALTH",
        "claim_status": "SETTLED",
        "provider_id": "PRV-MAX-01",
        "provider_name": "Max Healthcare Saket",
        "invoice_number": "INV-MAX-88901",
        "invoice_date": "2024-08-14",
        "total_claimed_amount": 32000.0,
        "approved_amount": 27000.0,
        "paid_amount": 27000.0
    }
    claims.append(h1_claim)
    line_items.extend([
        {
            "line_id": "LIN-H1-01",
            "claim_id": "CLM-HIST-001",
            "invoice_number": "INV-MAX-88901",
            "service_date": "2024-08-10",
            "service_code": "SRV-LAB-CBC",
            "service_category": "DIAGNOSTIC_LAB",
            "service_description": "Complete Blood Count (CBC)",
            "quantity": 1,
            "unit_price": 1200.0,
            "total_amount": 1200.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-H1-02",
            "claim_id": "CLM-HIST-001",
            "invoice_number": "INV-MAX-88901",
            "service_date": "2024-08-10",
            "service_code": "SRV-RAD-MRI-KNEE",
            "service_category": "DIAGNOSTIC_RAD",
            "service_description": "MRI Left Knee Joint without Contrast",
            "quantity": 1,
            "unit_price": 8500.0,
            "total_amount": 8500.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-H1-03",
            "claim_id": "CLM-HIST-001",
            "invoice_number": "INV-MAX-88901",
            "service_date": "2024-08-11",
            "service_code": "SRV-ROOM-PRIVATE",
            "service_category": "ROOM_CHARGES",
            "service_description": "Single Private Room Rent (4 Days)",
            "quantity": 4,
            "unit_price": 5500.0,
            "total_amount": 22000.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-H1-04",
            "claim_id": "CLM-HIST-001",
            "invoice_number": "INV-MAX-88901",
            "service_date": "2024-08-11",
            "service_code": "SRV-CONS-ORTHO",
            "service_category": "DOCTOR_CONSULTATION",
            "service_description": "Senior Orthopedic Surgeon Consultation",
            "quantity": 1,
            "unit_price": 2500.0,
            "total_amount": 2500.0,
            "is_recurring_treatment": False,
            "session_number": None
        }
    ])

    # Claim H2: Prior settled claim for Ramesh Verma
    h2_claim = {
        "claim_id": "CLM-HIST-002",
        "policy_number": "POL-HLTH-1003",
        "claimant_id": "CUST-5003",
        "claimant_name": "Ramesh Verma",
        "incident_date": "2024-09-01",
        "claim_submission_date": "2024-09-05",
        "claim_type": "HEALTH",
        "claim_status": "SETTLED",
        "provider_id": "PRV-APOLLO-02",
        "provider_name": "Apollo Hospitals Delhi",
        "invoice_number": "INV-APO-55421",
        "invoice_date": "2024-09-04",
        "total_claimed_amount": 42000.0,
        "approved_amount": 38000.0,
        "paid_amount": 38000.0
    }
    claims.append(h2_claim)
    line_items.extend([
        {
            "line_id": "LIN-H2-01",
            "claim_id": "CLM-HIST-002",
            "invoice_number": "INV-APO-55421",
            "service_date": "2024-09-01",
            "service_code": "SRV-CAR-ECG",
            "service_category": "DIAGNOSTIC_CAR",
            "service_description": "12-Lead Electrocardiogram (ECG)",
            "quantity": 1,
            "unit_price": 1000.0,
            "total_amount": 1000.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-H2-02",
            "claim_id": "CLM-HIST-002",
            "invoice_number": "INV-APO-55421",
            "service_date": "2024-09-01",
            "service_code": "SRV-CAR-ECHO",
            "service_category": "DIAGNOSTIC_CAR",
            "service_description": "2D Echocardiography with Doppler",
            "quantity": 1,
            "unit_price": 5000.0,
            "total_amount": 5000.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-H2-03",
            "claim_id": "CLM-HIST-002",
            "invoice_number": "INV-APO-55421",
            "service_date": "2024-09-02",
            "service_code": "SRV-PROC-ANGIO",
            "service_category": "SURGERY",
            "service_description": "Coronary Angiography",
            "quantity": 1,
            "unit_price": 36000.0,
            "total_amount": 36000.0,
            "is_recurring_treatment": False,
            "session_number": None
        }
    ])

    # -------------------------------------------------------------
    # Scenario 1: Exact Duplicate Claim (Incoming Claim duplicates H1)
    # -------------------------------------------------------------
    c1_claim = {
        "claim_id": "CLM-INCOMING-101",
        "policy_number": "POL-HLTH-1001",
        "claimant_id": "CUST-5001",
        "claimant_name": "Aarav Sharma",
        "incident_date": "2024-08-10",
        "claim_submission_date": "2024-10-01",
        "claim_type": "HEALTH",
        "claim_status": "SUBMITTED",
        "provider_id": "PRV-MAX-01",
        "provider_name": "Max Healthcare Saket",
        "invoice_number": "INV-MAX-88901",  # EXACT SAME INVOICE
        "invoice_date": "2024-08-14",
        "total_claimed_amount": 32000.0,
        "approved_amount": None,
        "paid_amount": None
    }
    claims.append(c1_claim)
    line_items.extend([
        {
            "line_id": "LIN-C1-01",
            "claim_id": "CLM-INCOMING-101",
            "invoice_number": "INV-MAX-88901",
            "service_date": "2024-08-10",
            "service_code": "SRV-LAB-CBC",
            "service_category": "DIAGNOSTIC_LAB",
            "service_description": "Complete Blood Count (CBC)",
            "quantity": 1,
            "unit_price": 1200.0,
            "total_amount": 1200.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C1-02",
            "claim_id": "CLM-INCOMING-101",
            "invoice_number": "INV-MAX-88901",
            "service_date": "2024-08-10",
            "service_code": "SRV-RAD-MRI-KNEE",
            "service_category": "DIAGNOSTIC_RAD",
            "service_description": "MRI Left Knee Joint without Contrast",
            "quantity": 1,
            "unit_price": 8500.0,
            "total_amount": 8500.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C1-03",
            "claim_id": "CLM-INCOMING-101",
            "invoice_number": "INV-MAX-88901",
            "service_date": "2024-08-11",
            "service_code": "SRV-ROOM-PRIVATE",
            "service_category": "ROOM_CHARGES",
            "service_description": "Single Private Room Rent (4 Days)",
            "quantity": 4,
            "unit_price": 5500.0,
            "total_amount": 22000.0,
            "is_recurring_treatment": False,
            "session_number": None
        }
    ])
    ground_truth.append({
        "case_id": "GT-CASE-01",
        "claim_id": "CLM-INCOMING-101",
        "scenario_type": "EXACT_DUPLICATE_CLAIM",
        "target_level": "CLAIM",
        "flagged_line_ids": ["LIN-C1-01", "LIN-C1-02", "LIN-C1-03"],
        "matched_claim_id": "CLM-HIST-001",
        "matched_line_id": None,
        "leakage_amount": 32000.0,
        "leakage_classification": "CALCULATED_EXACT",
        "rationale": "Exact duplicate submission of settled invoice INV-MAX-88901 from provider PRV-MAX-01 for claimant CUST-5001."
    })

    # -------------------------------------------------------------
    # Scenario 2: Intra-Claim Duplicate Line Item
    # A single claim has the same lab test / procedure billed twice on the same day
    # -------------------------------------------------------------
    c2_claim = {
        "claim_id": "CLM-INCOMING-102",
        "policy_number": "POL-HLTH-1002",
        "claimant_id": "CUST-5002",
        "claimant_name": "Priya Patel",
        "incident_date": "2024-10-12",
        "claim_submission_date": "2024-10-15",
        "claim_type": "HEALTH",
        "claim_status": "SUBMITTED",
        "provider_id": "PRV-FORTIS-03",
        "provider_name": "Fortis Memorial Research Institute",
        "invoice_number": "INV-FOR-77192",
        "invoice_date": "2024-10-14",
        "total_claimed_amount": 16500.0,
        "approved_amount": None,
        "paid_amount": None
    }
    claims.append(c2_claim)
    line_items.extend([
        {
            "line_id": "LIN-C2-01",
            "claim_id": "CLM-INCOMING-102",
            "invoice_number": "INV-FOR-77192",
            "service_date": "2024-10-12",
            "service_code": "SRV-LAB-THYROID",
            "service_category": "DIAGNOSTIC_LAB",
            "service_description": "Thyroid Profile Total (T3, T4, TSH)",
            "quantity": 1,
            "unit_price": 1800.0,
            "total_amount": 1800.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C2-02",  # DUPLICATE LINE ITEM of LIN-C2-01
            "claim_id": "CLM-INCOMING-102",
            "invoice_number": "INV-FOR-77192",
            "service_date": "2024-10-12",
            "service_code": "SRV-LAB-THYROID",
            "service_category": "DIAGNOSTIC_LAB",
            "service_description": "Thyroid Profile Total (T3, T4, TSH)",
            "quantity": 1,
            "unit_price": 1800.0,
            "total_amount": 1800.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C2-03",
            "claim_id": "CLM-INCOMING-102",
            "invoice_number": "INV-FOR-77192",
            "service_date": "2024-10-12",
            "service_code": "SRV-LAB-USG-ABDOMEN",
            "service_category": "DIAGNOSTIC_RAD",
            "service_description": "Ultrasound Whole Abdomen",
            "quantity": 1,
            "unit_price": 3500.0,
            "total_amount": 3500.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C2-04",
            "claim_id": "CLM-INCOMING-102",
            "invoice_number": "INV-FOR-77192",
            "service_date": "2024-10-13",
            "service_code": "SRV-ROOM-SEMI",
            "service_category": "ROOM_CHARGES",
            "service_description": "Semi Private Room Day 1",
            "quantity": 2,
            "unit_price": 4700.0,
            "total_amount": 9400.0,
            "is_recurring_treatment": False,
            "session_number": None
        }
    ])
    ground_truth.append({
        "case_id": "GT-CASE-02",
        "claim_id": "CLM-INCOMING-102",
        "scenario_type": "INTRA_CLAIM_DUPLICATE_LINE",
        "target_level": "LINE_ITEM",
        "flagged_line_ids": ["LIN-C2-02"],
        "matched_claim_id": "CLM-INCOMING-102",
        "matched_line_id": "LIN-C2-01",
        "leakage_amount": 1800.0,
        "leakage_classification": "CALCULATED_EXACT",
        "rationale": "Duplicate charge on same invoice: Thyroid Profile Total billed twice on 2024-10-12."
    })

    # -------------------------------------------------------------
    # Scenario 3: Cross-Claim Duplicate Line Item
    # A new claim submits an expensive test (MRI) that was already reimbursed in CLM-HIST-001
    # -------------------------------------------------------------
    c3_claim = {
        "claim_id": "CLM-INCOMING-103",
        "policy_number": "POL-HLTH-1001",
        "claimant_id": "CUST-5001",
        "claimant_name": "Aarav Sharma",
        "incident_date": "2024-08-10",
        "claim_submission_date": "2024-10-20",
        "claim_type": "HEALTH",
        "claim_status": "SUBMITTED",
        "provider_id": "PRV-DIAG-CITY",
        "provider_name": "City Imaging and Diagnostic Centre",
        "invoice_number": "INV-CITY-11029",
        "invoice_date": "2024-08-11",
        "total_claimed_amount": 11500.0,
        "approved_amount": None,
        "paid_amount": None
    }
    claims.append(c3_claim)
    line_items.extend([
        {
            "line_id": "LIN-C3-01",  # DUPLICATES LIN-H1-02 from CLM-HIST-001
            "claim_id": "CLM-INCOMING-103",
            "invoice_number": "INV-CITY-11029",
            "service_date": "2024-08-10",
            "service_code": "SRV-RAD-MRI-KNEE",
            "service_category": "DIAGNOSTIC_RAD",
            "service_description": "MRI Left Knee Joint without Contrast",
            "quantity": 1,
            "unit_price": 8500.0,
            "total_amount": 8500.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C3-02",
            "claim_id": "CLM-INCOMING-103",
            "invoice_number": "INV-CITY-11029",
            "service_date": "2024-08-11",
            "service_code": "SRV-CONS-FOLLOWUP",
            "service_category": "DOCTOR_CONSULTATION",
            "service_description": "Follow-up Consultant Review",
            "quantity": 1,
            "unit_price": 3000.0,
            "total_amount": 3000.0,
            "is_recurring_treatment": False,
            "session_number": None
        }
    ])
    ground_truth.append({
        "case_id": "GT-CASE-03",
        "claim_id": "CLM-INCOMING-103",
        "scenario_type": "CROSS_CLAIM_DUPLICATE_LINE",
        "target_level": "LINE_ITEM",
        "flagged_line_ids": ["LIN-C3-01"],
        "matched_claim_id": "CLM-HIST-001",
        "matched_line_id": "LIN-H1-02",
        "leakage_amount": 8500.0,
        "leakage_classification": "CALCULATED_EXACT",
        "rationale": "Cross-claim duplicate charge: MRI Left Knee Joint was already claimed and settled under CLM-HIST-001."
    })

    # -------------------------------------------------------------
    # Scenario 4: Near-Duplicate Claim & Line Items (Fuzzy / Typos / Date slop)
    # Re-submission of CLM-HIST-002 with minor invoice typo 'INV-AP0-55421' (0 instead of O)
    # and date off by 1 day, amount variance of ₹500
    # -------------------------------------------------------------
    c4_claim = {
        "claim_id": "CLM-INCOMING-104",
        "policy_number": "POL-HLTH-1003",
        "claimant_id": "CUST-5003",
        "claimant_name": "Ramesh Verma",
        "incident_date": "2024-09-02",  # 1 day difference
        "claim_submission_date": "2024-10-18",
        "claim_type": "HEALTH",
        "claim_status": "SUBMITTED",
        "provider_id": "PRV-APOLLO-02",
        "provider_name": "Apollo Hospitals Delhi",
        "invoice_number": "INV-AP0-55421",  # Typo: 0 instead of O
        "invoice_date": "2024-09-05",
        "total_claimed_amount": 42500.0,  # ₹500 slight variation
        "approved_amount": None,
        "paid_amount": None
    }
    claims.append(c4_claim)
    line_items.extend([
        {
            "line_id": "LIN-C4-01",
            "claim_id": "CLM-INCOMING-104",
            "invoice_number": "INV-AP0-55421",
            "service_date": "2024-09-02",
            "service_code": "SRV-CAR-ECG",
            "service_category": "DIAGNOSTIC_CAR",
            "service_description": "12 Lead ECG Cardiac Assessment", # Fuzzy match to '12-Lead Electrocardiogram (ECG)'
            "quantity": 1,
            "unit_price": 1000.0,
            "total_amount": 1000.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C4-02",
            "claim_id": "CLM-INCOMING-104",
            "invoice_number": "INV-AP0-55421",
            "service_date": "2024-09-02",
            "service_code": "SRV-CAR-ECHO",
            "service_category": "DIAGNOSTIC_CAR",
            "service_description": "2D Echo Doppler Examination", # Fuzzy match to '2D Echocardiography with Doppler'
            "quantity": 1,
            "unit_price": 5500.0, # ₹500 higher
            "total_amount": 5500.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C4-03",
            "claim_id": "CLM-INCOMING-104",
            "invoice_number": "INV-AP0-55421",
            "service_date": "2024-09-03",
            "service_code": "SRV-PROC-ANGIO",
            "service_category": "SURGERY",
            "service_description": "Coronary Angiography Procedure", # Matches 'Coronary Angiography'
            "quantity": 1,
            "unit_price": 36000.0,
            "total_amount": 36000.0,
            "is_recurring_treatment": False,
            "session_number": None
        }
    ])
    ground_truth.append({
        "case_id": "GT-CASE-04",
        "claim_id": "CLM-INCOMING-104",
        "scenario_type": "NEAR_DUPLICATE_CLAIM",
        "target_level": "CLAIM",
        "flagged_line_ids": ["LIN-C4-01", "LIN-C4-02", "LIN-C4-03"],
        "matched_claim_id": "CLM-HIST-002",
        "matched_line_id": None,
        "leakage_amount": 42500.0,
        "leakage_classification": "SUSPECTED_ESTIMATED",
        "rationale": "High-confidence near duplicate of settled claim CLM-HIST-002. Invoice # has 1-char typo ('INV-AP0-55421' vs 'INV-APO-55421'), dates shift by 1 day, same provider and procedure."
    })

    # -------------------------------------------------------------
    # Scenario 5: Legitimate Repeat Services (MUST NOT BE FLAGGED!)
    # Patient undergoing regular post-op physiotherapy on consecutive days
    # -------------------------------------------------------------
    c5_claim = {
        "claim_id": "CLM-INCOMING-105",
        "policy_number": "POL-HLTH-1004",
        "claimant_id": "CUST-5004",
        "claimant_name": "Neha Gupta",
        "incident_date": "2024-10-01",
        "claim_submission_date": "2024-10-15",
        "claim_type": "HEALTH",
        "claim_status": "SUBMITTED",
        "provider_id": "PRV-REHAB-WELL",
        "provider_name": "Wellspring Physical Therapy & Rehab",
        "invoice_number": "INV-WELL-4401",
        "invoice_date": "2024-10-14",
        "total_claimed_amount": 6000.0,
        "approved_amount": None,
        "paid_amount": None
    }
    claims.append(c5_claim)
    line_items.extend([
        {
            "line_id": "LIN-C5-01",
            "claim_id": "CLM-INCOMING-105",
            "invoice_number": "INV-WELL-4401",
            "service_date": "2024-10-05",
            "service_code": "SRV-THERAPY-PHYSIO",
            "service_category": "THERAPY_REHAB",
            "service_description": "Post-Op Knee Mobilization Physiotherapy - Session 1",
            "quantity": 1,
            "unit_price": 1500.0,
            "total_amount": 1500.0,
            "is_recurring_treatment": True,
            "session_number": 1
        },
        {
            "line_id": "LIN-C5-02",
            "claim_id": "CLM-INCOMING-105",
            "invoice_number": "INV-WELL-4401",
            "service_date": "2024-10-07",
            "service_code": "SRV-THERAPY-PHYSIO",
            "service_category": "THERAPY_REHAB",
            "service_description": "Post-Op Knee Mobilization Physiotherapy - Session 2",
            "quantity": 1,
            "unit_price": 1500.0,
            "total_amount": 1500.0,
            "is_recurring_treatment": True,
            "session_number": 2
        },
        {
            "line_id": "LIN-C5-03",
            "claim_id": "CLM-INCOMING-105",
            "invoice_number": "INV-WELL-4401",
            "service_date": "2024-10-09",
            "service_code": "SRV-THERAPY-PHYSIO",
            "service_category": "THERAPY_REHAB",
            "service_description": "Post-Op Knee Mobilization Physiotherapy - Session 3",
            "quantity": 1,
            "unit_price": 1500.0,
            "total_amount": 1500.0,
            "is_recurring_treatment": True,
            "session_number": 3
        },
        {
            "line_id": "LIN-C5-04",
            "claim_id": "CLM-INCOMING-105",
            "invoice_number": "INV-WELL-4401",
            "service_date": "2024-10-11",
            "service_code": "SRV-THERAPY-PHYSIO",
            "service_category": "THERAPY_REHAB",
            "service_description": "Post-Op Knee Mobilization Physiotherapy - Session 4",
            "quantity": 1,
            "unit_price": 1500.0,
            "total_amount": 1500.0,
            "is_recurring_treatment": True,
            "session_number": 4
        }
    ])
    ground_truth.append({
        "case_id": "GT-CASE-05",
        "claim_id": "CLM-INCOMING-105",
        "scenario_type": "LEGITIMATE_REPEAT_SERVICE",
        "target_level": "NONE",
        "flagged_line_ids": [],
        "matched_claim_id": None,
        "matched_line_id": None,
        "leakage_amount": 0.0,
        "leakage_classification": "NONE",
        "rationale": "Valid recurring post-op physiotherapy sessions on distinct dates (Oct 5, 7, 9, 11) with explicit session numbers. No duplicate leakage."
    })

    # -------------------------------------------------------------
    # Scenario 6: Clean, Valid Independent Claim
    # Distinct health claim with standard single services
    # -------------------------------------------------------------
    c6_claim = {
        "claim_id": "CLM-INCOMING-106",
        "policy_number": "POL-HLTH-1002",
        "claimant_id": "CUST-5002",
        "claimant_name": "Priya Patel",
        "incident_date": "2024-10-25",
        "claim_submission_date": "2024-10-28",
        "claim_type": "HEALTH",
        "claim_status": "SUBMITTED",
        "provider_id": "PRV-VISION-EYE",
        "provider_name": "Centre for Sight Eye Institute",
        "invoice_number": "INV-EYE-90211",
        "invoice_date": "2024-10-26",
        "total_claimed_amount": 28000.0,
        "approved_amount": None,
        "paid_amount": None
    }
    claims.append(c6_claim)
    line_items.extend([
        {
            "line_id": "LIN-C6-01",
            "claim_id": "CLM-INCOMING-106",
            "invoice_number": "INV-EYE-90211",
            "service_date": "2024-10-25",
            "service_code": "SRV-EYE-CATARACT",
            "service_category": "SURGERY",
            "service_description": "Phacoemulsification with Foldable IOL (Right Eye)",
            "quantity": 1,
            "unit_price": 25000.0,
            "total_amount": 25000.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C6-02",
            "claim_id": "CLM-INCOMING-106",
            "invoice_number": "INV-EYE-90211",
            "service_date": "2024-10-25",
            "service_code": "SRV-EYE-DROPS",
            "service_category": "PHARMACY",
            "service_description": "Post-Op Antibiotic and Anti-inflammatory Eye Drops Kit",
            "quantity": 1,
            "unit_price": 3000.0,
            "total_amount": 3000.0,
            "is_recurring_treatment": False,
            "session_number": None
        }
    ])
    ground_truth.append({
        "case_id": "GT-CASE-06",
        "claim_id": "CLM-INCOMING-106",
        "scenario_type": "CLEAN_VALID_CLAIM",
        "target_level": "NONE",
        "flagged_line_ids": [],
        "matched_claim_id": None,
        "matched_line_id": None,
        "leakage_amount": 0.0,
        "leakage_classification": "NONE",
        "rationale": "Clean valid independent claim with no duplicate charges."
    })

    # -------------------------------------------------------------
    # Scenario 7: Policy Limit Breach (Room Rent Daily Limit Exceeded)
    # Problem statement example: Room charge billed at ₹7,000/day exceeds ₹5,000 limit for 3 days = ₹6,000
    # -------------------------------------------------------------
    c7_claim = {
        "claim_id": "CLM-INCOMING-107",
        "policy_number": "POL-HLTH-1001",
        "claimant_id": "CUST-5001",
        "claimant_name": "Aarav Sharma",
        "incident_date": "2024-10-20",
        "claim_submission_date": "2024-10-24",
        "claim_type": "HEALTH",
        "claim_status": "SUBMITTED",
        "provider_id": "PRV-MAX-01",
        "provider_name": "Max Healthcare Saket",
        "invoice_number": "INV-MAX-99120",
        "invoice_date": "2024-10-23",
        "total_claimed_amount": 24000.0,
        "approved_amount": None,
        "paid_amount": None
    }
    claims.append(c7_claim)
    line_items.extend([
        {
            "line_id": "LIN-C7-01",
            "claim_id": "CLM-INCOMING-107",
            "invoice_number": "INV-MAX-99120",
            "service_date": "2024-10-20",
            "service_code": "SRV-ROOM-DELUXE",
            "service_category": "ROOM_CHARGES",
            "service_description": "Deluxe Single Room Rent (3 Days)",
            "quantity": 3,
            "unit_price": 7000.0,  # Exceeds POL-HLTH-1001 limit of 5000.0 by 2000/day
            "total_amount": 21000.0,
            "is_recurring_treatment": False,
            "session_number": None
        },
        {
            "line_id": "LIN-C7-02",
            "claim_id": "CLM-INCOMING-107",
            "invoice_number": "INV-MAX-99120",
            "service_date": "2024-10-21",
            "service_code": "SRV-CONS-PHYSICIAN",
            "service_category": "DOCTOR_CONSULTATION",
            "service_description": "In-Patient Physician Daily Rounds",
            "quantity": 1,
            "unit_price": 3000.0,
            "total_amount": 3000.0,
            "is_recurring_treatment": False,
            "session_number": None
        }
    ])
    ground_truth.append({
        "case_id": "GT-CASE-07",
        "claim_id": "CLM-INCOMING-107",
        "scenario_type": "POLICY_LIMIT_BREACH",
        "target_level": "LINE_ITEM",
        "flagged_line_ids": ["LIN-C7-01"],
        "matched_claim_id": None,
        "matched_line_id": None,
        "leakage_amount": 6000.0,
        "leakage_classification": "CALCULATED_EXACT",
        "rationale": "Daily room rent ₹7,000 exceeds policy limit of ₹5,000 by ₹2,000 for 3 days = ₹6,000 calculated excess."
    })

    # Save to JSON
    with open(os.path.join(DATA_DIR, "policies.json"), "w", encoding="utf-8") as f:
        json.dump(policies, f, indent=2)

    with open(os.path.join(DATA_DIR, "claims.json"), "w", encoding="utf-8") as f:
        json.dump(claims, f, indent=2)

    with open(os.path.join(DATA_DIR, "claim_line_items.json"), "w", encoding="utf-8") as f:
        json.dump(line_items, f, indent=2)

    with open(os.path.join(DATA_DIR, "ground_truth_duplicates.json"), "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    # Save to CSV
    def write_csv(filename, data_list):
        if not data_list:
            return
        keys = data_list[0].keys()
        with open(os.path.join(DATA_DIR, filename), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in data_list:
                # Format list fields for CSV
                formatted_row = {}
                for k, v in row.items():
                    if isinstance(v, list):
                        formatted_row[k] = ";".join(str(item) for item in v)
                    else:
                        formatted_row[k] = v
                writer.writerow(formatted_row)

    write_csv("policies.csv", policies)
    write_csv("claims.csv", claims)
    write_csv("claim_line_items.csv", line_items)
    write_csv("ground_truth_duplicates.csv", ground_truth)

    print(f"Dataset generated successfully in: {DATA_DIR}")
    print(f"Generated {len(policies)} policies, {len(claims)} claims, {len(line_items)} line items, and {len(ground_truth)} benchmark ground truth cases.")

if __name__ == "__main__":
    create_dataset()

