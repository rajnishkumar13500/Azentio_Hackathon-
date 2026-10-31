import json
import pytest
from src.config import settings
from src.schemas import Claim, Policy
from src.engine import validation_engine

def load_data():
    with open(settings.POLICIES_FILE, "r", encoding="utf-8") as f:
        policies_data = json.load(f)
    with open(settings.SYNTHETIC_CLAIMS_FILE, "r", encoding="utf-8") as f:
        claims_data = json.load(f)
    return policies_data, claims_data

def test_all_synthetic_claims_execution():
    policies_data, claims_data = load_data()
    assert len(claims_data) == 5

    for raw_claim in claims_data:
        claim = Claim(**raw_claim)
        policy = Policy(**policies_data[claim.policy_id])
        report = validation_engine.validate_claim(claim, policy)

        assert report.claim_id == claim.claim_id
        assert report.summary.total_claimed > 0
        assert report.summary.calculated_settlement >= 0

def test_clm_001_comprehensive_leakage():
    policies_data, claims_data = load_data()
    raw_claim = next(c for c in claims_data if c["claim_id"] == "CLM-001")
    claim = Claim(**raw_claim)
    policy = Policy(**policies_data[claim.policy_id])

    report = validation_engine.validate_claim(claim, policy)
    s = report.summary

    assert s.overall_status == "FLAGGED_LEAKAGE"
    # PPE and Gloves excluded
    assert s.total_excluded == 6500.0  # 4800 + 1700
    # Room rent capped at 5000/day for 4 days (billed 7500 => excess 2500*4 = 10,000)
    assert s.total_sublimit_deduction == 10000.0
    # Proportionate deduction applied to Surgeon fee & doctor visits
    assert s.total_proportionate_deduction > 0
    # Deductible of 5000 applied
    assert s.deductible_applied == 5000.0
    # 10% copay applied
    assert s.copay_applied > 0
    # Significant prevented leakage vs proposed settlement 145,000
    assert s.calculated_leakage_prevented > 40000.0

def test_clm_002_balance_sum_insured_exhaustion():
    policies_data, claims_data = load_data()
    raw_claim = next(c for c in claims_data if c["claim_id"] == "CLM-002")
    claim = Claim(**raw_claim)
    policy = Policy(**policies_data[claim.policy_id])

    report = validation_engine.validate_claim(claim, policy)
    s = report.summary

    assert s.overall_status == "FLAGGED_LEAKAGE"
    # Balance sum insured is only 80,000. Settlement must be capped at 80,000 max.
    assert s.calculated_settlement <= 80000.0
    # Proposed settlement was 135,000, so leakage prevented is at least 55,000
    assert s.calculated_leakage_prevented >= 55000.0

def test_clm_003_waiting_period_breach():
    policies_data, claims_data = load_data()
    raw_claim = next(c for c in claims_data if c["claim_id"] == "CLM-003")
    claim = Claim(**raw_claim)
    policy = Policy(**policies_data[claim.policy_id])

    report = validation_engine.validate_claim(claim, policy)
    s = report.summary

    # Must be completely rejected
    assert s.overall_status == "REJECTED"
    assert s.calculated_settlement == 0.0
    # Entire proposed settlement (62,000) saved from financial leakage
    assert s.calculated_leakage_prevented == 62000.0

def test_clm_004_clean_claim():
    policies_data, claims_data = load_data()
    raw_claim = next(c for c in claims_data if c["claim_id"] == "CLM-004")
    claim = Claim(**raw_claim)
    policy = Policy(**policies_data[claim.policy_id])

    report = validation_engine.validate_claim(claim, policy)
    s = report.summary

    # Approved with 0 leakage prevented because handler proposed the exact right amount
    assert s.overall_status == "APPROVED"
    assert s.calculated_leakage_prevented == 0.0
    assert s.total_excluded == 0.0

def test_clm_005_jargon_exclusions_and_anomaly():
    policies_data, claims_data = load_data()
    raw_claim = next(c for c in claims_data if c["claim_id"] == "CLM-005")
    claim = Claim(**raw_claim)
    policy = Policy(**policies_data[claim.policy_id])

    report = validation_engine.validate_claim(claim, policy)
    s = report.summary

    assert s.overall_status == "FLAGGED_LEAKAGE"
    # Consumables ("Disposable Trocar Cannula 10mm & Surgical Drape" + "Registration fee and TV charges") excluded
    assert s.total_excluded == 17000.0  # 13500 + 3500
    # Benchmark outlier detected (Appendectomy billed at 125,000 vs 110,000 threshold)
    assert s.suspected_leakage_total > 0
