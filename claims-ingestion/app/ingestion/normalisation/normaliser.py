import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
]

class Normaliser:
    @staticmethod
    def clean_string(val: Any) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        if s.lower() in ["", "none", "null", "n/a", "nan"]:
            return None
        return s

    @staticmethod
    def parse_date(val: Any) -> Optional[str]:
        """Returns standard ISO date string YYYY-MM-DD or original cleaned string if unparseable"""
        cleaned = Normaliser.clean_string(val)
        if not cleaned:
            return None
        
        # If it's already an ISO date like 2024-05-10
        if re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
            return cleaned

        for fmt in DATE_FORMATS:
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue
        
        # Return cleaned as-is for the date validator to catch and flag explicitly
        return cleaned

    @staticmethod
    def parse_decimal(val: Any) -> Optional[str]:
        """Parses amount string into clean Decimal string representation, preserving precision"""
        cleaned = Normaliser.clean_string(val)
        if not cleaned:
            return None
        
        # Remove currency symbols and formatting characters
        clean_amt = re.sub(r"[₹$,\sA-Za-z]", "", cleaned)
        try:
            d = Decimal(clean_amt)
            return str(d)
        except (InvalidOperation, ValueError):
            return cleaned  # Pass through for validator to report

    @staticmethod
    def normalise_record(record_type: str, mapped_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalises field values according to record type requirements"""
        norm = dict(mapped_payload)

        # Standardise IDs - preserve leading zeros and strip whitespace
        for id_field in ["claim_id", "policy_number", "claimant_id", "provider_id", "invoice_id", "invoice_reference", "line_item_id", "settlement_id", "history_id"]:
            if id_field in norm and norm[id_field] is not None:
                cleaned = Normaliser.clean_string(norm[id_field])
                if cleaned is not None:
                    norm[id_field] = cleaned

        # Document OCR often yields invoice_reference without invoice_id.
        if record_type == "INVOICE" and not norm.get("invoice_id") and norm.get("invoice_reference"):
            norm["invoice_id"] = norm["invoice_reference"]

        # Standardise Dates
        for date_field in ["incident_date", "effective_from", "effective_to", "invoice_date", "settlement_date", "event_date"]:
            if date_field in norm and norm[date_field] is not None:
                norm[date_field] = Normaliser.parse_date(norm[date_field])

        # Standardise Monetary / Decimal Fields
        for amount_field in ["sum_insured", "requested_amount", "total_amount", "unit_price", "line_amount", "approved_amount", "paid_amount", "amount", "sub_limit", "deductible", "copay_percentage"]:
            if amount_field in norm and norm[amount_field] is not None:
                norm[amount_field] = Normaliser.parse_decimal(norm[amount_field])

        # Quantity
        if "quantity" in norm and norm["quantity"] is not None:
            norm["quantity"] = Normaliser.parse_decimal(norm["quantity"])

        # Default currency
        if "currency" in norm:
            norm["currency"] = (Normaliser.clean_string(norm["currency"]) or "INR").upper()
        else:
            norm["currency"] = "INR"

        # Claim type uppercase
        if "claim_type" in norm and norm["claim_type"]:
            norm["claim_type"] = str(norm["claim_type"]).strip().upper()

        return norm
