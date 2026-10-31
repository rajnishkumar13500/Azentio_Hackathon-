from typing import Optional
from src.rules.base import BasePolicyRule
from src.schemas import Claim, Policy, LineItem, RuleResult, RuleStatus
from src.catalog import medical_catalog

class BenchmarkAnomalyRule(BasePolicyRule):
    rule_id = "POL-ANOMALY-001"
    rule_name = "Provider Benchmark Pricing Anomaly Detector"
    description = "Detects excessive billing by comparing procedure rates against regional benchmarks."

    def evaluate_line_item(
        self, item: LineItem, claim: Claim, policy: Policy
    ) -> Optional[RuleResult]:
        desc = item.description
        cat = item.category.upper()

        if cat in ["SURGERY", "INVESTIGATION"]:
            proc_key = medical_catalog.normalize_procedure(
                claim.incident_details.icd10_code, desc
            )
            if not proc_key:
                proc_key = medical_catalog.normalize_procedure(
                    None, claim.incident_details.diagnosis_description
                )

            if proc_key:
                benchmark_info = medical_catalog.get_benchmark(proc_key)
                if benchmark_info:
                    median = benchmark_info["benchmark_median"]
                    threshold = benchmark_info["anomaly_threshold"]

                    if item.total_amount > threshold:
                        suspected_leakage = round(item.total_amount - median, 2)
                        return RuleResult(
                            rule_id="POL-ANOMALY-PRICE-01",
                            rule_name="Unusual Provider Pricing Outlier",
                            status=RuleStatus.ANOMALY_SUSPECTED,
                            claimed_amount=item.total_amount,
                            admissible_amount=item.total_amount, # Deterministic admissibility retained until HITL review
                            discrepancy_amount=0.0,
                            suspected_leakage_amount=suspected_leakage,
                            formula_applied=f"Billed ({item.total_amount:,.2f}) > Anomaly_Threshold ({threshold:,.2f})",
                            reason=(
                                f"Billed amount of ₹{item.total_amount:,.2f} for '{benchmark_info['procedure_name']}' "
                                f"significantly exceeds the regional threshold of ₹{threshold:,.2f} (median benchmark: ₹{median:,.2f}). "
                                f"Flagged as ₹{suspected_leakage:,.2f} SUSPECTED LEAKAGE for medical officer review."
                            ),
                            metadata={"benchmark_median": median, "threshold": threshold}
                        )

        return None

    def evaluate(self, claim: Claim, policy: Policy, context: Optional[dict] = None) -> list:
        return []
