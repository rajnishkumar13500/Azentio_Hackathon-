import os
from typing import List, Dict, Any, Optional
from src.ingestion.models import IngestionResult, IngestionError
from src.ingestion.parsers import JsonClaimParser, CsvClaimParser, ExcelClaimParser, DocumentTextParser
from src.ingestion.validators import ClaimDataValidator
from src.schemas import Claim

class IngestionService:
    """
    Unified Ingestion Service for Multi-Format Claims Ingestion:
    - CSV, Excel (.xlsx), JSON, and Sample Document Uploads.
    - Validates identifiers, amounts, dates, and mandatory fields.
    - Guarantees that invalid records are explicitly flagged rather than silently ignored.
    """

    def ingest_file(self, filename: str, content: bytes) -> IngestionResult:
        ext = os.path.splitext(filename)[1].lower().strip(".")
        format_detected = ext

        raw_claims_list: List[Dict[str, Any]] = []
        parse_errors: List[IngestionError] = []
        warnings: List[str] = []

        try:
            if ext in ["json"]:
                raw_claims_list = JsonClaimParser.parse(content)
            elif ext in ["csv"]:
                raw_claims_list = CsvClaimParser.parse(content)
            elif ext in ["xlsx", "xls"]:
                raw_claims_list = ExcelClaimParser.parse(content)
            elif ext in ["txt", "md", "doc"]:
                format_detected = "document"
                text_content = content.decode("utf-8", errors="replace")
                doc_claim = DocumentTextParser.parse_document(text_content)
                raw_claims_list = [doc_claim]
            else:
                return IngestionResult(
                    success=False,
                    source_filename=filename,
                    format_detected=format_detected,
                    errors=[
                        IngestionError(
                            field_name="file_extension",
                            rejected_value=ext,
                            error_message=f"Unsupported file format '{ext}'. Supported formats: CSV, XLSX, JSON, TXT/DOC."
                        )
                    ]
                )
        except Exception as e:
            return IngestionResult(
                success=False,
                source_filename=filename,
                format_detected=format_detected,
                errors=[
                    IngestionError(
                        field_name="file_parsing",
                        rejected_value=str(e),
                        error_message=f"Failed to parse {filename}: {str(e)}"
                    )
                ]
            )

        valid_claims: List[Claim] = []
        validation_errors: List[IngestionError] = []

        for idx, raw_dict in enumerate(raw_claims_list, start=1):
            row_num = raw_dict.get("_row_number", idx)
            claim_obj, errs, warns = ClaimDataValidator.validate_raw_dict(raw_dict, row_idx=row_num)
            warnings.extend(warns)

            if errs:
                validation_errors.extend(errs)
            elif claim_obj:
                valid_claims.append(claim_obj)

        is_success = len(validation_errors) == 0 and len(valid_claims) > 0

        return IngestionResult(
            success=is_success,
            source_filename=filename,
            format_detected=format_detected,
            total_records=len(raw_claims_list),
            valid_records_count=len(valid_claims),
            invalid_records_count=len(raw_claims_list) - len(valid_claims),
            claims=valid_claims,
            errors=validation_errors,
            warnings=warnings,
        )

ingestion_service = IngestionService()

