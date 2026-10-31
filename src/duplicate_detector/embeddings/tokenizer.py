"""
Clinical Domain Tokenizer with Medical Canonical Concept Normalization and Multi-Word Phrase Mapping.
Normalizes healthcare jargon, abbreviations, and clinical terminology to canonical concept tokens.
"""

import re
from typing import List, Set, Dict

# Multi-word clinical phrases mapped to canonical concept tokens (checked first)
MULTI_WORD_CLINICAL_CONCEPTS: Dict[str, str] = {
    "magnetic resonance imaging": "mri_scan",
    "complete blood count": "complete_blood_count",
    "complete hemogram": "complete_blood_count",
    "thyroid stimulating hormone": "thyroid_profile",
    "thyroid profile": "thyroid_profile",
    "thyroid function test": "thyroid_profile",
    "whole abdomen": "abdomen_scan",
    "physical therapy": "physiotherapy",
    "computed tomography": "ct_scan",
    "cardiac evaluation": "cardiac_assessment",
    "post op": "post_op",
    "right eye": "eye_ocular",
    "left eye": "eye_ocular"
}

# Single token canonical mappings
SINGLE_TOKEN_CONCEPTS: Dict[str, str] = {
    "ekg": "electrocardiogram",
    "ecg": "electrocardiogram",
    "electrocardiogram": "electrocardiogram",
    "electrocardiography": "electrocardiogram",
    "cbc": "complete_blood_count",
    "hemogram": "complete_blood_count",
    "mri": "mri_scan",
    "usg": "ultrasound",
    "ultrasonography": "ultrasound",
    "sonogram": "ultrasound",
    "echo": "echocardiography",
    "echocardiogram": "echocardiography",
    "angio": "angiography",
    "angiogram": "angiography",
    "platelets": "platelet",
    "physio": "physiotherapy",
    "rehab": "physiotherapy",
    "phaco": "cataract_surgery",
    "iol": "cataract_surgery",
    "xray": "radiography",
    "radiograph": "radiography"
}

# Clinical stopwords
CLINICAL_STOPWORDS: Set[str] = {
    "with", "without", "and", "or", "for", "the", "in", "on", "at", "to",
    "of", "by", "per", "day", "days", "unit", "units", "charge", "charges",
    "fee", "cost", "examination", "assessment", "evaluation", "procedure",
    "department", "hospital", "clinic", "test", "tests", "panel", "scan", "total"
}


class ClinicalTokenizer:
    """Clinical-aware tokenizer that normalizes medical phrases and terms into canonical concepts."""

    def __init__(self, expand_synonyms: bool = True, remove_stopwords: bool = True):
        self.expand_synonyms = expand_synonyms
        self.remove_stopwords = remove_stopwords

    def clean_and_normalize(self, text: str) -> str:
        """Lowercases, splits punctuation, and normalizes multi-word clinical concepts."""
        if not text:
            return ""
        text = text.lower().replace("-", " ")
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = " ".join(text.split())

        # Map multi-word phrases
        for phrase, concept in MULTI_WORD_CLINICAL_CONCEPTS.items():
            if phrase in text:
                text = text.replace(phrase, concept)

        return text

    def tokenize(self, text: str) -> List[str]:
        """Tokenizes text into a clean list of canonical clinical tokens."""
        normalized_text = self.clean_and_normalize(text)
        tokens = normalized_text.split()

        clean_tokens: List[str] = []
        for tok in tokens:
            if self.remove_stopwords and tok in CLINICAL_STOPWORDS:
                continue

            # Map single token to canonical concept if applicable
            canonical = SINGLE_TOKEN_CONCEPTS.get(tok, tok) if self.expand_synonyms else tok
            clean_tokens.append(canonical)

        return clean_tokens

    def get_character_ngrams(self, text: str, n_min: int = 3, n_max: int = 5) -> List[str]:
        """Generates subword character n-grams for typo robustness."""
        cleaned = re.sub(r"[^a-z0-9]", "", text.lower())
        ngrams: List[str] = []
        length = len(cleaned)
        for n in range(n_min, min(n_max + 1, length + 1)):
            for i in range(length - n + 1):
                ngrams.append(cleaned[i:i + n])
        return ngrams
