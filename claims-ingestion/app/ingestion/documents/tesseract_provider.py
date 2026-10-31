import os
import shutil
import subprocess
from typing import List
from app.ingestion.documents.ocr_interface import OCRProvider, OCRResult, OCRWord, OCRBoundingBox

class TesseractProvider(OCRProvider):
    def __init__(self, tesseract_cmd: str = None):
        if tesseract_cmd:
            self.tesseract_cmd = tesseract_cmd
        elif shutil.which("tesseract"):
            self.tesseract_cmd = "tesseract"
        elif os.path.exists("/opt/homebrew/bin/tesseract"):
            self.tesseract_cmd = "/opt/homebrew/bin/tesseract"
        elif os.path.exists("/usr/local/bin/tesseract"):
            self.tesseract_cmd = "/usr/local/bin/tesseract"
        else:
            self.tesseract_cmd = "tesseract"

    def extract_text(self, image_path: str, page_number: int = 1) -> OCRResult:
        if not os.path.exists(image_path):
            return OCRResult(text="", page_number=page_number, confidence=0.0, words=[], ocr_provider="tesseract")

        try:
            # 1. Run tesseract for TSV (which includes text, confidence, bbox)
            cmd_tsv = [self.tesseract_cmd, image_path, "stdout", "tsv"]
            result_tsv = subprocess.run(cmd_tsv, capture_output=True, text=True, check=True)
            
            words: List[OCRWord] = []
            full_text_lines = []
            total_conf = 0.0
            conf_count = 0

            lines = result_tsv.stdout.splitlines()
            if lines and len(lines) > 1:
                header = lines[0].split("\t")
                # tsv columns: level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf, text
                for line in lines[1:]:
                    parts = line.split("\t")
                    if len(parts) >= 12:
                        word_text = parts[11].strip()
                        conf_str = parts[10].strip()
                        try:
                            conf = float(conf_str)
                        except ValueError:
                            conf = -1.0

                        if conf > 0 and word_text:
                            total_conf += conf
                            conf_count += 1
                            try:
                                bbox = OCRBoundingBox(
                                    x=int(parts[6]),
                                    y=int(parts[7]),
                                    width=int(parts[8]),
                                    height=int(parts[9])
                                )
                            except ValueError:
                                bbox = None

                            words.append(OCRWord(text=word_text, confidence=conf, bbox=bbox))

            # 2. Get plain text
            cmd_txt = [self.tesseract_cmd, image_path, "stdout"]
            result_txt = subprocess.run(cmd_txt, capture_output=True, text=True, check=True)
            raw_text = result_txt.stdout.strip()

            avg_conf = (total_conf / conf_count) if conf_count > 0 else 0.0

            return OCRResult(
                text=raw_text,
                page_number=page_number,
                confidence=round(avg_conf, 2),
                words=words,
                ocr_provider="tesseract"
            )

        except Exception as e:
            # Fallback or error
            return OCRResult(
                text=f"OCR execution failed: {str(e)}",
                page_number=page_number,
                confidence=0.0,
                words=[],
                ocr_provider="tesseract"
            )
