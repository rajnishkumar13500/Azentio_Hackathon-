import re
from decimal import Decimal
from typing import Dict, Any, List, Optional

class DocumentFieldExtractor:
    @staticmethod
    def extract_candidate_fields(raw_text: str) -> Dict[str, Any]:
        """
        Deterministic regex and pattern based extraction of candidate fields
        from document or OCR text.
        """
        candidates: Dict[str, Any] = {
            "invoice_reference": None,
            "claim_id": None,
            "invoice_date": None,
            "total_amount": None,
            "provider_name": None,
            "line_items": [],
            "confidence": 85.0
        }

        if not raw_text:
            return candidates

        # 1. Invoice Reference / Bill No
        # Prioritize explicit pattern like INV-xxx or BILL-xxx
        inv_token_match = re.search(r"\b(INV[-:_][A-Za-z0-9\-]+|BILL[-:_][A-Za-z0-9\-]+)\b", raw_text, re.IGNORECASE)
        if inv_token_match:
            candidates["invoice_reference"] = inv_token_match.group(1).replace(":", "-")
        else:
            inv_match = re.search(r"(?:invoice\s*(?:no|num|number|#|ref)|bill\s*(?:no|num|#))[:\s]*([A-Za-z0-9\-_/]+)", raw_text, re.IGNORECASE)
            if inv_match:
                candidates["invoice_reference"] = inv_match.group(1).strip()

        # 2. Claim ID
        claim_token_match = re.search(r"\b(CLM[-:_][A-Za-z0-9\-]+)\b", raw_text, re.IGNORECASE)
        if claim_token_match:
            candidates["claim_id"] = claim_token_match.group(1).replace(":", "-")
        else:
            claim_match = re.search(r"(?:claim\s*(?:no|id|number|ref))[:\s]*([A-Za-z0-9\-_]+)", raw_text, re.IGNORECASE)
            if claim_match:
                candidates["claim_id"] = claim_match.group(1).strip()

        # 3. Date
        date_match = re.search(r"(?:date|invoice\s*date|bill\s*date)[:\s]*([0-9]{4}[-/]?[0-9]{2}[-/]?[0-9]{2}|[0-9]{2}[-/]?[0-9]{2}[-/]?[0-9]{4})", raw_text, re.IGNORECASE)
        if date_match:
            raw_d = date_match.group(1).strip()
            # If format like 202403-18 or 20240318
            if len(raw_d) == 9 and raw_d[6] == "-":
                raw_d = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[7:]}"
            candidates["invoice_date"] = raw_d
        else:
            generic_date = re.search(r"\b([0-9]{4}-[0-9]{2}-[0-9]{2})\b", raw_text)
            if generic_date:
                candidates["invoice_date"] = generic_date.group(1)

        # 4. Total Amount
        total_match = re.search(r"(?:total\s*amount|total|net\s*payable|gross\s*amount|grand\s*total)[:\s]*(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]{2})?)", raw_text, re.IGNORECASE)
        if total_match:
            amt_str = total_match.group(1).replace(",", "").strip()
            try:
                candidates["total_amount"] = str(Decimal(amt_str))
            except Exception:
                candidates["total_amount"] = amt_str

        # 5. Hospital / Provider name
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        for line in lines[:5]:  # Look in first few header lines
            if any(kw in line.lower() for kw in ["hospital", "clinic", "healthcare", "medical", "nursing", "centre", "center"]):
                candidates["provider_name"] = line
                break

        # 6. Candidate Line Items
        # Pattern: description ... qty ... rate ... amount
        for line in lines:
            line_item_match = re.search(r"^(.*?)\s+(\d+)\s+([0-9,]+(?:\.[0-9]{2})?)\s+([0-9,]+(?:\.[0-9]{2})?)$", line)
            if line_item_match:
                desc = line_item_match.group(1).strip()
                qty = line_item_match.group(2).strip()
                price = line_item_match.group(3).replace(",", "").strip()
                amt = line_item_match.group(4).replace(",", "").strip()
                if desc and not any(kw in desc.lower() for kw in ["total", "subtotal", "tax", "gst", "discount"]):
                    candidates["line_items"].append({
                        "description": desc,
                        "quantity": qty,
                        "unit_price": price,
                        "line_amount": amt
                    })

        return candidates
