"""Unit tests for hybrid_contract validators (no ML / network)."""

from __future__ import annotations

import unittest

from hybrid_contract import HybridContractError, validate_audio_analysis, validate_face_analysis, validate_report_message, validate_text_analysis


class TestHybridContract(unittest.TestCase):
    def test_face_ok(self) -> None:
        validate_face_analysis(
            {
                "type": "face_analysis",
                "payload": {
                    "module": "face",
                    "version": "v1",
                    "stage": "partial",
                    "trace_id": "t1",
                    "face_features": {"dominant_emotion": "happy", "confidence": 80},
                },
            }
        )

    def test_face_ok_with_behavior(self) -> None:
        validate_face_analysis(
            {
                "type": "face_analysis",
                "payload": {
                    "module": "face",
                    "version": "v1",
                    "stage": "partial",
                    "trace_id": "t1b",
                    "face_features": {"dominant_emotion": "happy", "confidence": 80},
                    "face_behavior": {
                        "schema_version": "face_behavior.v1",
                        "provider": "mediapipe_face_landmarker",
                        "face_count": 1,
                        "blendshapes": {"smile": 0.8, "jaw_open": 0.2},
                        "quality": {"trackable": True, "confidence": 0.9},
                    },
                },
            }
        )

    def test_face_missing_envelope(self) -> None:
        with self.assertRaises(HybridContractError):
            validate_face_analysis({"type": "face_analysis", "payload": {"face_features": {}}})

    def test_face_behavior_invalid(self) -> None:
        with self.assertRaises(HybridContractError):
            validate_face_analysis(
                {
                    "type": "face_analysis",
                    "payload": {
                        "module": "face",
                        "version": "v1",
                        "stage": "partial",
                        "trace_id": "tb",
                        "face_features": {},
                        "face_behavior": {
                            "schema_version": "face_behavior.v1",
                            "provider": "x",
                            "face_count": 1,
                            "blendshapes": {"smile": 1.5},
                            "quality": {"trackable": True},
                        },
                    },
                }
            )

    def test_audio_ok(self) -> None:
        validate_audio_analysis(
            {
                "type": "audio_analysis",
                "payload": {
                    "module": "audio",
                    "version": "v1",
                    "stage": "partial",
                    "trace_id": "t2",
                    "audio_features": {"energy_rms_norm": 0.1},
                },
            }
        )

    def test_text_ok(self) -> None:
        validate_text_analysis(
            {
                "type": "text_analysis",
                "payload": {
                    "module": "text",
                    "version": "v1",
                    "stage": "partial",
                    "trace_id": "t3",
                    "transcript_partial": "hi",
                },
            }
        )

    def test_report_partial_ok(self) -> None:
        validate_report_message(
            {
                "type": "analysis_report_partial",
                "payload": {
                    "module": "report",
                    "version": "rv1",
                    "stage": "partial",
                    "trace_id": "t4",
                    "report": {"summary": "x"},
                    "report_source": "local_stub",
                    "model_version": "rv1",
                    "generated_at": "2026-01-01T00:00:00Z",
                    "config_snapshot": {},
                },
            },
            expect_final=False,
        )

    def test_report_final_stage_mismatch(self) -> None:
        with self.assertRaises(HybridContractError):
            validate_report_message(
                {
                    "type": "analysis_report",
                    "payload": {
                        "module": "report",
                        "version": "rv1",
                        "stage": "partial",
                        "trace_id": "t5",
                        "report": {},
                        "report_source": "local_stub",
                        "model_version": "rv1",
                        "generated_at": "2026-01-01T00:00:00Z",
                        "config_snapshot": {},
                    },
                },
                expect_final=True,
            )


if __name__ == "__main__":
    unittest.main()
