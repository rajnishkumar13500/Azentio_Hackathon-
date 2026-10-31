"""
BERT & Transformer-based Semantic Embedding Provider.
Supports HuggingFace Transformers and Sentence-Transformers with Mean Pooling and L2 Normalization.
Includes ClinicalBERT, all-MiniLM-L6-v2, and graceful fallback if torch is not installed.
"""

from typing import List, Optional, Union
import numpy as np


class BertSemanticEmbedder:
    """
    BERT-based semantic embedding engine.
    Computes dense 384-d or 768-d contextual embeddings using Transformer self-attention.
    Supports Bio_ClinicalBERT, all-MiniLM-L6-v2, and standard BERT models.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.is_loaded = False
        self._tokenizer = None
        self._model = None
        self._backend = None  # "sentence_transformers" or "transformers"
        self._load_model()

    def _load_model(self):
        """Attempts to load SentenceTransformer or HuggingFace Transformers."""
        # Method 1: Try sentence_transformers
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._backend = "sentence_transformers"
            self.is_loaded = True
            return
        except ImportError:
            pass
        except Exception:
            pass

        # Method 2: Try HuggingFace transformers + PyTorch
        try:
            import torch
            from transformers import AutoTokenizer, AutoModel

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            self._model.eval()
            self._backend = "transformers"
            self.is_loaded = True
            return
        except ImportError:
            pass
        except Exception:
            pass

        self.is_loaded = False

    def embed(self, text: str) -> np.ndarray:
        """
        Generates an L2-normalized dense vector embedding using BERT self-attention.
        """
        if not text:
            return np.zeros(384)

        if not self.is_loaded:
            raise RuntimeError(
                f"BERT model '{self.model_name}' is not loaded. "
                f"Please ensure 'torch' and 'transformers' or 'sentence-transformers' are installed: "
                f"pip install torch transformers sentence-transformers"
            )

        if self._backend == "sentence_transformers":
            vec = self._model.encode(text, normalize_embeddings=True)
            return np.array(vec, dtype=np.float32)

        elif self._backend == "transformers":
            import torch

            # Tokenize input text with padding and truncation
            inputs = self._tokenizer(
                text,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt"
            )

            with torch.no_grad():
                outputs = self._model(**inputs)
                # Mean Pooling: take average of token embeddings weighted by attention mask
                token_embeddings = outputs[0]  # First element has all token embeddings
                input_mask_expanded = inputs["attention_mask"].unsqueeze(-1).expand(token_embeddings.size()).float()
                sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
                sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                mean_pooled = sum_embeddings / sum_mask

                # L2 normalize
                normalized = torch.nn.functional.normalize(mean_pooled, p=2, dim=1)
                return normalized.squeeze(0).cpu().numpy().astype(np.float32)

    def cosine_similarity(self, text1: str, text2: str) -> float:
        """
        Computes cosine similarity between two medical texts in BERT embedding space:
        cos(u, v) = (u . v) / (||u|| * ||v||)
        """
        if not text1 or not text2:
            return 0.0

        if text1.strip().lower() == text2.strip().lower():
            return 1.0

        u = self.embed(text1)
        v = self.embed(text2)

        # Dot product of L2 normalized vectors
        dot = float(np.dot(u, v))
        return max(0.0, min(1.0, dot))

