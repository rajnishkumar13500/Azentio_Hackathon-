from datetime import datetime
from typing import Optional, List
from src.rules.base import BasePolicyRule
from src.schemas import Claim, Policy, RuleResult, RuleStatus
from src.catalog import medical_catalog

class CoverageRule(BasePolicyRule):
    rule_id = "POL-COV-001"
    rule_name = "Policy Coverage & Eligibility Verification"
    description = "Checks policy active status, dates, eligible dependents, and waiting periods."

    def evaluate(self, claim: Claim, policy: Policy, context: Optional[dict] = None) -> List[RuleResult]:
        results: List[RuleResult] = []

        # 1. Active Status Check
        if policy.status.upper() != "ACTIVE":
            results.append(
                RuleResult(
                    rule_id="POL-COV-STATUS-01",
                    rule_name="Policy Active Status Check",
                    status=RuleStatus.FAILED,
                    claimed_amount=sum(item.total_amount for item in claim.line_items),
                    admissible_amount=0.0,
                    discrepancy_amount=sum(item.total_amount for item in claim.line_items),
                    formula_applied="Policy.status == ACTIVE",
                    reason=f"Policy {policy.policy_id} is currently {policy.status}. Claims are not payable."
                )
            )
            return results

        # 2. Date Validity Check
        try:
            adm_date = datetime.fromisoformat(claim.incident_details.admission_date.replace("Z", "+00:00")).date()
            p_start = datetime.strptime(policy.start_date, "%Y-%m-%d").date()
            p_end = datetime.strptime(policy.end_date, "%Y-%m-%d").date()

            if not (p_start <= adm_date <= p_end):
                results.append(
                    RuleResult(
                        rule_id="POL-COV-DATES-02",
                        rule_name="Policy Period Validity",
                        status=RuleStatus.FAILED,
                        claimed_amount=sum(item.total_amount for item in claim.line_items),
                        admissible_amount=0.0,
                        discrepancy_amount=sum(item.total_amount for item in claim.line_items),
                        formula_applied=f"{p_start} <= {adm_date} <= {p_end}",
                        reason=f"Admission date {adm_date} is outside the active policy period ({p_start} to {p_end})."
                    )
                )
                return results
        except Exception:
            pass

        # 3. Dependent Eligibility
        rel = claim.claimant.relationship_to_insured.upper()
        if rel not in [d.upper() for d in policy.covered_dependents]:
            results.append(
                RuleResult(
                    rule_id="POL-COV-DEPENDENT-03",
                    rule_name="Covered Dependent Verification",
                    status=RuleStatus.FAILED,
                    claimed_amount=sum(item.total_amount for item in claim.line_items),
                    admissible_amount=0.0,
                    discrepancy_amount=sum(item.total_amount for item in claim.line_items),
                    formula_applied=f"claimant.relationship ({rel}) IN policy.covered_dependents",
                    reason=f"Claimant relationship '{rel}' is not covered under policy {policy.policy_id}."
                )
            )
            return results

        # 4. Pre-Existing Disease (PED) Waiting Period Check
        tenure_months = claim.incident_details.policy_tenure_months
        if claim.incident_details.is_pre_existing:
            ped_waiting = policy.waiting_periods.pre_existing_disease_months
            if tenure_months < ped_waiting:
                results.append(
                    RuleResult(
                        rule_id="POL-WAIT-PED-04",
                        rule_name="Pre-Existing Disease Waiting Period",
                        status=RuleStatus.FAILED,
                        claimed_amount=sum(item.total_amount for item in claim.line_items),
                        admissible_amount=0.0,
                        discrepancy_amount=sum(item.total_amount for item in claim.line_items),
                        formula_applied=f"Tenure ({tenure_months} mo) < PED Waiting ({ped_waiting} mo)",
                        reason=(
                            f"Pre-existing condition claimed at {tenure_months} months tenure. "
                            f"Policy requires a {ped_waiting}-month waiting period for pre-existing conditions."
                        )
                    )
                )
                return results

        # 5. Specific Disease Waiting Period Check (e.g., Cataract, Knee Osteoarthritis)
        icd_code = claim.incident_details.icd10_code
        if icd_code and icd_code in medical_catalog.icd10_codes:
            code_info = medical_catalog.icd10_codes[icd_code]
            if code_info.get("specific_disease_waiting", False):
                spec_waiting = policy.waiting_periods.specific_diseases_months
                if tenure_months < spec_waiting:
                    results.append(
                        RuleResult(
                            rule_id="POL-WAIT-SPECIFIC-05",
                            rule_name="Specific Ailment Waiting Period",
                            status=RuleStatus.FAILED,
                            claimed_amount=sum(item.total_amount for item in claim.line_items),
                            admissible_amount=0.0,
                            discrepancy_amount=sum(item.total_amount for item in claim.line_items),
                            formula_applied=f"Tenure ({tenure_months} mo) < Specific Waiting ({spec_waiting} mo)",
                            reason=(
                                f"Ailment '{code_info.get('display_name')}' is subject to a {spec_waiting}-month "
                                f"waiting period. Current tenure: {tenure_months} months."
                            )
                        )
                    )
                    return results

        # If all passed
        results.append(
            RuleResult(
                rule_id="POL-COV-VERIFIED-00",
                rule_name="Policy Coverage Validated",
                status=RuleStatus.PASSED,
                claimed_amount=sum(item.total_amount for item in claim.line_items),
                admissible_amount=sum(item.total_amount for item in claim.line_items),
                discrepancy_amount=0.0,
                reason="Policy is active, claimant is eligible, and all waiting periods are satisfied."
            )
        )
        return results

