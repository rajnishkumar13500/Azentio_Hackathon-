import json
from typing import Dict, Any, List
from app.ingestion.parsers.base import BaseParser, ParsingResult, ParsedSourceRecord

class JSONParser(BaseParser):
    COLLECTION_TYPE_MAP = {
        "policies": "POLICY",
        "policy": "POLICY",
        "claims": "CLAIM",
        "claim": "CLAIM",
        "invoices": "INVOICE",
        "invoice": "INVOICE",
        "line_items": "INVOICE_LINE_ITEM",
        "invoice_line_items": "INVOICE_LINE_ITEM",
        "settlements": "SETTLEMENT",
        "settlement": "SETTLEMENT",
        "providers": "PROVIDER",
        "provider": "PROVIDER",
        "history": "CLAIM_HISTORY",
        "claim_history": "CLAIM_HISTORY",
    }

    def infer_record_type(self, payload: Dict[str, Any]) -> str:
        keys = [k.lower() for k in payload.keys()]
        if "policy_number" in keys or "sum_insured" in keys:
            return "POLICY"
        if "provider_name" in keys or "provider_type" in keys:
            return "PROVIDER"
        if "service_code" in keys or "unit_price" in keys:
            return "INVOICE_LINE_ITEM"
        if "invoice_reference" in keys or "total_amount" in keys:
            return "INVOICE"
        if "settlement_status" in keys or "approved_amount" in keys:
            return "SETTLEMENT"
        if "event_type" in keys or "event_description" in keys:
            return "CLAIM_HISTORY"
        if "claim_id" in keys or "requested_amount" in keys:
            return "CLAIM"
        return "CLAIM"

    def parse(self, file_path: str, filename: str, **kwargs) -> ParsingResult:
        records: List[ParsedSourceRecord] = []
        parsing_errors: List[Dict[str, Any]] = []
        detected_types = set()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return ParsingResult(
                success=False,
                total_rows_read=0,
                records=[],
                parsing_errors=[{
                    "source_file": filename,
                    "error": f"Invalid JSON syntax: line {e.lineno}, col {e.colno} ({e.msg})"
                }],
                detected_record_types=[]
            )
        except Exception as e:
            return ParsingResult(
                success=False,
                total_rows_read=0,
                records=[],
                parsing_errors=[{
                    "source_file": filename,
                    "error": f"Failed to read JSON: {str(e)}"
                }],
                detected_record_types=[]
            )

        total_rows = 0

        # Pattern 1: JSON array of records
        if isinstance(data, list):
            for idx, item in enumerate(data):
                total_rows += 1
                row_idx = idx + 1
                if not isinstance(item, dict):
                    parsing_errors.append({
                        "source_file": filename,
                        "source_row": row_idx,
                        "error": f"Expected JSON object at index {idx}, received {type(item).__name__}"
                    })
                    continue

                rec_type = kwargs.get("record_type") or self.infer_record_type(item)
                detected_types.add(rec_type)

                source_rec_id = None
                for key in ["claim_id", "policy_number", "invoice_id", "line_item_id", "settlement_id", "provider_id", "history_id", "id"]:
                    if key in item and item[key] is not None:
                        source_rec_id = str(item[key])
                        break

                records.append(ParsedSourceRecord(
                    source_file=filename,
                    source_row=row_idx,
                    source_record_id=source_rec_id,
                    record_type_hint=rec_type,
                    raw_payload=item,
                    is_skipped=False
                ))

        # Pattern 2: JSON object containing named collections
        elif isinstance(data, dict):
            # Check if this dict has named collections or is a single record
            has_collections = any(k in self.COLLECTION_TYPE_MAP and isinstance(v, list) for k, v in data.items())
            
            if has_collections:
                for coll_name, items in data.items():
                    target_rec_type = self.COLLECTION_TYPE_MAP.get(coll_name.lower())
                    if not target_rec_type:
                        # Unknown collection in JSON
                        parsing_errors.append({
                            "source_file": filename,
                            "error": f"Unrecognized collection '{coll_name}' in JSON. Must be one of: {list(self.COLLECTION_TYPE_MAP.keys())}"
                        })
                        continue

                    if not isinstance(items, list):
                        parsing_errors.append({
                            "source_file": filename,
                            "error": f"Collection '{coll_name}' must be an array of records."
                        })
                        continue

                    detected_types.add(target_rec_type)
                    for idx, item in enumerate(items):
                        total_rows += 1
                        row_idx = idx + 1
                        if not isinstance(item, dict):
                            parsing_errors.append({
                                "source_file": filename,
                                "source_sheet": coll_name,
                                "source_row": row_idx,
                                "error": f"Expected object in collection '{coll_name}' at index {idx}"
                            })
                            continue

                        source_rec_id = None
                        for key in ["claim_id", "policy_number", "invoice_id", "line_item_id", "settlement_id", "provider_id", "history_id", "id"]:
                            if key in item and item[key] is not None:
                                source_rec_id = str(item[key])
                                break

                        records.append(ParsedSourceRecord(
                            source_file=filename,
                            source_sheet=coll_name,
                            source_row=row_idx,
                            source_record_id=source_rec_id,
                            record_type_hint=target_rec_type,
                            raw_payload=item,
                            is_skipped=False
                        ))
            else:
                # Single record dictionary
                total_rows = 1
                rec_type = kwargs.get("record_type") or self.infer_record_type(data)
                detected_types.add(rec_type)
                source_rec_id = None
                for key in ["claim_id", "policy_number", "invoice_id", "line_item_id", "settlement_id", "provider_id", "history_id", "id"]:
                    if key in data and data[key] is not None:
                        source_rec_id = str(data[key])
                        break

                records.append(ParsedSourceRecord(
                    source_file=filename,
                    source_row=1,
                    source_record_id=source_rec_id,
                    record_type_hint=rec_type,
                    raw_payload=data,
                    is_skipped=False
                ))
        else:
            return ParsingResult(
                success=False,
                total_rows_read=0,
                records=[],
                parsing_errors=[{
                    "source_file": filename,
                    "error": f"Unsupported JSON root type '{type(data).__name__}'. Expected array or object."
                }],
                detected_record_types=[]
            )

        return ParsingResult(
            success=True,
            total_rows_read=total_rows,
            records=records,
            parsing_errors=parsing_errors,
            detected_record_types=list(detected_types)
        )
