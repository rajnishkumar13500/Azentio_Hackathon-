import os
from typing import Dict, Any, List
from app.ingestion.parsers.base import BaseParser, ParsingResult, ParsedSourceRecord
from app.ingestion.documents.ocr_interface import OCRProvider
from app.ingestion.documents.tesseract_provider import TesseractProvider
from app.ingestion.documents.field_extractor import DocumentFieldExtractor

class ImageParser(BaseParser):
    def __init__(self, ocr_provider: OCRProvider = None):
        self.ocr_provider = ocr_provider or TesseractProvider()

    def parse(self, file_path: str, filename: str, **kwargs) -> ParsingResult:
        records: List[ParsedSourceRecord] = []
        parsing_errors: List[Dict[str, Any]] = []

        if not os.path.exists(file_path):
            return ParsingResult(
                success=False,
                total_rows_read=0,
                records=[],
                parsing_errors=[{"source_file": filename, "error": f"Image file '{file_path}' does not exist"}],
                detected_record_types=[]
            )

        try:
            ocr_res = self.ocr_provider.extract_text(file_path)
            fields = DocumentFieldExtractor.extract_candidate_fields(ocr_res.text)

            raw_payload = {
                "document_type": "IMAGE_OCR",
                "extracted_text": ocr_res.text,
                "extraction_method": ocr_res.ocr_provider,
                "confidence": ocr_res.confidence,
                "words_detected": len(ocr_res.words),
                **fields
            }

            source_rec_id = fields.get("claim_id") or fields.get("invoice_reference") or "IMG-001"

            records.append(ParsedSourceRecord(
                source_file=filename,
                source_page=ocr_res.page_number,
                source_record_id=source_rec_id,
                record_type_hint=kwargs.get("record_type") or "INVOICE",
                raw_payload=raw_payload,
                is_skipped=False
            ))

            return ParsingResult(
                success=True,
                total_rows_read=1,
                records=records,
                parsing_errors=parsing_errors,
                detected_record_types=["INVOICE"]
            )

        except Exception as e:
            return ParsingResult(
                success=False,
                total_rows_read=0,
                records=[],
                parsing_errors=[{"source_file": filename, "error": f"Image OCR parsing failed: {str(e)}"}],
                detected_record_types=[]
            )
