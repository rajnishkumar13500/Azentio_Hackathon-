from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ParsedSourceRecord(BaseModel):
    source_file: str
    source_sheet: Optional[str] = None
    source_row: Optional[int] = None
    source_page: Optional[int] = None
    source_record_id: Optional[str] = None
    record_type_hint: Optional[str] = None
    raw_payload: Dict[str, Any]
    is_skipped: bool = False
    skip_reason: Optional[str] = None

class ParsingResult(BaseModel):
    success: bool
    total_rows_read: int
    records: List[ParsedSourceRecord]
    parsing_errors: List[Dict[str, Any]]
    detected_record_types: List[str]

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, filename: str, **kwargs) -> ParsingResult:
        pass
