"""
Claims Leakage & Duplicate Detection Benchmark Runner.
Loads synthetic dataset and executes DuplicateDetectionEngine across all benchmark test cases.
"""

import json
import os
import sys

# Ensure workspace root is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from duplicate_detector.engine import DuplicateDetectionEngine
from duplicate_detector.models import Claim, LineItem


def load_dataset():
    data_dir = os.path.join(ROOT_DIR, "data", "synthetic")
    with open(os.path.join(data_dir, "policies.json"), "r", encoding="utf-8") as f:
        policies_raw = json.load(f)
    with open(os.path.join(data_dir, "claims.json"), "r", encoding="utf-8") as f:
        claims_raw = json.load(f)
    with open(os.path.join(data_dir, "claim_line_items.json"), "r", encoding="utf-8") as f:
        line_items_raw = json.load(f)
    with open(os.path.join(data_dir, "ground_truth_duplicates.json"), "r", encoding="utf-8") as f:
        ground_truth_raw = json.load(f)

    policies_map = {p["policy_number"]: p for p in policies_raw}

    # Group line items by claim_id
    lines_by_claim = {}
    for item in line_items_raw:
        lines_by_claim.setdefault(item["claim_id"], []).append(LineItem.from_dict(item))

    # Build Claim objects
    all_claims = []
    for c_raw in claims_raw:
        items = lines_by_claim.get(c_raw["claim_id"], [])
        all_claims.append(Claim.from_dict(c_raw, items=items))

    historical = [c for c in all_claims if c.claim_status == "SETTLED"]
    incoming = [c for c in all_claims if c.claim_status == "SUBMITTED"]

    return historical, incoming, ground_truth_raw, policies_map


def run_benchmark():
    historical_claims, incoming_claims, ground_truth, policies_map = load_dataset()
    gt_map = {gt["claim_id"]: gt for gt in ground_truth}

    engine = DuplicateDetectionEngine()

    print("=" * 105)
    print("      AZENTIO HACKATHON: CLAIMS LEAKAGE & DUPLICATE DETECTION BENCHMARK SUITE")
    print("=" * 105)
    print(f"Loaded {len(historical_claims)} Historical Baseline Claims & {len(incoming_claims)} Incoming Test Claims.\n")

    passed_count = 0
    total_test_cases = len(incoming_claims)

    for claim in incoming_claims:
        policy = policies_map.get(claim.policy_number)
        result = engine.evaluate(claim, historical_claims, policy_data=policy)
        gt = gt_map.get(claim.claim_id)

        print("-" * 105)
        print(f"CLAIM ID: {claim.claim_id} | Claimant: {claim.claimant_name} | Provider: {claim.provider_name}")
        print(f"Total Claim Amount: ₹{claim.total_claimed_amount:,.2f}")

        detected_leakage = result.summary.overall_leakage_amount
        expected_leakage = gt["leakage_amount"] if gt else 0.0
        expected_scenario = gt["scenario_type"] if gt else "UNKNOWN"

        # Determine Primary Detected Scenario
        if result.findings:
            primary_scenario = result.findings[0].scenario_type.value
        else:
            primary_scenario = "NO_DUPLICATE_FLAGGED"

        # Validate Pass/Fail Criteria
        leakage_match = abs(detected_leakage - expected_leakage) < 1.0
        scenario_match = (
            (expected_scenario in [primary_scenario, "LEGITIMATE_REPEAT_SERVICE", "CLEAN_VALID_CLAIM"])
            if not result.has_duplicate_leakage else
            (primary_scenario == expected_scenario)
        )

        test_passed = leakage_match and (
            scenario_match or
            (expected_scenario in ["LEGITIMATE_REPEAT_SERVICE", "CLEAN_VALID_CLAIM"] and not result.has_duplicate_leakage)
        )

        status_str = "✅ PASS" if test_passed else "❌ FAIL"
        if test_passed:
            passed_count += 1

        print(f"Expected Scenario : {expected_scenario}")
        print(f"Detected Scenario : {primary_scenario} (Findings: {len(result.findings)})")
        print(f"Expected Leakage  : ₹{expected_leakage:,.2f} ({gt['leakage_classification'] if gt else 'NONE'})")
        print(f"Calculated Leakage: ₹{result.summary.total_leakage_calculated:,.2f}")
        print(f"Suspected Leakage : ₹{result.summary.total_leakage_suspected:,.2f}")
        print(f"Recommendation    : {result.summary.recommendation.value} | Severity: {result.summary.highest_severity.value}")
        print(f"Verdict           : {status_str}")

        if result.findings:
            print("\n  🔍 Finding Details:")
            for idx, f in enumerate(result.findings, 1):
                print(f"    [{idx}] Rule: {f.rule_code} | Conf: {f.confidence_score*100:.0f}% | Type: {f.scenario_type.value}")
                print(f"        Leakage: ₹{f.leakage_amount:,.2f} ({f.leakage_classification.value})")
                print(f"        Evidence: Matched {f.evidence.source_type} '{f.evidence.matched_claim_id or f.evidence.matched_line_id}' (sim: {f.evidence.similarity_score*100:.1f}%)")
                print(f"        Explanation: {f.explanation}")
                print(f"        Action: {f.suggested_action.value}")
        else:
            print("  ℹ️ No duplicate leakage detected. Legitimate service approved.")

        print()

    print("=" * 105)
    print(f"BENCHMARK RESULTS: {passed_count} / {total_test_cases} TEST CASES PASSED (Accuracy: {passed_count/total_test_cases*100:.1f}%)")
    print("=" * 105)

    # Export Enriched Output Dataset with Detection Columns
    export_detection_results(historical_claims, incoming_claims, engine, gt_map, policies_map)


def export_detection_results(historical_claims, incoming_claims, engine, gt_map, policies_map):
    output_records = []
    for claim in incoming_claims:
        policy = policies_map.get(claim.policy_number)
        res = engine.evaluate(claim, historical_claims, policy_data=policy)
        primary_finding = res.findings[0] if res.findings else None

        record = {
            "claim_id": claim.claim_id,
            "policy_number": claim.policy_number,
            "claimant_name": claim.claimant_name,
            "provider_name": claim.provider_name,
            "invoice_number": claim.invoice_number,
            "total_claimed_amount": claim.total_claimed_amount,
            "has_duplicate_leakage": res.has_duplicate_leakage,
            "detected_scenario": primary_finding.scenario_type.value if primary_finding else "NO_DUPLICATE_FLAGGED",
            "calculated_leakage_amount": res.summary.total_leakage_calculated,
            "suspected_leakage_amount": res.summary.total_leakage_suspected,
            "overall_leakage_amount": res.summary.overall_leakage_amount,
            "highest_severity": res.summary.highest_severity.value,
            "confidence_score": primary_finding.confidence_score if primary_finding else 1.0,
            "recommendation": res.summary.recommendation.value,
            "rule_code_triggered": primary_finding.rule_code if primary_finding else "NONE",
            "matched_evidence_ref": (
                (primary_finding.evidence.matched_claim_id or primary_finding.evidence.matched_line_id or "")
                if primary_finding else "NONE"
            ),
            "leakage_explanation": (
                primary_finding.explanation if primary_finding
                else "No duplicate leakage detected. Legitimate service approved."
            )
        }
        output_records.append(record)

    data_dir = os.path.join(ROOT_DIR, "data", "synthetic")
    
    # Save as JSON
    out_json_path = os.path.join(data_dir, "claims_detection_output.json")
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(output_records, f, indent=2)

    # Save as CSV
    import csv
    out_csv_path = os.path.join(data_dir, "claims_detection_output.csv")
    if output_records:
        keys = output_records[0].keys()
        with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(output_records)

    print(f"\n📁 Enriched Detection Output Dataset saved to:")
    print(f"   • CSV:  {out_csv_path}")
    print(f"   • JSON: {out_json_path}")


if __name__ == "__main__":
    run_benchmark()

