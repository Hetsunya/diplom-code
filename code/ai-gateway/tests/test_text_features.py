"""Unit tests for heuristic text_features enrichment."""

from __future__ import annotations

import unittest

from modules.text.features import enrich_text_features


class TestEnrichTextFeatures(unittest.TestCase):
    def test_fills_sentiment_and_keyphrases(self) -> None:
        out = enrich_text_features(
            transcript_partial="Спасибо за отличную работу",
            transcript_final=None,
            text_features={},
        )
        self.assertEqual(out["sentiment"], "positive")
        self.assertIsInstance(out["keyphrases"], list)
        self.assertGreater(len(out["keyphrases"]), 0)
        self.assertIsInstance(out["topics"], list)
        self.assertIsNotNone(out.get("confidence"))

    def test_preserves_asr_features(self) -> None:
        out = enrich_text_features(
            transcript_partial="x",
            transcript_final=None,
            text_features={"sentiment": "negative", "confidence": 0.1, "topics": ["t1"]},
        )
        self.assertEqual(out["sentiment"], "negative")
        self.assertEqual(out["confidence"], 0.1)
        self.assertEqual(out["topics"], ["t1"])

    def test_empty_text_returns_dict_unchanged_structure(self) -> None:
        out = enrich_text_features(
            transcript_partial=None,
            transcript_final=None,
            text_features={"confidence": 0.5},
        )
        self.assertEqual(out.get("confidence"), 0.5)


if __name__ == "__main__":
    unittest.main()
