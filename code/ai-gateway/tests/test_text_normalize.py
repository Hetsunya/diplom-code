"""Unit tests for ASR response normalization."""

from __future__ import annotations

import unittest

from modules.text.normalize import has_transcript_content, normalize_asr_response


class TestNormalizeAsrResponse(unittest.TestCase):
    def test_canonical_keys_passthrough(self) -> None:
        raw = {
            "transcript_partial": "  hi  ",
            "transcript_final": None,
            "language": "ru",
            "text_features": {"confidence": 0.9},
        }
        n = normalize_asr_response(raw)
        self.assertEqual(n["transcript_partial"], "hi")
        self.assertIsNone(n["transcript_final"])
        self.assertEqual(n["language"], "ru")
        self.assertEqual(n["text_features"]["confidence"], 0.9)

    def test_whisper_text_alias(self) -> None:
        n = normalize_asr_response({"text": "  partial line  ", "language": "en"})
        self.assertEqual(n["transcript_partial"], "partial line")
        self.assertIsNone(n["transcript_final"])

    def test_segments_join(self) -> None:
        n = normalize_asr_response(
            {
                "segments": [{"text": " a "}, {"text": "b"}],
                "language": "de",
            }
        )
        self.assertEqual(n["transcript_partial"], "a b")
        self.assertEqual(n["language"], "de")

    def test_final_alias(self) -> None:
        n = normalize_asr_response({"transcript_partial": "x", "final": "done"})
        self.assertEqual(n["transcript_final"], "done")

    def test_has_transcript_content(self) -> None:
        self.assertFalse(has_transcript_content({"transcript_partial": None, "transcript_final": None}))
        self.assertFalse(has_transcript_content({"transcript_partial": "  ", "transcript_final": None}))
        self.assertTrue(has_transcript_content({"transcript_partial": "a", "transcript_final": None}))
        self.assertTrue(has_transcript_content({"transcript_partial": None, "transcript_final": "b"}))


if __name__ == "__main__":
    unittest.main()
