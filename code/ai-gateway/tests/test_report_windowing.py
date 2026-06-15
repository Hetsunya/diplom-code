"""Unit tests for report fusion windowing."""

from __future__ import annotations

import time
import unittest

from modules.report.stub_builder import build_stub_report
from modules.report.windowing import compute_fusion_meta


class TestComputeFusionMeta(unittest.TestCase):
    def test_trace_ids_by_participant(self) -> None:
        now = time.time()
        feats = [
            {"kind": "audio", "participant_id": "a", "trace_id": "t1", "ts": now, "data": {}},
            {"kind": "text", "participant_id": "a", "trace_id": "t1", "ts": now, "data": {"payload": {}}},
            {"kind": "face", "participant_id": "b", "trace_id": "t2", "ts": now, "data": {"face_features": {}}},
        ]
        m = compute_fusion_meta(feats, bucket_sec=3600.0)
        self.assertIn("a", m["trace_ids_by_participant"])
        self.assertIn("t1", m["trace_ids_by_participant"]["a"])
        self.assertEqual(len(m["buckets"]), 2)

    def test_bucket_sec_zero_skips_buckets(self) -> None:
        feats = [{"kind": "audio", "participant_id": "x", "trace_id": "z", "ts": 1.0, "data": {}}]
        m = compute_fusion_meta(feats, bucket_sec=0.0)
        self.assertEqual(m["buckets"], [])
        self.assertEqual(m["bucket_sec"], 0.0)


class TestBuildStubReportFusion(unittest.TestCase):
    def test_stub_includes_fusion(self) -> None:
        rep = build_stub_report(99, [], bucket_sec=10.0)
        self.assertIn("fusion", rep)
        self.assertEqual(rep["fusion"]["bucket_sec"], 10.0)

    def test_stub_includes_face_behavior_summary(self) -> None:
        now = time.time()
        rep = build_stub_report(
            99,
            [
                {
                    "kind": "face",
                    "participant_id": "p1",
                    "trace_id": "t1",
                    "ts": now,
                    "data": {
                        "face_behavior": {
                            "schema_version": "face_behavior.v1",
                            "provider": "deepface",
                            "face_count": 1,
                            "engagement_proxy": 0.76,
                            "quality": {"trackable": True, "confidence": 0.9},
                        }
                    },
                },
                {
                    "kind": "face",
                    "participant_id": "p1",
                    "trace_id": "t2",
                    "ts": now + 1.0,
                    "data": {
                        "face_behavior": {
                            "schema_version": "face_behavior.v1",
                            "provider": "deepface",
                            "face_count": 0,
                            "engagement_proxy": 0.11,
                            "quality": {"trackable": False, "guard_reason": "no_face"},
                        }
                    },
                },
            ],
            bucket_sec=10.0,
        )
        self.assertIn("face_behavior_summary", rep)
        fbs = rep["face_behavior_summary"]
        self.assertEqual(fbs["events"], 2)
        self.assertEqual(fbs["trackable_events"], 1)
        self.assertEqual(fbs["guard_reasons"].get("no_face"), 1)

    def test_stub_meeting_summary_when_face_emotions(self) -> None:
        now = time.time()
        rep = build_stub_report(
            42,
            [
                {
                    "kind": "face",
                    "participant_id": "alice",
                    "trace_id": "t1",
                    "ts": now,
                    "data": {
                        "face_features": {
                            "face_detected": True,
                            "dominant_emotion": "happy",
                            "confidence": 70.0,
                        }
                    },
                },
                {
                    "kind": "face",
                    "participant_id": "alice",
                    "trace_id": "t2",
                    "ts": now + 1,
                    "data": {
                        "face_features": {
                            "face_detected": True,
                            "dominant_emotion": "neutral",
                            "confidence": 55.0,
                        }
                    },
                },
                {
                    "kind": "text",
                    "participant_id": "alice",
                    "trace_id": "t3",
                    "ts": now + 2,
                    "data": {"payload": {"transcript_final": "Привет"}},
                },
            ],
            bucket_sec=30.0,
        )
        self.assertIn("meeting_summary", rep)
        ms = rep["meeting_summary"]
        self.assertEqual(ms["session_id"], 42)
        self.assertGreaterEqual(ms["participant_count"], 1)
        self.assertTrue(any(x.get("emotion") == "happy" for x in ms.get("emotion_distribution_top", [])))


if __name__ == "__main__":
    unittest.main()
