"""
Unit Tests for Duplicate Detection Engine and Leakage Calculator.
Tests all scenarios using standard unittest framework.
"""

import unittest
import os
import sys

# Ensure root directory is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from duplicate_detector.engine import DuplicateDetectionEngine
from duplicate_detector.models import (
    DuplicateScenarioType,
    LeakageClassification,
    Severity,
    Recommendation
)
from duplicate_detector.utils import token_sort_ratio, string_similarity, days_between
from run_detection_benchmark import load_dataset


class TestDuplicateDetector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.historical, cls.incoming, cls.ground_truth, cls.policies_map = load_dataset()
        cls.engine = DuplicateDetectionEngine()
        cls.incoming_by_id = {c.claim_id: c for c in cls.incoming}

    def test_exact_duplicate_claim(self):
        """Scenario 1: Exact claim re-submission with same invoice number."""
        claim = self.incoming_by_id["CLM-INCOMING-101"]
        result = self.engine.evaluate(claim, self.historical)

        self.assertTrue(result.has_duplicate_leakage)
        self.assertEqual(len(result.findings), 1)
        finding = result.findings[0]

        self.assertEqual(finding.scenario_type, DuplicateScenarioType.EXACT_DUPLICATE_CLAIM)
        self.assertEqual(finding.severity, Severity.CRITICAL)
        self.assertEqual(finding.confidence_score, 1.0)
        self.assertEqual(finding.leakage_classification, LeakageClassification.CALCULATED_EXACT)
        self.assertEqual(finding.leakage_amount, 32000.0)
        self.assertEqual(result.summary.total_leakage_calculated, 32000.0)
        self.assertEqual(result.summary.total_leakage_suspected, 0.0)
        self.assertEqual(result.summary.recommendation, Recommendation.REJECT_CLAIM)

    def test_intra_claim_duplicate_line(self):
        """Scenario 2: Same bill line item repeated on same invoice and date."""
        claim = self.incoming_by_id["CLM-INCOMING-102"]
        result = self.engine.evaluate(claim, self.historical)

        self.assertTrue(result.has_duplicate_leakage)
        self.assertEqual(len(result.findings), 1)
        finding = result.findings[0]

        self.assertEqual(finding.scenario_type, DuplicateScenarioType.INTRA_CLAIM_DUPLICATE_LINE)
        self.assertEqual(finding.current_line_id, "LIN-C2-02")
        self.assertEqual(finding.leakage_amount, 1800.0)
        self.assertEqual(finding.leakage_classification, LeakageClassification.CALCULATED_EXACT)
        self.assertEqual(result.summary.total_leakage_calculated, 1800.0)
        self.assertEqual(result.summary.recommendation, Recommendation.DISALLOW_LINE_ITEM)

    def test_cross_claim_duplicate_line(self):
        """Scenario 3: Procedure already settled in an earlier claim re-billed in new claim."""
        claim = self.incoming_by_id["CLM-INCOMING-103"]
        result = self.engine.evaluate(claim, self.historical)

        self.assertTrue(result.has_duplicate_leakage)
        self.assertEqual(len(result.findings), 1)
        finding = result.findings[0]

        self.assertEqual(finding.scenario_type, DuplicateScenarioType.CROSS_CLAIM_DUPLICATE_LINE)
        self.assertEqual(finding.current_line_id, "LIN-C3-01")
        self.assertEqual(finding.leakage_amount, 8500.0)
        self.assertEqual(finding.leakage_classification, LeakageClassification.CALCULATED_EXACT)
        self.assertEqual(result.summary.total_leakage_calculated, 8500.0)
        self.assertEqual(result.summary.recommendation, Recommendation.DISALLOW_LINE_ITEM)

    def test_near_duplicate_claim(self):
        """Scenario 4: Claim with typo in invoice number and ±1 day shift."""
        claim = self.incoming_by_id["CLM-INCOMING-104"]
        result = self.engine.evaluate(claim, self.historical)

        self.assertTrue(result.has_duplicate_leakage)
        self.assertEqual(len(result.findings), 1)
        finding = result.findings[0]

        self.assertEqual(finding.scenario_type, DuplicateScenarioType.NEAR_DUPLICATE_CLAIM)
        self.assertEqual(finding.leakage_classification, LeakageClassification.SUSPECTED_ESTIMATED)
        self.assertEqual(finding.leakage_amount, 42500.0)
        self.assertEqual(result.summary.total_leakage_calculated, 0.0)
        self.assertEqual(result.summary.total_leakage_suspected, 42500.0)
        self.assertEqual(result.summary.recommendation, Recommendation.INVESTIGATE_FOR_REVIEW)

    def test_legitimate_repeat_service_pass(self):
        """Scenario 5: Sequential physiotherapy sessions must NOT be flagged."""
        claim = self.incoming_by_id["CLM-INCOMING-105"]
        result = self.engine.evaluate(claim, self.historical)

        self.assertFalse(result.has_duplicate_leakage)
        self.assertEqual(len(result.findings), 0)
        self.assertEqual(result.summary.overall_leakage_amount, 0.0)
        self.assertEqual(result.summary.recommendation, Recommendation.ALLOW)

    def test_clean_valid_claim_pass(self):
        """Scenario 6: Clean claim with single procedures must NOT be flagged."""
        claim = self.incoming_by_id["CLM-INCOMING-106"]
        result = self.engine.evaluate(claim, self.historical)

        self.assertFalse(result.has_duplicate_leakage)
        self.assertEqual(len(result.findings), 0)
        self.assertEqual(result.summary.overall_leakage_amount, 0.0)
        self.assertEqual(result.summary.recommendation, Recommendation.ALLOW)

    def test_policy_limit_breach(self):
        """Scenario 7: Room rent billed exceeds policy daily limit."""
        claim = self.incoming_by_id["CLM-INCOMING-107"]
        policy = self.policies_map.get(claim.policy_number)
        result = self.engine.evaluate(claim, self.historical, policy_data=policy)

        self.assertTrue(result.has_duplicate_leakage)
        self.assertEqual(len(result.findings), 1)
        finding = result.findings[0]

        self.assertEqual(finding.scenario_type, DuplicateScenarioType.POLICY_LIMIT_BREACH)
        self.assertEqual(finding.current_line_id, "LIN-C7-01")
        self.assertEqual(finding.leakage_amount, 6000.0)
        self.assertEqual(finding.leakage_classification, LeakageClassification.CALCULATED_EXACT)
        self.assertIsNotNone(finding.arithmetic_proof)
        self.assertEqual(finding.arithmetic_proof.calculated_discrepancy, 6000.0)
        self.assertEqual(result.summary.total_leakage_calculated, 6000.0)

    def test_similarity_utilities(self):
        """Test token sort ratio order invariance and date delta utilities."""
        s1 = "Complete Blood Count (CBC) with Platelets"
        s2 = "Platelets with Complete Blood Count (CBC)"
        self.assertGreater(token_sort_ratio(s1, s2), 0.95)

        # Date diff
        self.assertEqual(days_between("2024-08-10", "2024-08-12"), 2)


if __name__ == "__main__":
    unittest.main()

