from typing import Dict, Any, List, Optional
from app.domain.enums import RecordType

KNOWN_ALIASES = {
    # CLAIM
    "claim_id": ["claim_id", "claim_no", "claim_number", "claimid", "claimref", "claim_ref"],
    "policy_number": ["policy_number", "policy_no", "policy_ref", "policyref", "policyno", "policy_id"],
    "claimant_id": ["claimant_id", "member_id", "patient_id", "insured_id", "beneficiary_id"],
    "claimant_name": ["claimant_name", "customer_name", "patient_name", "insured_name", "member_name", "name"],
    "incident_date": ["incident_date", "incident_dt", "admission_date", "hospitalization_date", "loss_date", "event_date"],
    "claim_type": ["claim_type", "type", "claim_category", "settlement_type"],
    "requested_amount": ["requested_amount", "claim_value", "claim_amount", "claimed_amount", "amount_claimed", "bill_amount"],
    "currency": ["currency", "curr", "curr_code"],
    
    # POLICY
    "effective_from": ["effective_from", "start_date", "policy_start", "inception_date", "valid_from"],
    "effective_to": ["effective_to", "end_date", "policy_end", "expiry_date", "valid_to"],
    "sum_insured": ["sum_insured", "coverage_amount", "total_sum_insured", "sum_assured", "policy_limit"],
    
    # INVOICE
    "invoice_id": ["invoice_id", "inv_id", "bill_id", "invoice_no"],
    "provider_id": ["provider_id", "hospital_id", "hospital_code", "provider_code"],
    "invoice_reference": ["invoice_reference", "invoice_ref", "bill_no", "bill_number", "invoice_num", "invoice_number"],
    "invoice_date": ["invoice_date", "bill_date", "inv_date", "date"],
    "total_amount": ["total_amount", "invoice_total", "bill_total", "net_amount", "gross_amount", "amount"],

    # LINE ITEM
    "line_item_id": ["line_item_id", "item_id", "line_id"],
    "service_code": ["service_code", "procedure_code", "code", "item_code"],
    "description": ["description", "service_description", "item_name", "service_name", "line_description"],
    "category": ["category", "service_category", "type", "expense_type"],
    "quantity": ["quantity", "qty", "units", "count"],
    "unit_price": ["unit_price", "rate", "price", "unit_cost"],
    "line_amount": ["line_amount", "total_line_amount", "item_total", "line_total", "amount"],

    # PROVIDER
    "provider_name": ["provider_name", "hospital_name", "clinic_name", "vendor_name"],
    "provider_type": ["provider_type", "hospital_type", "facility_type"],
    "address": ["address", "location", "hospital_address"],

    # SETTLEMENT
    "settlement_id": ["settlement_id", "settle_id", "payment_id"],
    "approved_amount": ["approved_amount", "authorized_amount", "settled_amount"],
    "paid_amount": ["paid_amount", "disbursed_amount", "payment_amount"],
    "settlement_date": ["settlement_date", "payment_date", "approval_date"],
    "settlement_status": ["settlement_status", "status", "payment_status"],

    # HISTORY
    "history_id": ["history_id", "event_id"],
    "event_description": ["event_description", "description", "details", "remarks"],
}

MANDATORY_FIELDS = {
    "CLAIM": ["claim_id", "claimant_name", "incident_date", "requested_amount"],
    "POLICY": ["policy_number", "effective_from", "effective_to", "sum_insured"],
    "INVOICE": ["invoice_id", "claim_id", "invoice_reference", "invoice_date", "total_amount"],
    "INVOICE_LINE_ITEM": ["line_item_id", "description", "quantity", "unit_price", "line_amount"],
    "PROVIDER": ["provider_id", "provider_name"],
    "SETTLEMENT": ["settlement_id", "claim_id", "approved_amount", "paid_amount", "settlement_date", "settlement_status"],
    "CLAIM_HISTORY": ["claim_id", "event_type", "event_date", "event_description"],
}

class FieldMapper:
    @staticmethod
    def suggest_mappings(record_type: str, source_fields: List[str]) -> Dict[str, str]:
        """Returns mapping of canonical_field -> source_field"""
        suggestions = {}
        source_lower_map = {f.lower().strip().replace("-", "_").replace(" ", "_"): f for f in source_fields}

        for canonical_name, aliases in KNOWN_ALIASES.items():
            for alias in aliases:
                norm_alias = alias.lower().replace("-", "_").replace(" ", "_")
                if norm_alias in source_lower_map:
                    suggestions[canonical_name] = source_lower_map[norm_alias]
                    break
        return suggestions

    @staticmethod
    def map_record(
        record_type: str,
        raw_payload: Dict[str, Any],
        mapping_rules: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Maps raw payload fields to canonical payload fields.
        mapping_rules can be canonical_field -> source_field OR source_field -> canonical_field.
        Preserves unmapped fields under '_extra_fields'.
        """
        # Determine rules: canonical -> source
        resolved_mapping: Dict[str, str] = {}
        if mapping_rules:
            for k, v in mapping_rules.items():
                if k in KNOWN_ALIASES:
                    resolved_mapping[k] = v
                elif v in KNOWN_ALIASES:
                    resolved_mapping[v] = k
                else:
                    resolved_mapping[v] = k
        else:
            resolved_mapping = FieldMapper.suggest_mappings(record_type, list(raw_payload.keys()))

        normalised = {}
        consumed_source_keys = set()

        for canonical_field, source_field in resolved_mapping.items():
            if source_field in raw_payload:
                normalised[canonical_field] = raw_payload[source_field]
                consumed_source_keys.add(source_field)

        # Fallback check for exact key matches
        for k, v in raw_payload.items():
            if k not in consumed_source_keys:
                k_clean = k.strip().lower().replace(" ", "_")
                if k_clean in KNOWN_ALIASES and k_clean not in normalised:
                    normalised[k_clean] = v
                    consumed_source_keys.add(k)

        # Preserve unknown columns in _extra_fields
        extra_fields = {k: v for k, v in raw_payload.items() if k not in consumed_source_keys}
        if extra_fields:
            normalised["_extra_fields"] = extra_fields

        return normalised
