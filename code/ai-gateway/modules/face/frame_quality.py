"""OpenCV-based frame sharpness (optional dependency for runtime face plugin)."""

from __future__ import annotations

import cv2
import numpy as np


def laplacian_variance_bgr(img_bgr: np.ndarray) -> float:
    """Higher variance ≈ sharper frame; uniform / blank frames are near 0."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def should_skip_blurry_frame(img_bgr: np.ndarray, min_laplacian_var: float) -> bool:
    if min_laplacian_var <= 0.0:
        return False
    return laplacian_variance_bgr(img_bgr) < min_laplacian_var
