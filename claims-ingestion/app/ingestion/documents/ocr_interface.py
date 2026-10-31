from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class OCRBoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: Optional[OCRBoundingBox] = None

class OCRResult(BaseModel):
    text: str
    page_number: int = 1
    confidence: float = 0.0
    words: List[OCRWord] = []
    ocr_provider: str = "tesseract"

class OCRProvider(ABC):
    @abstractmethod
    def extract_text(self, image_path: str, page_number: int = 1) -> OCRResult:
        """Extract text and confidence metrics from image"""
        pass
