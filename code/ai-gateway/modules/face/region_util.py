"""Clamp + sanity checks for face bounding boxes (DeepFace region)."""

from __future__ import annotations


def clamp_face_region(
    x: int,
    y: int,
    w: int,
    h: int,
    frame_w: int,
    frame_h: int,
    *,
    max_area_frac: float,
    min_side_px: int = 8,
) -> tuple[int, int, int, int] | None:
    """
    Intersect with frame, drop degenerate / full-frame false positives.

    OpenCV Haar sometimes returns boxes that cover most of the image; those are rejected when
    area > max_area_frac * frame area.
    """
    if frame_w <= 0 or frame_h <= 0 or w <= 0 or h <= 0:
        return None
    max_af = max(0.05, min(0.95, float(max_area_frac)))

    x0 = min(max(0, x), frame_w - 1)
    y0 = min(max(0, y), frame_h - 1)
    w0 = min(w, frame_w - x0)
    h0 = min(h, frame_h - y0)
    if w0 < min_side_px or h0 < min_side_px:
        return None
    if w0 * h0 > max_af * frame_w * frame_h:
        return None
    return x0, y0, w0, h0


def ema_bbox(
    prev: tuple[int, int, int, int] | None,
    cur: tuple[int, int, int, int],
    alpha: float,
) -> tuple[int, int, int, int]:
    """Exponential moving average over x, y, w, h."""
    if prev is None or alpha <= 0:
        return cur
    a = min(max(float(alpha), 0.0), 1.0)
    out: list[int] = []
    for p, c in zip(prev, cur):
        out.append(int(round(a * c + (1.0 - a) * p)))
    return out[0], out[1], out[2], out[3]
