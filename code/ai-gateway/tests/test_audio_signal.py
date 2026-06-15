"""Unit tests for baseline audio signal extraction."""

from __future__ import annotations

import base64
import unittest

from modules.audio.signal import extract_audio_features, extract_audio_features_safe


class TestAudioSignal(unittest.TestCase):
    def test_s16_sine_energy_and_safe_fallback(self) -> None:
        import numpy as np

        sine = (np.sin(np.linspace(0, 8 * np.pi, 1600)) * 16000).astype("<i2").tobytes()
        payload = {"chunk_base64": base64.b64encode(sine).decode("ascii"), "timeslice_ms": 1000}
        out = extract_audio_features(payload, {})
        self.assertGreater(out["energy_rms_norm"], 0.01)
        self.assertGreater(out["pcm_samples_used"], 0)
        self.assertTrue(out["pcm_s16_like"])

        bad = extract_audio_features_safe({}, {})
        self.assertFalse(bad.get("degraded"))

    def test_pause_and_jitter_from_timing(self) -> None:
        payload: dict = {"timeslice_ms": 1000}
        p = {"pause_threshold_ms": 500}
        o1 = extract_audio_features(payload, p, inter_arrival_ms=3000.0, iat_history_ms=[1000.0, 3000.0, 1000.0])
        self.assertGreater(o1["pause_ratio"], 0.0)
        self.assertGreater(o1["timing_jitter_ms"], 0.0)

    def test_safe_on_invalid_numpy_path(self) -> None:
        class BoomPayload(dict):
            def get(self, key, default=None):  # type: ignore[override]
                if key == "timeslice_ms":
                    raise RuntimeError("boom")
                return super().get(key, default)

        out = extract_audio_features_safe(BoomPayload())
        self.assertTrue(out.get("degraded"))


if __name__ == "__main__":
    unittest.main()
