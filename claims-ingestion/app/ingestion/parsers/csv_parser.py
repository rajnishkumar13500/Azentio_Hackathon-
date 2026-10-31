import csv
import os
from typing import Dict, Any, List
from app.ingestion.parsers.base import BaseParser, ParsingResult, ParsedSourceRecord

class CSVParser(BaseParser):
    def infer_record_type(self, headers: List[str], filename: str) -> str:
        h_lower = [h.strip().lower() for h in headers if h]
        fn_lower = filename.lower()
        
        # Check filename first if distinctive
        if "claim" in fn_lower:
            return "CLAIM"
        if "policy" in fn_lower or "policies" in fn_lower:
            return "POLICY"
        if "provider" in fn_lower:
            return "PROVIDER"
        if "line" in fn_lower or "item" in fn_lower:
            return "INVOICE_LINE_ITEM"
        if "invoice" in fn_lower or "bill" in fn_lower:
            return "INVOICE"
        if "settle" in fn_lower:
            return "SETTLEMENT"
        if "history" in fn_lower:
            return "CLAIM_HISTORY"

        # Check headers (more specific first)
        if any(h in ["line_item_id", "service_code"] for h in h_lower):
            return "INVOICE_LINE_ITEM"
        if any(h in ["invoice_id", "invoice_reference"] for h in h_lower):
            return "INVOICE"
        if any(h in ["settlement_id", "approved_amount", "paid_amount"] for h in h_lower):
            return "SETTLEMENT"
        if any(h in ["history_id", "event_type", "event_description"] for h in h_lower):
            return "CLAIM_HISTORY"
        if any(h in ["claim_id", "claimant_name", "incident_date"] for h in h_lower):
            return "CLAIM"
        if any(h in ["sum_insured", "effective_from", "effective_to"] for h in h_lower):
            return "POLICY"
        if any(h in ["provider_id", "provider_name", "provider_code"] for h in h_lower):
            return "PROVIDER"
        return "CLAIM"

    def parse(self, file_path: str, filename: str, **kwargs) -> ParsingResult:
        records: List[ParsedSourceRecord] = []
        parsing_errors: List[Dict[str, Any]] = []
        
        # Test encodings
        encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252"]
        content = None
        used_encoding = "utf-8"
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                    used_encoding = enc
                    break
            except (UnicodeDecodeError, Exception):
                continue
        
        if content is None:
            return ParsingResult(
                success=False,
                total_rows_read=0,
                records=[],
                parsing_errors=[{
                    "source_file": filename,
                    "error": "Failed to decode CSV file with supported encodings (UTF-8, Latin1, CP1252)."
                }],
                detected_record_types=[]
            )

        lines = content.splitlines()
        if not lines:
            return ParsingResult(
                success=True,
                total_rows_read=0,
                records=[],
                parsing_errors=[{
                    "source_file": filename,
                    "error": "File is empty."
                }],
                detected_record_types=[]
            )

        reader = csv.reader(lines)
        try:
            headers = next(reader)
        except StopIteration:
            return ParsingResult(
                success=True,
                total_rows_read=0,
                records=[],
                parsing_errors=[{
                    "source_file": filename,
                    "error": "File has no headers."
                }],
                detected_record_types=[]
            )

        cleaned_headers = [h.strip() for h in headers]
        default_record_type = kwargs.get("record_type") or self.infer_record_type(cleaned_headers, filename)
        detected_types = {default_record_type}

        row_idx = 1
        for row in reader:
            row_idx += 1
            # Check if row is blank
            if not row or all(col.strip() == "" for col in row):
                records.append(ParsedSourceRecord(
                    source_file=filename,
                    source_row=row_idx,
                    record_type_hint=default_record_type,
                    raw_payload={},
                    is_skipped=True,
                    skip_reason="Blank spreadsheet row"
                ))
                continue

            # Check if column count matches headers
            if len(row) > len(cleaned_headers):
                # Extra columns
                parsing_errors.append({
                    "source_file": filename,
                    "source_row": row_idx,
                    "error": f"Row has {len(row)} columns, expected {len(cleaned_headers)} headers."
                })
                # We still store it with padding
            payload = {}
            for i, header in enumerate(cleaned_headers):
                val = row[i].strip() if i < len(row) else ""
                payload[header] = val

            # Detect source_record_id candidate
            source_rec_id = None
            for key in ["claim_id", "policy_number", "invoice_id", "line_item_id", "settlement_id", "provider_id", "history_id", "id"]:
                if key in payload and payload[key]:
                    source_rec_id = str(payload[key])
                    break

            records.append(ParsedSourceRecord(
                source_file=filename,
                source_row=row_idx,
                source_record_id=source_rec_id,
                record_type_hint=default_record_type,
                raw_payload=payload,
                is_skipped=False
            ))

        return ParsingResult(
            success=True,
            total_rows_read=row_idx,
            records=records,
            parsing_errors=parsing_errors,
            detected_record_types=list(detected_types)
        )
