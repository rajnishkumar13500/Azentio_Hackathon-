import csv
import io
import json
import logging
from typing import List, Dict, Any, Tuple
import openpyxl

from src.ingestion.models import IngestionError
from src.ingestion.validators import ClaimDataValidator
from src.ai import groq_agent

logger = logging.getLogger(__name__)

class JsonClaimParser:
    @staticmethod
    def parse(content: bytes) -> List[Dict[str, Any]]:
        text = content.decode("utf-8")
        data = json.loads(text)
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("JSON must contain an object or array of claim objects.")

class CsvClaimParser:
    """
    Parses CSV where each row represents a line item, grouped by claim_id.
    """
    @staticmethod
    def parse(content: bytes) -> List[Dict[str, Any]]:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        claims_map: Dict[str, Dict[str, Any]] = {}

        for row_idx, row in enumerate(reader, start=2):
            cid = str(row.get("claim_id", "")).strip()
            if not cid:
                continue

            if cid not in claims_map:
                claims_map[cid] = {
                    "claim_id": cid,
                    "case_title": row.get("case_title", f"Claim {cid}"),
                    "policy_id": row.get("policy_id", ""),
                    "claimant": {
                        "claimant_id": row.get("claimant_id", f"C-{cid}"),
                        "name": row.get("claimant_name", ""),
                        "relationship_to_insured": row.get("relationship", "SELF"),
                        "age": row.get("age", 35),
                    },
                    "incident_details": {
                        "admission_date": row.get("admission_date", ""),
                        "discharge_date": row.get("discharge_date", ""),
                        "hospital_id": row.get("hospital_id", "HOSP-001"),
                        "hospital_name": row.get("hospital_name", ""),
                        "icd10_code": row.get("icd10_code", ""),
                        "diagnosis_description": row.get("diagnosis", ""),
                        "policy_tenure_months": int(row.get("tenure_months", 12) or 12),
                        "is_pre_existing": str(row.get("is_pre_existing", "false")).lower() in ["true", "1", "yes"],
                        "proposed_settlement_amount": float(row.get("proposed_settlement", 0.0) or 0.0),
                    },
                    "line_items": [],
                    "_row_number": row_idx,
                }

            # Append line item if line details exist
            line_desc = row.get("description", "").strip()
            if line_desc:
                qty = float(row.get("quantity", 1.0) or 1.0)
                unit_price = float(row.get("unit_price", 0.0) or 0.0)
                total_amt = float(row.get("total_amount", qty * unit_price) or (qty * unit_price))
                claims_map[cid]["line_items"].append({
                    "line_id": row.get("line_id", f"L{len(claims_map[cid]['line_items'])+1}"),
                    "category": row.get("category", "GENERAL").strip().upper(),
                    "item_code": row.get("item_code", "ITEM-01"),
                    "description": line_desc,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_amount": total_amt,
                    "service_date": row.get("service_date", row.get("admission_date")),
                })

        return list(claims_map.values())

class ExcelClaimParser:
    """
    Parses Excel (.xlsx) files.
    """
    @staticmethod
    def parse(content: bytes) -> List[Dict[str, Any]]:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            return []

        headers = [str(h).strip().lower() if h else "" for h in rows[0]]
        claims_map: Dict[str, Dict[str, Any]] = {}

        for row_idx, r_values in enumerate(rows[1:], start=2):
            row = {headers[i]: r_values[i] for i in range(min(len(headers), len(r_values)))}
            cid = str(row.get("claim_id", "")).strip()
            if not cid:
                continue

            if cid not in claims_map:
                claims_map[cid] = {
                    "claim_id": cid,
                    "case_title": row.get("case_title", f"Claim {cid}"),
                    "policy_id": str(row.get("policy_id", "")),
                    "claimant": {
                        "claimant_id": str(row.get("claimant_id", f"C-{cid}")),
                        "name": str(row.get("claimant_name", "")),
                        "relationship_to_insured": str(row.get("relationship", "SELF")),
                        "age": row.get("age", 35),
                    },
                    "incident_details": {
                        "admission_date": str(row.get("admission_date", "")),
                        "discharge_date": str(row.get("discharge_date", "")),
                        "hospital_id": str(row.get("hospital_id", "HOSP-001")),
                        "hospital_name": str(row.get("hospital_name", "")),
                        "icd10_code": str(row.get("icd10_code", "")),
                        "diagnosis_description": str(row.get("diagnosis", "")),
                        "policy_tenure_months": int(row.get("tenure_months", 12) or 12),
                        "is_pre_existing": str(row.get("is_pre_existing", "false")).lower() in ["true", "1", "yes"],
                        "proposed_settlement_amount": float(row.get("proposed_settlement", 0.0) or 0.0),
                    },
                    "line_items": [],
                    "_row_number": row_idx,
                }

            line_desc = str(row.get("description", "")).strip()
            if line_desc:
                qty = float(row.get("quantity", 1.0) or 1.0)
                unit_price = float(row.get("unit_price", 0.0) or 0.0)
                total_amt = float(row.get("total_amount", qty * unit_price) or (qty * unit_price))
                claims_map[cid]["line_items"].append({
                    "line_id": str(row.get("line_id", f"L{len(claims_map[cid]['line_items'])+1}")),
                    "category": str(row.get("category", "GENERAL")).strip().upper(),
                    "item_code": str(row.get("item_code", "ITEM-01")),
                    "description": line_desc,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_amount": total_amt,
                    "service_date": str(row.get("service_date", row.get("admission_date"))),
                })

        return list(claims_map.values())

class DocumentTextParser:
    """
    Uses Groq Qwen LLM to extract structured claim data from unstructured
    hospital bills, discharge summaries, or clinical text reports.
    """
    @staticmethod
    def parse_document(text_content: str) -> Dict[str, Any]:
        if not groq_agent.is_available:
            raise RuntimeError("Groq API key required for AI-powered document extraction.")

        prompt = f"""You are an expert Insurance Medical Bill & Claims Parser.
Extract structured insurance claim details from the following document text into strict JSON:

Document Content:
---
{text_content}
---

Return ONLY valid JSON matching this schema:
{{
  "claim_id": "<extracted or generated ID, e.g. CLM-DOC-001>",
  "policy_id": "<policy number or POL-COMPREHENSIVE-01 if not found>",
  "case_title": "<Short summary of the medical case>",
  "claimant": {{
    "claimant_id": "C-001",
    "name": "<Patient/Claimant Name>",
    "relationship_to_insured": "SELF",
    "age": <age as integer>
  }},
  "incident_details": {{
    "admission_date": "YYYY-MM-DD",
    "discharge_date": "YYYY-MM-DD",
    "hospital_id": "HOSP-001",
    "hospital_name": "<Hospital Name>",
    "icd10_code": "<ICD-10 code if present or inferred>",
    "diagnosis_description": "<Primary Diagnosis>",
    "policy_tenure_months": 12,
    "is_pre_existing": false,
    "proposed_settlement_amount": <total claimed amount>
  }},
  "line_items": [
    {{
      "line_id": "L1",
      "category": "ROOM_RENT|SURGERY|CONSUMABLE|PHARMACY|INVESTIGATION|CONSULTATION|ADMINISTRATIVE",
      "item_code": "<code or auto-generated>",
      "description": "<Description of service or medicine>",
      "quantity": <number>,
      "unit_price": <number>,
      "total_amount": <quantity * unit_price>
    }}
  ]
}}"""

        response = groq_agent.client.chat.completions.create(
            model=groq_agent.model,
            messages=[
                {"role": "system", "content": "You are a specialized document OCR and insurance claims extraction assistant."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1500,
        )

        content = response.choices[0].message.content
        return json.loads(content)
