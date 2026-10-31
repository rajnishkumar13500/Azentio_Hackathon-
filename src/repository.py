import json
from typing import Dict, List, Optional
from src.schemas import Claim
from src.config import settings

class ClaimsRepository:
    """
    In-memory claims portfolio store.
    Starts EMPTY by default as per enterprise requirements:
    Users start with a clean dashboard and ingest claims batches via CSV/Excel/Doc/JSON,
    or click 'Load Sample Batch' to populate with demo data.
    """

    def __init__(self):
        self._claims: Dict[str, Claim] = {}

    def get_all(self) -> List[Claim]:
        return list(self._claims.values())

    def get_by_id(self, claim_id: str) -> Optional[Claim]:
        return self._claims.get(claim_id)

    def add_claims(self, claims: List[Claim]) -> int:
        added_count = 0
        for claim in claims:
            self._claims[claim.claim_id] = claim
            added_count += 1
        return added_count

    def clear(self) -> None:
        self._claims.clear()

    def count(self) -> int:
        return len(self._claims)

    def seed_demo_batch(self) -> List[Claim]:
        """Loads the pre-configured 5 synthetic claims into the repository."""
        with open(settings.SYNTHETIC_CLAIMS_FILE, "r", encoding="utf-8") as f:
            raw_claims = json.load(f)
        loaded = []
        for raw in raw_claims:
            c = Claim(**raw)
            self._claims[c.claim_id] = c
            loaded.append(c)
        return loaded

    def seed_correlation_batch(self) -> List[Claim]:
        """Loads the Level 2 cross-claim correlation dataset into the repository."""
        corr_file = settings.DATA_DIR / "synthetic" / "cross_claim_correlation_dataset.json"
        with open(corr_file, "r", encoding="utf-8") as f:
            raw_claims = json.load(f)
        loaded = []
        for raw in raw_claims:
            c = Claim(**raw)
            self._claims[c.claim_id] = c
            loaded.append(c)
        return loaded

claims_repository = ClaimsRepository()

