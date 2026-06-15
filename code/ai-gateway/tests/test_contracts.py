from __future__ import annotations

import unittest

from contracts import has_required_envelope_fields, is_valid_face_behavior_v1


class TestContracts(unittest.TestCase):
    def test_face_behavior_valid(self) -> None:
        payload = {
            "module": "face",
            "version": "v1",
            "stage": "partial",
            "trace_id": "t1",
            "face_behavior": {
                "schema_version": "face_behavior.v1",
                "provider": "mediapipe_face_landmarker",
                "face_count": 1,
                "blendshapes": {"smile": 0.8, "jaw_open": 0.2},
                "head_pose": {"yaw_deg": 1.2, "pitch_deg": -2.4, "roll_deg": 0.4},
                "eye_state": {
                    "left_closed_prob": 0.05,
                    "right_closed_prob": 0.06,
                    "blink_detected": False,
                },
                "engagement_proxy": 0.77,
                "quality": {"trackable": True, "confidence": 0.88},
            },
        }
        self.assertTrue(has_required_envelope_fields(payload))
        self.assertTrue(is_valid_face_behavior_v1(payload["face_behavior"]))

    def test_face_behavior_invalid_quality(self) -> None:
        bad = {
            "schema_version": "face_behavior.v1",
            "provider": "mediapipe_face_landmarker",
            "face_count": 1,
            "quality": {"trackable": "yes"},
        }
        self.assertFalse(is_valid_face_behavior_v1(bad))

    def test_face_payload_rejects_invalid_behavior(self) -> None:
        payload = {
            "module": "face",
            "version": "v1",
            "stage": "partial",
            "trace_id": "t1",
            "face_behavior": {
                "schema_version": "face_behavior.v1",
                "provider": "mediapipe_face_landmarker",
                "face_count": 1,
                "blendshapes": {"smile": 1.5},
                "quality": {"trackable": True},
            },
        }
        self.assertFalse(has_required_envelope_fields(payload))


if __name__ == "__main__":
    unittest.main()

