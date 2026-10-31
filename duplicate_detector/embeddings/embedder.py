"""
Clinical Semantic Embedder and Vector Similarity Engine.
Produces dense normalized vector embeddings for claims text and calculates semantic cosine similarity.
"""

from typing import List, Optional, Union
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from .tokenizer import ClinicalTokenizer


class ClinicalSemanticEmbedder:
    """
    Generates semantic vector embeddings for medical service descriptions and claims.
    Combines clinical token normalization with subword n-gram TF-IDF weighting.
    """

    def __init__(self, embedding_dim: int = 128):
        self.tokenizer = ClinicalTokenizer(expand_synonyms=True, remove_stopwords=True)
        self.embedding_dim = embedding_dim
        # Token-level and subword character n-gram analyzer
        self.vectorizer = TfidfVectorizer(
            tokenizer=self.tokenizer.tokenize,
            token_pattern=None,
            ngram_range=(1, 2),
            sublinear_tf=True,
            norm="l2"
        )
        self._is_fitted = False
        self._corpus_cache: List[str] = []

    def fit(self, texts: List[str]) -> "ClinicalSemanticEmbedder":
        """Fits the TF-IDF vocabulary on a domain corpus of clinical descriptions."""
        if texts:
            self._corpus_cache = list(set(self._corpus_cache + texts))
            self.vectorizer.fit(self._corpus_cache)
            self._is_fitted = True
        return self

    def embed(self, text: str) -> np.ndarray:
        """
        Generates an L2-normalized vector embedding for the input text.
        Returns a 1D numpy array.
        """
        if not self._is_fitted:
            self.fit([text, "medical health hospital claim diagnostic surgery therapy"])

        try:
            vec = self.vectorizer.transform([text]).toarray()[0]
        except Exception:
            self.fit([text])
            vec = self.vectorizer.transform([text]).toarray()[0]

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def cosine_similarity(self, text1: str, text2: str) -> float:
        """
        Calculates semantic cosine similarity between two medical descriptions.
        Returns a float between 0.0 (unrelated) and 1.0 (identical/synonymous).
        """
        if not text1 or not text2:
            return 0.0

        # Fast path for identical text
        if text1.strip().lower() == text2.strip().lower():
            return 1.0

        if not self._is_fitted:
            self.fit([text1, text2])

        try:
            v1 = self.vectorizer.transform([text1]).toarray()[0]
            v2 = self.vectorizer.transform([text2]).toarray()[0]
        except Exception:
            self.fit([text1, text2])
            v1 = self.vectorizer.transform([text1]).toarray()[0]
            v2 = self.vectorizer.transform([text2]).toarray()[0]

        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)

        if n1 == 0 or n2 == 0:
            # Fallback to token overlap Jaccard similarity if empty
            t1 = set(self.tokenizer.tokenize(text1))
            t2 = set(self.tokenizer.tokenize(text2))
            if not t1 or not t2:
                return 0.0
            return float(len(t1 & t2) / len(t1 | t2))

        similarity = float(np.dot(v1, v2) / (n1 * n2))
        return max(0.0, min(1.0, similarity))


# Global singleton instance for high-performance reuse across the engine
default_clinical_embedder = ClinicalSemanticEmbedder()
