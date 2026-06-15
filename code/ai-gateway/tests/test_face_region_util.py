"""Tests for bbox clamp + EMA used by face debug overlay."""

from __future__ import annotations

import unittest

from modules.face.region_util import clamp_face_region, ema_bbox


class TestClampFaceRegion(unittest.TestCase):
    def test_valid(self) -> None:
        r = clamp_face_region(10, 20, 80, 100, 640, 480, max_area_frac=0.5)
        assert r is not None
        self.assertTupleEqual(r, (10, 20, 80, 100))

    def test_rejects_near_full_frame(self) -> None:
        r = clamp_face_region(0, 0, 600, 450, 640, 480, max_area_frac=0.42)
        self.assertIsNone(r)

    def test_clips_negative_origin(self) -> None:
        r = clamp_face_region(-10, -20, 200, 240, 640, 480, max_area_frac=0.6)
        assert r is not None
        self.assertGreaterEqual(r[0], 0)
        self.assertGreaterEqual(r[1], 0)
        self.assertLessEqual(r[0] + r[2], 640)
        self.assertLessEqual(r[1] + r[3], 480)


class TestEmaBBox(unittest.TestCase):
    def test_none_prev(self) -> None:
        self.assertTupleEqual(
            ema_bbox(None, (1, 2, 30, 40), 0.5),
            (1, 2, 30, 40),
        )

    def test_blends(self) -> None:
        p = (0, 0, 10, 10)
        c = (10, 10, 20, 20)
        out = ema_bbox(p, c, 0.5)
        self.assertEqual(out, (5, 5, 15, 15))


if __name__ == "__main__":
    unittest.main()
