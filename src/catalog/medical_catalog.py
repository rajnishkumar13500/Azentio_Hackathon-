import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from src.config import settings

class MedicalCatalog:
    def __init__(self, catalog_path: Optional[Path] = None):
        self.catalog_path = catalog_path or settings.CATALOG_FILE
        self._load_catalog()

    def _load_catalog(self):
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Catalog file not found at {self.catalog_path}")
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.icd10_codes: Dict[str, Any] = data.get("icd10_codes", {})
        self.procedure_aliases: Dict[str, str] = data.get("procedure_aliases", {})
        self.irdai_non_payable_consumables: List[str] = [
            item.lower().strip() for item in data.get("irdai_non_payable_consumables", [])
        ]
        self.procedure_benchmarks: Dict[str, Any] = data.get("procedure_benchmarks", {})

    def is_non_payable_consumable(self, item_description: str) -> Tuple[bool, Optional[str]]:
        """
        Deterministic clinical text check with word boundaries:
        Checks if item description matches any known IRDAI non-payable consumables
        or administrative charges (e.g. avoids false matching 'ppe' inside 'appendectomy').
        """
        desc_clean = item_description.lower().strip()
        for consumable in self.irdai_non_payable_consumables:
            # Use word boundary search to avoid substring collisions
            pattern = rf"\b{re.escape(consumable)}\b"
            if re.search(pattern, desc_clean, re.IGNORECASE):
                return True, f"Matches IRDAI Non-Payable item: '{consumable}'"
        return False, None

    def normalize_procedure(self, icd10: Optional[str], description: str) -> Optional[str]:
        """
        Maps an ICD-10 code or procedure description to a standardized policy procedure key.
        e.g., 'Phaco with Foldable IOL' -> 'cataract'
        """
        if icd10 and icd10 in self.icd10_codes:
            return self.icd10_codes[icd10].get("policy_procedure_key")
        
        desc_clean = description.lower()
        for alias, procedure_key in self.procedure_aliases.items():
            if alias in desc_clean:
                return procedure_key
        return None

    def get_benchmark(self, procedure_key: str) -> Optional[Dict[str, Any]]:
        return self.procedure_benchmarks.get(procedure_key)

medical_catalog = MedicalCatalog()
