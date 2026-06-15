"""Unit tests for report data_quality augmentation."""

from __future__ import annotations

import unittest

from modules.report.data_quality import augment_report_data_quality


class TestAugmentReportDataQuality(unittest.TestCase):
    def test_first_tick_no_false_positive(self) -> None:
        curr = {"text_analysis_errors": 5, "face_inference_errors": 1}
        prev = curr
        out = augment_report_data_quality({"session_id": 1, "summary": "x"}, curr, prev)
        dq = out.get("data_quality")
        assert isinstance(dq, dict)
        self.assertTrue(dq["complete"])
        self.assertEqual(dq["degraded_sources"], [])
        self.assertEqual(dq["counters_window"]["text_analysis_errors"], 0)

    def test_delta_marks_text_and_face(self) -> None:
        prev = {"text_analysis_errors": 1, "speech_service_circuit_open": 0, "face_inference_errors": 0}
        curr = {"text_analysis_errors": 3, "speech_service_circuit_open": 1, "face_inference_errors": 2}
        out = augment_report_data_quality({}, curr, prev)
        dq = out["data_quality"]
        self.assertFalse(dq["complete"])
        self.assertIn("text_asr", dq["degraded_sources"])
        self.assertIn("face_inference", dq["degraded_sources"])
        self.assertGreater(dq["counters_window"]["text_analysis_errors"], 0)


if __name__ == "__main__":
    unittest.main()
