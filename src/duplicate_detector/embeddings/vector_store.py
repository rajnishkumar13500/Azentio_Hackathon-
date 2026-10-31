"""
In-Memory Semantic Vector Index for Fast Claims & Line Items Nearest-Neighbor Search.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from .embedder import ClinicalSemanticEmbedder, default_clinical_embedder


class ClinicalVectorIndex:
    """Indexed vector repository enabling fast cosine-similarity searches across historical claims."""

    def __init__(self, embedder: ClinicalSemanticEmbedder = default_clinical_embedder):
        self.embedder = embedder
        self.item_ids: List[str] = []
        self.metadata: List[Dict[str, Any]] = []
        self.vectors: List[np.ndarray] = []
        self._matrix: np.ndarray = np.empty((0, 0))

    def index_items(self, items: List[Dict[str, Any]], text_field: str = "service_description", id_field: str = "line_id"):
        """Indexes a batch of claim line items into the vector space."""
        texts = [item.get(text_field, "") for item in items]
        self.embedder.fit(texts)

        for item in items:
            text = item.get(text_field, "")
            vec = self.embedder.embed(text)
            self.item_ids.append(item.get(id_field, ""))
            self.metadata.append(item)
            self.vectors.append(vec)

        if self.vectors:
            self._matrix = np.vstack(self.vectors)

    def search_similar(
        self,
        query_text: str,
        top_k: int = 5,
        min_similarity: float = 0.70
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Finds the top-k most semantically similar historical records to the query text.
        Returns a list of (metadata_dict, cosine_similarity_score).
        """
        if self._matrix.size == 0 or not query_text:
            return []

        query_vec = self.embedder.embed(query_text)
        
        # Matrix dot product against all indexed vectors
        scores = np.dot(self._matrix, query_vec)

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score >= min_similarity:
                results.append((self.metadata[idx], round(score, 3)))

        return results

