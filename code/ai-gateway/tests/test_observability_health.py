from __future__ import annotations

import unittest

from observability import incr, observe_module_latency, snapshot_health


class TestObservabilityHealth(unittest.TestCase):
    def test_snapshot_health_latency_ring(self) -> None:
        incr("audio_analysis_sent")
        observe_module_latency("audio", 10.0)
        observe_module_latency("audio", 20.0)
        h = snapshot_health()
        self.assertIn("audio_analysis_sent", h["counters"])
        self.assertIn("audio", h["latency_ms"])
        self.assertGreater(h["latency_ms"]["audio"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
