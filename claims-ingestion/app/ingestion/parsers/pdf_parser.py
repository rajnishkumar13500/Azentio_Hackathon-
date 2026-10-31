import os
from typing import Dict, Any, List
from app.ingestion.parsers.base import BaseParser, ParsingResult, ParsedSourceRecord
from app.ingestion.documents.pdf_extractor import PDFExtractor
from app.ingestion.documents.field_extractor import DocumentFieldExtractor

class PDFParser(BaseParser):
    def __init__(self, pdf_extractor: PDFExtractor = None):
        self.pdf_extractor = pdf_extractor or PDFExtractor()

    def parse(self, file_path: str, filename: str, **kwargs) -> ParsingResult:
        records: List[ParsedSourceRecord] = []
        parsing_errors: List[Dict[str, Any]] = []

        if not os.path.exists(file_path):
            return ParsingResult(
                success=False,
                total_rows_read=0,
                records=[],
                parsing_errors=[{"source_file": filename, "error": f"File '{file_path}' does not exist"}],
                detected_record_types=[]
            )

        try:
            pages = self.pdf_extractor.extract_text_and_pages(file_path)
            if not pages:
                return ParsingResult(
                    success=True,
                    total_rows_read=0,
                    records=[],
                    parsing_errors=[{"source_file": filename, "error": "PDF has no extractable pages or text"}],
                    detected_record_types=[]
                )

            for p in pages:
                page_num = p.get("page", 1)
                text = p.get("text", "")
                method = p.get("method", "digital")
                conf = p.get("confidence", 0.0)

                fields = DocumentFieldExtractor.extract_candidate_fields(text)
                
                raw_payload = {
                    "document_type": "PDF",
                    "page_number": page_num,
                    "extracted_text": text,
                    "extraction_method": method,
                    "confidence": conf,
                    **fields
                }

                source_rec_id = fields.get("claim_id") or fields.get("invoice_reference") or f"PDF-P{page_num}"

                records.append(ParsedSourceRecord(
                    source_file=filename,
                    source_page=page_num,
                    source_record_id=source_rec_id,
                    record_type_hint=kwargs.get("record_type") or "INVOICE",
                    raw_payload=raw_payload,
                    is_skipped=False
                ))

            return ParsingResult(
                success=True,
                total_rows_read=len(records),
                records=records,
                parsing_errors=parsing_errors,
                detected_record_types=["INVOICE"]
            )

        except Exception as e:
            return ParsingResult(
                success=False,
                total_rows_read=0,
                records=[],
                parsing_errors=[{"source_file": filename, "error": f"PDF parsing failed: {str(e)}"}],
                detected_record_types=[]
            )
