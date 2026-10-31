from typing import Optional, Tuple
from src.rules.base import BasePolicyRule
from src.schemas import Claim, Policy, LineItem, RuleResult, RuleStatus
from src.catalog import medical_catalog
from src.ai import groq_agent

class ClinicalExclusionRule(BasePolicyRule):
    rule_id = "POL-EXCL-001"
    rule_name = "Non-Payable Consumables & Regulatory Exclusions"
    description = "Identifies non-payable consumables, PPE, luxury charges, and administrative fees using clinical catalog and Groq Qwen AI."

    def evaluate_line_item(
        self, item: LineItem, claim: Claim, policy: Policy
    ) -> Optional[RuleResult]:
        desc = item.description
        cat = item.category.upper()

        # Step 1: Explicit Category Check
        if cat in ["CONSUMABLE", "ADMINISTRATIVE"]:
            # Check catalog first
            is_match, reason = medical_catalog.is_non_payable_consumable(desc)
            if is_match:
                return RuleResult(
                    rule_id="POL-EXCL-CATALOG-01",
                    rule_name="IRDAI Non-Payable Consumables Exclusion",
                    status=RuleStatus.EXCLUDED,
                    claimed_amount=item.total_amount,
                    admissible_amount=0.0,
                    discrepancy_amount=item.total_amount,
                    formula_applied="item.category in [CONSUMABLE, ADMINISTRATIVE] or in IRDAI_LIST",
                    reason=f"{reason} - Invoiced under category {cat}."
                )

        # Step 2: Deterministic Catalog Keyword Search (even if categorized under Pharmacy or Surgery)
        is_match, reason = medical_catalog.is_non_payable_consumable(desc)
        if is_match:
            return RuleResult(
                rule_id="POL-EXCL-IRDAI-02",
                rule_name="IRDAI Non-Payable Consumables Exclusion",
                status=RuleStatus.EXCLUDED,
                claimed_amount=item.total_amount,
                admissible_amount=0.0,
                discrepancy_amount=item.total_amount,
                formula_applied="item.description matches IRDAI_LIST",
                reason=f"{reason}. Regulatory exclusion for hospital consumables."
            )

        # Step 3: AI Clinical Reasoning via Groq Qwen (if Groq is available and item seems ambiguous)
        if groq_agent.is_available and (cat in ["CONSUMABLE", "ADMINISTRATIVE", "MISC"] or "charge" in desc.lower()):
            diag = claim.incident_details.diagnosis_description
            ai_eval = groq_agent.normalize_clinical_line_item(desc, cat, diag)
            if ai_eval.get("is_excluded", False):
                return RuleResult(
                    rule_id="POL-EXCL-AI-03",
                    rule_name="AI Clinical Exclusion Assessment (Groq Qwen)",
                    status=RuleStatus.EXCLUDED,
                    claimed_amount=item.total_amount,
                    admissible_amount=0.0,
                    discrepancy_amount=item.total_amount,
                    formula_applied="Groq_Qwen.is_excluded == True",
                    reason=f"AI Auditor identified non-payable item: {ai_eval.get('reasoning')} (Concept: {ai_eval.get('concept')})",
                    metadata={"ai_concept": ai_eval.get("concept")}
                )

        return None

    def evaluate(self, claim: Claim, policy: Policy, context: Optional[dict] = None) -> list:
        # Handled per line item
        return []

