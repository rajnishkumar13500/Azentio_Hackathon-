import pytest
from src.schemas import Policy, PolicySubLimits, WaitingPeriods, Claim, Claimant, IncidentDetails, LineItem, RuleStatus
from src.rules import (
    CoverageRule,
    ClinicalExclusionRule,
    SubLimitRule,
    ProportionateDeductionRule,
    DeductibleRule,
    CoPaymentRule,
    BenefitLimitRule,
    BenchmarkAnomalyRule,
)

@pytest.fixture
def standard_policy():
    return Policy(
        policy_id="TEST-POL-01",
        policy_name="Test Health Policy",
        start_date="2026-01-01",
        end_date="2026-12-31",
        status="ACTIVE",
        sum_insured=500000.0,
        balance_sum_insured=400000.0,
        co_payment_percentage=10.0,
        deductible_per_claim=5000.0,
        proportionate_deduction=True,
        sub_limits=PolicySubLimits(
            daily_room_rent=5000.0,
            daily_icu_rent=10000.0,
            procedure_caps={"cataract": 30000.0}
        ),
        waiting_periods=WaitingPeriods(
            initial_waiting_days=30,
            specific_diseases_months=24,
            pre_existing_disease_months=36
        ),
        covered_dependents=["SELF", "SPOUSE"]
    )

def test_coverage_rule_inactive_policy(standard_policy):
    standard_policy.status = "EXPIRED"
    claim = Claim(
        claim_id="CLM-TEST-01",
        policy_id=standard_policy.policy_id,
        claimant=Claimant(claimant_id="C1", name="Test", relationship_to_insured="SELF", age=30),
        incident_details=IncidentDetails(
            admission_date="2026-06-01T10:00:00Z",
            discharge_date="2026-06-03T10:00:00Z",
            hospital_id="H1",
            diagnosis_description="Fever",
            policy_tenure_months=12
        ),
        line_items=[
            LineItem(line_id="L1", category="ROOM_RENT", item_code="R1", description="Room", unit_price=2000.0, total_amount=4000.0)
        ]
    )
    rule = CoverageRule()
    results = rule.evaluate(claim, standard_policy)
    assert any(r.status == RuleStatus.FAILED for r in results)

def test_room_rent_sublimit_breach(standard_policy):
    rule = SubLimitRule()
    item = LineItem(
        line_id="L1",
        category="ROOM_RENT",
        item_code="ROOM-DELUXE",
        description="Deluxe Room (3 days)",
        quantity=3.0,
        unit_price=7000.0,
        total_amount=21000.0
    )
    claim = Claim(
        claim_id="CLM-01",
        policy_id=standard_policy.policy_id,
        claimant=Claimant(claimant_id="C1", name="Test", age=30),
        incident_details=IncidentDetails(
            admission_date="2026-06-01T10:00:00Z",
            discharge_date="2026-06-04T10:00:00Z",
            hospital_id="H1",
            diagnosis_description="Surgery"
        )
    )
    result = rule.evaluate_line_item(item, claim, standard_policy)
    assert result is not None
    assert result.status == RuleStatus.BREACHED
    # Allowed: 5000 * 3 = 15,000. Claimed: 21,000. Excess: 6,000.
    assert result.admissible_amount == 15000.0
    assert result.discrepancy_amount == 6000.0

def test_clinical_exclusion_consumable(standard_policy):
    rule = ClinicalExclusionRule()
    item = LineItem(
        line_id="L2",
        category="CONSUMABLE",
        item_code="PPE-01",
        description="Surgical PPE Kits & Examination Gloves",
        quantity=2.0,
        unit_price=1500.0,
        total_amount=3000.0
    )
    claim = Claim(
        claim_id="CLM-01",
        policy_id=standard_policy.policy_id,
        claimant=Claimant(claimant_id="C1", name="Test", age=30),
        incident_details=IncidentDetails(
            admission_date="2026-06-01T10:00:00Z",
            discharge_date="2026-06-04T10:00:00Z",
            hospital_id="H1",
            diagnosis_description="Surgery"
        )
    )
    result = rule.evaluate_line_item(item, claim, standard_policy)
    assert result is not None
    assert result.status == RuleStatus.EXCLUDED
    assert result.admissible_amount == 0.0
    assert result.discrepancy_amount == 3000.0

def test_proportionate_deduction(standard_policy):
    rule = ProportionateDeductionRule()
    # If room rent allowed is 5000 and billed was 7500, ratio is 5000 / 7500 = 0.6667
    item = LineItem(
        line_id="L3",
        category="SURGERY",
        item_code="SURG-01",
        description="Surgeon Operation Charges",
        quantity=1.0,
        unit_price=60000.0,
        total_amount=60000.0
    )
    ratio = round(5000.0 / 7500.0, 4) # 0.6667
    result = rule.evaluate_line_item(item, ratio, standard_policy)
    assert result is not None
    assert result.status == RuleStatus.BREACHED
    # 60,000 * 0.6667 = 40,002.0. Excess = 19,998.0
    assert result.admissible_amount == 40002.0
    assert result.discrepancy_amount == 19998.0

def test_deductible_and_copay_waterfall(standard_policy):
    ded_rule = DeductibleRule()
    copay_rule = CoPaymentRule()

    # Base admissible: 100,000
    base = 100000.0
    ded_res = ded_rule.evaluate_deductible(base, standard_policy)
    assert ded_res.discrepancy_amount == 5000.0
    assert ded_res.admissible_amount == 95000.0

    # 10% copay on 95,000 = 9,500
    copay_res = copay_rule.evaluate_copay(ded_res.admissible_amount, standard_policy)
    assert copay_res.discrepancy_amount == 9500.0
    assert copay_res.admissible_amount == 85500.0

def test_benefit_limit_balance_capping(standard_policy):
    standard_policy.balance_sum_insured = 50000.0
    rule = BenefitLimitRule()
    result = rule.evaluate_benefit_limit(80000.0, standard_policy)
    assert result.status == RuleStatus.BREACHED
    assert result.admissible_amount == 50000.0
    assert result.discrepancy_amount == 30000.0
