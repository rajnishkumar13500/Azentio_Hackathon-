import os
from typing import List, Dict, Any, Tuple
from app.ingestion.documents.ocr_interface import OCRResult
from app.ingestion.documents.tesseract_provider import TesseractProvider

class PDFExtractor:
    def __init__(self, ocr_provider=None):
        self.ocr_provider = ocr_provider or TesseractProvider()

    def extract_text_and_pages(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from PDF file.
        Returns list of dicts: [{"page": 1, "text": "...", "method": "digital" | "ocr", "confidence": 100.0}]
        """
        results = []

        # 1. Try PyMuPDF (fitz)
        pymupdf_available = False
        try:
            import fitz
            pymupdf_available = True
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text().strip()
                if len(text) > 40:
                    results.append({
                        "page": page_num + 1,
                        "text": text,
                        "method": "digital_pymupdf",
                        "confidence": 100.0
                    })
                else:
                    # Page has insufficient text -> render as image and OCR
                    pix = page.get_pixmap()
                    temp_img_path = f"/tmp/page_{page_num + 1}_{os.path.basename(file_path)}.png"
                    pix.save(temp_img_path)
                    ocr_res = self.ocr_provider.extract_text(temp_img_path, page_number=page_num + 1)
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
                    results.append({
                        "page": page_num + 1,
                        "text": ocr_res.text,
                        "method": "ocr_tesseract",
                        "confidence": ocr_res.confidence
                    })
            doc.close()
            return results
        except ImportError:
            pass
        except Exception:
            pass

        # 2. Try pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                text = (page.extract_text() or "").strip()
                results.append({
                    "page": idx + 1,
                    "text": text,
                    "method": "digital_pypdf",
                    "confidence": 95.0 if len(text) > 40 else 20.0
                })
            return results
        except Exception as e:
            results.append({
                "page": 1,
                "text": f"Error reading PDF: {str(e)}",
                "method": "failed",
                "confidence": 0.0
            })
            return results
