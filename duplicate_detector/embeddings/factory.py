"""
Embedder Factory providing automatic selection between BERT Transformer embeddings
and lightweight Clinical Semantic Embeddings based on environment capabilities.
"""

import sys
from .embedder import ClinicalSemanticEmbedder, default_clinical_embedder
from .bert_embedder import BertSemanticEmbedder


def get_semantic_embedder(
    prefer_bert: bool = True,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
):
    """
    Returns the optimal semantic embedding engine available in the environment:
    1. If prefer_bert=True and PyTorch/Transformers are installed -> Uses BERT.
    2. Otherwise -> Uses ClinicalSemanticEmbedder (0-dependency, high-speed).
    """
    if prefer_bert:
        bert = BertSemanticEmbedder(model_name=model_name)
        if bert.is_loaded:
            sys.stderr.write(f"[EmbedderFactory] 🚀 Active Backend: BERT ({bert.model_name})\n")
            return bert

    sys.stderr.write("[EmbedderFactory] ⚡ Active Backend: Clinical Domain Semantic Embedder\n")
    return default_clinical_embedder

