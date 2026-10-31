"""
Unit and Integration Tests for Cross-Claim Correlation Engine (Level 2 Step 1).
"""

import json
from pathlib import Path
import pytest
from src.investigation.correlation import CrossClaimCorrelationEngine
from src.investigation.models import CorrelationRelationshipType

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "cross_claim_correlation_dataset.json"


@pytest.fixture
def correlation_dataset():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def correlation_engine(correlation_dataset):
    return CrossClaimCorrelationEngine(correlation_dataset)


def test_cross_policy_shared_invoice_double_dipping(correlation_engine, correlation_dataset):
    target = next(c for c in correlation_dataset if c["claim_id"] == "CLM-CORR-001")
    report = correlation_engine.correlate(target)

    assert report.total_correlated_claims >= 1
    assert report.highest_severity == "CRITICAL"

    match = next(m for m in report.correlations if m.matched_claim_id == "CLM-CORR-002")
    assert match.relationship_type == CorrelationRelationshipType.CROSS_POLICY_SHARED_INVOICE
    assert match.severity == "CRITICAL"
    assert "invoice_number" in match.matching_attributes
    assert "hospital_id" in match.matching_attributes
    assert match.shared_values["invoice_number"] == "INV-MAX-2026-991"
    assert match.potential_leakage_amount == 180000.0
    assert "CROSS-POLICY DOUBLE DIPPING" in match.explanation


def test_overlapping_hospitalization_conflict(correlation_engine, correlation_dataset):
    target = next(c for c in correlation_dataset if c["claim_id"] == "CLM-CORR-003")
    report = correlation_engine.correlate(target)

    assert report.total_correlated_claims >= 1
    assert report.highest_severity == "CRITICAL"

    match = next(m for m in report.correlations if m.matched_claim_id == "CLM-CORR-004")
    assert match.relationship_type == CorrelationRelationshipType.OVERLAPPING_HOSPITALIZATION
    assert match.severity == "CRITICAL"
    assert "claimant_id" in match.matching_attributes
    assert match.potential_leakage_amount == 65000.0
    assert "PHYSICAL IMPOSSIBILITY" in match.explanation


def test_split_incident_unbundling(correlation_engine, correlation_dataset):
    target = next(c for c in correlation_dataset if c["claim_id"] == "CLM-CORR-005")
    report = correlation_engine.correlate(target)

    match = next(m for m in report.correlations if m.matched_claim_id == "CLM-CORR-006")
    assert match.relationship_type == CorrelationRelationshipType.SPLIT_INCIDENT_CLAIM
    assert match.severity == "HIGH"
    assert "SUSPECTED SPLIT INCIDENT UNBUNDLING" in match.explanation
    assert match.requires_investigation is True


def test_high_velocity_provider_collusion(correlation_engine, correlation_dataset):
    target = next(c for c in correlation_dataset if c["claim_id"] == "CLM-CORR-009")
    report = correlation_engine.correlate(target)

    collusion_matches = [
        m for m in report.correlations
        if m.relationship_type == CorrelationRelationshipType.HIGH_VELOCITY_PROVIDER_COLLUSION
    ]
    assert len(collusion_matches) >= 1
    assert report.highest_severity == "HIGH"
    assert "HIGH-VELOCITY FREQUENCY SPIKE" in collusion_matches[0].explanation


def test_claimant_history_baseline_non_fraud(correlation_engine, correlation_dataset):
    target = next(c for c in correlation_dataset if c["claim_id"] == "CLM-CORR-010")
    report = correlation_engine.correlate(target)

    assert report.total_correlated_claims == 1
    match = report.correlations[0]
    assert match.matched_claim_id == "CLM-CORR-011"
    assert match.relationship_type == CorrelationRelationshipType.CLAIMANT_HISTORY
    assert match.severity == "INFO"
    assert match.requires_investigation is False
    assert match.potential_leakage_amount == 0.0


def test_provider_recycled_invoice_across_patients(correlation_engine, correlation_dataset):
    target = next(c for c in correlation_dataset if c["claim_id"] == "CLM-CORR-012")
    report = correlation_engine.correlate(target)

    match = next(m for m in report.correlations if m.matched_claim_id == "CLM-CORR-013")
    assert match.relationship_type == CorrelationRelationshipType.PROVIDER_SHARED_INVOICE_ACROSS_PATIENTS
    assert match.severity == "CRITICAL"
    assert match.potential_leakage_amount == 88000.0
    assert "RECYCLED INVOICE" in match.explanation


def test_network_graph_construction(correlation_engine, correlation_dataset):
    target = next(c for c in correlation_dataset if c["claim_id"] == "CLM-CORR-001")
    report = correlation_engine.correlate(target)

    node_types = {n.type for n in report.network_nodes}
    assert "CLAIM" in node_types
    assert "POLICY" in node_types
    assert "CLAIMANT" in node_types
    assert "PROVIDER" in node_types
    assert "INVOICE" in node_types

    target_node = next(n for n in report.network_nodes if n.metadata.get("is_target"))
    assert target_node.id == "claim:CLM-CORR-001"
    assert len(report.network_edges) >= 4

