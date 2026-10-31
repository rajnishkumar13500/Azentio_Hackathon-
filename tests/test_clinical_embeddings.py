"""
Tests for Clinical Domain Tokenization, Medical Semantic Embeddings, and Vector Index.
"""

import unittest
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from duplicate_detector.embeddings import (
    ClinicalTokenizer,
    ClinicalSemanticEmbedder,
    ClinicalVectorIndex,
    BertSemanticEmbedder,
    get_semantic_embedder
)


class TestClinicalEmbeddings(unittest.TestCase):

    def setUp(self):
        self.tokenizer = ClinicalTokenizer(expand_synonyms=True, remove_stopwords=True)
        self.embedder = ClinicalSemanticEmbedder()

    def test_synonym_expansion_tokenization(self):
        """Tests that clinical acronyms expand to canonical medical concepts."""
        tokens_ecg = self.tokenizer.tokenize("12-Lead ECG Test")
        self.assertIn("electrocardiogram", tokens_ecg)

        tokens_cbc = self.tokenizer.tokenize("Routine CBC Panel")
        self.assertIn("complete_blood_count", tokens_cbc)

        tokens_mri = self.tokenizer.tokenize("Magnetic Resonance Imaging Left Knee Joint")
        self.assertIn("mri_scan", tokens_mri)

    def test_medical_semantic_similarity(self):
        """Tests that semantically identical medical procedures have high cosine similarity."""
        # 1. ECG vs EKG
        s1 = "12-Lead Electrocardiogram (ECG)"
        s2 = "12-Lead EKG Cardiac Evaluation"
        sim_ecg = self.embedder.cosine_similarity(s1, s2)
        self.assertGreaterEqual(sim_ecg, 0.60)

        # 2. CBC vs Hemogram
        s3 = "Complete Blood Count (CBC) with Platelets"
        s4 = "Complete Hemogram with Platelet Analysis"
        sim_cbc = self.embedder.cosine_similarity(s3, s4)
        self.assertGreaterEqual(sim_cbc, 0.60)

        # 3. MRI Acronym vs Full Name
        s5 = "MRI Left Knee Joint without Contrast"
        s6 = "Magnetic Resonance Imaging Left Knee Joint"
        sim_mri = self.embedder.cosine_similarity(s5, s6)
        self.assertGreaterEqual(sim_mri, 0.60)

    def test_orthogonal_services_low_similarity(self):
        """Unrelated medical procedures must have near-zero semantic similarity."""
        s_knee = "MRI Left Knee Joint without Contrast"
        s_eye = "Phacoemulsification with Foldable IOL (Right Eye)"
        sim = self.embedder.cosine_similarity(s_knee, s_eye)
        self.assertLess(sim, 0.30)

    def test_vector_index_search(self):
        """Tests fast cosine-similarity search in the ClinicalVectorIndex."""
        historical_lines = [
            {"line_id": "L1", "service_description": "Complete Blood Count (CBC) with Platelets"},
            {"line_id": "L2", "service_description": "MRI Left Knee Joint without Contrast"},
            {"line_id": "L3", "service_description": "Single Private Room Rent (4 Days)"},
            {"line_id": "L4", "service_description": "12-Lead Electrocardiogram (ECG)"}
        ]

        index = ClinicalVectorIndex(embedder=self.embedder)
        index.index_items(historical_lines, text_field="service_description", id_field="line_id")

        # Query using clinical synonym "Hemogram Platelet"
        matches = index.search_similar("Complete Hemogram Platelet Examination", top_k=2)
        self.assertGreater(len(matches), 0)
        top_match, score = matches[0]
        self.assertEqual(top_match["line_id"], "L1")
        self.assertGreaterEqual(score, 0.70)

    def test_bert_embedder_interface(self):
        """Tests that BertSemanticEmbedder initializes and provides a valid interface."""
        bert = BertSemanticEmbedder("sentence-transformers/all-MiniLM-L6-v2")
        self.assertIsNotNone(bert)
        self.assertEqual(bert.model_name, "sentence-transformers/all-MiniLM-L6-v2")

    def test_embedder_factory(self):
        """Tests that get_semantic_embedder selects an active embedder."""
        embedder = get_semantic_embedder(prefer_bert=True)
        self.assertIsNotNone(embedder)
        self.assertTrue(hasattr(embedder, "cosine_similarity"))
        self.assertTrue(hasattr(embedder, "embed"))
        # Test similarity functionality through factory-provided embedder
        sim = embedder.cosine_similarity("Complete Blood Count", "Complete Blood Count")
        self.assertEqual(sim, 1.0)


if __name__ == "__main__":
    unittest.main()
