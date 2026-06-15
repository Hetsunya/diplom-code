"""DeepFace output normalization and face_features payloads (no OpenCV import)."""

from __future__ import annotations

import math
from typing import Any


def _deg(rad: float) -> float:
    return float(rad) * 180.0 / math.pi


def _euler_from_matrix4x4_row_major(m16: list[float]) -> dict[str, float] | None:
    """
    Convert 4x4 row-major transform matrix to Euler angles (deg).

    We expose a pragmatic head pose estimate for UI/reporting. Convention:
    - yaw: left/right (around Y)
    - pitch: up/down (around X)
    - roll: tilt (around Z)
    """
    if len(m16) != 16:
        return None
    r00, r01, r02 = m16[0], m16[1], m16[2]
    r10, r11, r12 = m16[4], m16[5], m16[6]
    r20, r21, r22 = m16[8], m16[9], m16[10]

    sy = math.sqrt((r00 * r00) + (r10 * r10))
    singular = sy < 1e-6
    if not singular:
        pitch = math.atan2(r21, r22)
        yaw = math.atan2(-r20, sy)
        roll = math.atan2(r10, r00)
    else:
        pitch = math.atan2(-r12, r11)
        yaw = math.atan2(-r20, sy)
        roll = 0.0

    return {"yaw_deg": _deg(yaw), "pitch_deg": _deg(pitch), "roll_deg": _deg(roll)}


def build_face_behavior_v1_mediapipe(
    *,
    schema_version: str,
    confidence: float,
    blendshapes: dict[str, float],
    transform_matrix16: list[float] | None,
    face_detected: bool,
    guard_reason: str | None,
    frame_laplacian_var: float | None = None,
    min_face_side_px: int | None = None,
) -> dict[str, Any]:
    """
    Build `face_behavior` from MediaPipe Face Landmarker outputs.
    """
    # Canonical v1 subset (if missing, omit).
    def pick(*names: str) -> float | None:
        for n in names:
            v = blendshapes.get(n)
            if isinstance(v, (int, float)):
                return _clamp01(float(v))
        return None

    out_blend: dict[str, float] = {}
    for k, v in (
        ("smile", pick("smile", "mouthSmileLeft", "mouthSmileRight")),
        ("jaw_open", pick("jawOpen")),
        ("eye_closed_left", pick("eyeBlinkLeft", "eyeClosedLeft")),
        ("eye_closed_right", pick("eyeBlinkRight", "eyeClosedRight")),
        ("brow_inner_up", pick("browInnerUp")),
        ("mouth_pucker", pick("mouthPucker")),
    ):
        if v is not None:
            out_blend[k] = float(v)

    head_pose = None
    if transform_matrix16 is not None and len(transform_matrix16) == 16:
        angles = _euler_from_matrix4x4_row_major(transform_matrix16)
        if angles is not None:
            head_pose = {**angles, "transform_matrix": [float(x) for x in transform_matrix16]}

    left_closed = out_blend.get("eye_closed_left")
    right_closed = out_blend.get("eye_closed_right")
    eye_state = None
    if left_closed is not None or right_closed is not None:
        eye_state = {
            "left_closed_prob": float(left_closed or 0.0),
            "right_closed_prob": float(right_closed or 0.0),
            "blink_detected": bool((left_closed or 0.0) > 0.6 or (right_closed or 0.0) > 0.6),
        }

    engagement_proxy = None
    if out_blend:
        # simple proxy: smile boosts, high eye-closed reduces, jaw-open mild boosts
        smile = out_blend.get("smile", 0.0)
        jaw = out_blend.get("jaw_open", 0.0)
        eye = max(out_blend.get("eye_closed_left", 0.0), out_blend.get("eye_closed_right", 0.0))
        engagement_proxy = _clamp01((smile * 0.65) + (jaw * 0.15) - (eye * 0.35) + 0.25)

    trackable = bool(face_detected) and guard_reason is None
    quality: dict[str, Any] = {
        "trackable": trackable,
        "confidence": float(confidence),
    }
    if guard_reason:
        quality["guard_reason"] = guard_reason
    if frame_laplacian_var is not None:
        quality["frame_laplacian_var"] = float(frame_laplacian_var)
    if min_face_side_px is not None:
        quality["min_face_side_px"] = int(min_face_side_px)

    out: dict[str, Any] = {
        "schema_version": schema_version,
        "provider": "mediapipe_face_landmarker",
        "face_count": 1 if face_detected else 0,
        "quality": quality,
    }
    if out_blend:
        out["blendshapes"] = out_blend
    if head_pose is not None:
        out["head_pose"] = head_pose
    if eye_state is not None:
        out["eye_state"] = eye_state
    if engagement_proxy is not None:
        out["engagement_proxy"] = float(engagement_proxy)
    return out


def _coerce_float(v: Any) -> float | None:
    """DeepFace/TensorFlow often returns numpy scalars; `isinstance(x, float)` is False for those."""
    if v is None or isinstance(v, bool):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(x):
        return None
    return x


def _sanitize_emotion_probs(probs: dict[Any, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in probs.items():
        key = k if isinstance(k, str) else str(k)
        fv = _coerce_float(v)
        if fv is not None:
            out[key] = fv
    return out


def is_no_face_deepface_error(exc: BaseException) -> bool:
    s = str(exc).lower()
    needles = (
        "face could not be detected",
        "detected face is too small",
        "there is no face",
        "no face detected",
    )
    return any(n in s for n in needles)


def normalize_deepface_result(result: Any) -> dict[str, Any] | None:
    """Pick first face dict from DeepFace `analyze` return value."""
    if isinstance(result, dict):
        obj = result
    elif isinstance(result, list) and result:
        first = result[0]
        if not isinstance(first, dict):
            return None
        obj = first
    else:
        return None

    dominant_raw = obj.get("dominant_emotion")
    probs_raw = obj.get("emotion")
    if not isinstance(probs_raw, dict):
        return None
    dominant = dominant_raw if isinstance(dominant_raw, str) else None
    if dominant is None and dominant_raw is not None:
        dominant = str(dominant_raw).strip() or None
    if not dominant:
        return None

    probs = _sanitize_emotion_probs(probs_raw)
    confidence_val = probs.get(dominant)
    if confidence_val is None:
        confidence_val = 0.0

    region = obj.get("region")
    region_w = region_h = region_x = region_y = None
    if isinstance(region, dict):
        rw = _coerce_float(region.get("w"))
        rh = _coerce_float(region.get("h"))
        if rw is not None and rh is not None:
            region_w, region_h = int(round(rw)), int(round(rh))
        rx = _coerce_float(region.get("x", region.get("left")))
        ry = _coerce_float(region.get("y", region.get("top")))
        if rx is not None and ry is not None:
            region_x, region_y = int(round(rx)), int(round(ry))

    return {
        "dominant_emotion": dominant,
        "probs": probs,
        "confidence": float(confidence_val),
        "region_w": region_w,
        "region_h": region_h,
        "region_x": region_x,
        "region_y": region_y,
    }


def build_face_features_positive(
    *,
    dominant: str,
    probs: dict[str, Any],
    confidence: float,
    region_w: int | None,
    region_h: int | None,
    min_face_side_px: int,
) -> dict[str, Any] | None:
    """
    Build `face_features` for a confident detection.

    Returns None if region is present and too small (noisy partial detections).
    """
    if min_face_side_px > 0 and region_w is not None and region_h is not None:
        if min(region_w, region_h) < min_face_side_px:
            return None

    return {
        "dominant_emotion": dominant,
        "probs": probs,
        "face_detected": True,
        "confidence": confidence,
    }


def build_face_features_guard(*, reason: str) -> dict[str, Any]:
    """Structured payload when we intentionally emit a negative / guard outcome."""
    return {
        "face_detected": False,
        "dominant_emotion": None,
        "probs": {},
        "confidence": 0.0,
        "guard_reason": reason,
    }


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def build_face_behavior_v1(
    *,
    provider: str,
    schema_version: str,
    confidence: float,
    probs: dict[str, Any],
    face_detected: bool,
    guard_reason: str | None,
    frame_laplacian_var: float | None = None,
    min_face_side_px: int | None = None,
) -> dict[str, Any]:
    """
    Build a minimal behavior payload compatible with docs/ANALYSIS_WS_CONTRACTS.md.

    We intentionally keep this model-agnostic: DeepFace currently gives emotion probabilities,
    so v1 behavior proxies are derived from those scores and quality gates.
    """
    happy = _clamp01(float(probs.get("happy", 0.0)) / 100.0 if probs else 0.0)
    surprise = _clamp01(float(probs.get("surprise", 0.0)) / 100.0 if probs else 0.0)
    neutral = _clamp01(float(probs.get("neutral", 0.0)) / 100.0 if probs else 0.0)
    sad = _clamp01(float(probs.get("sad", 0.0)) / 100.0 if probs else 0.0)
    fear = _clamp01(float(probs.get("fear", 0.0)) / 100.0 if probs else 0.0)
    angry = _clamp01(float(probs.get("angry", 0.0)) / 100.0 if probs else 0.0)

    engagement_proxy = _clamp01((happy * 0.55) + (surprise * 0.15) + (neutral * 0.2) - (sad * 0.05) - (fear * 0.025) - (angry * 0.025))
    trackable = bool(face_detected) and guard_reason is None

    quality: dict[str, Any] = {
        "trackable": trackable,
        "confidence": float(confidence),
    }
    if guard_reason:
        quality["guard_reason"] = guard_reason
    if frame_laplacian_var is not None:
        quality["frame_laplacian_var"] = float(frame_laplacian_var)
    if min_face_side_px is not None:
        quality["min_face_side_px"] = int(min_face_side_px)

    return {
        "schema_version": schema_version,
        "provider": provider,
        "face_count": 1 if face_detected else 0,
        "blendshapes": {
            "smile": happy,
            "jaw_open": surprise,
            "eye_closed_left": 1.0 - neutral,
            "eye_closed_right": 1.0 - neutral,
        },
        "engagement_proxy": engagement_proxy,
        "quality": quality,
    }
