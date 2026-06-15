"""v1 analysis envelope helpers (see docs/ANALYSIS_WS_CONTRACTS.md)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

ModuleName = Literal["text", "audio", "face", "report"]
StageName = Literal["partial", "final"]


def build_trace_id() -> str:
    return str(uuid.uuid4())


def analysis_envelope(
    *,
    module: ModuleName,
    version: str,
    stage: StageName,
    trace_id: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "module": module,
        "version": version,
        "stage": stage,
        "trace_id": trace_id,
    }
    if extra:
        out.update(extra)
    return out


def has_required_envelope_fields(payload: dict[str, Any]) -> bool:
    """Validate required v1 analysis envelope fields inside payload."""
    required = ("module", "version", "stage", "trace_id")
    for key in required:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            return False
    if payload.get("module") == "face" and "face_behavior" in payload:
        face_behavior = payload.get("face_behavior")
        if not is_valid_face_behavior_v1(face_behavior):
            return False
    return True


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _num_0_1(v: Any) -> bool:
    if not _is_number(v):
        return False
    return 0.0 <= float(v) <= 1.0


def is_valid_face_behavior_v1(face_behavior: Any) -> bool:
    """Validate optional `face_behavior` extension for `face_analysis` payload."""
    if not isinstance(face_behavior, dict):
        return False
    schema_version = face_behavior.get("schema_version")
    provider = face_behavior.get("provider")
    face_count = face_behavior.get("face_count")
    quality = face_behavior.get("quality")
    if not isinstance(schema_version, str) or not schema_version.strip():
        return False
    if not isinstance(provider, str) or not provider.strip():
        return False
    if not _is_number(face_count) or float(face_count) < 0:
        return False
    if not isinstance(quality, dict):
        return False
    if not isinstance(quality.get("trackable"), bool):
        return False

    guard_reason = quality.get("guard_reason")
    if guard_reason is not None and not isinstance(guard_reason, str):
        return False
    for key in ("frame_laplacian_var", "min_face_side_px", "confidence"):
        value = quality.get(key)
        if value is not None and not _is_number(value):
            return False

    blendshapes = face_behavior.get("blendshapes")
    if blendshapes is not None:
        if not isinstance(blendshapes, dict):
            return False
        for k, v in blendshapes.items():
            if not isinstance(k, str) or not _num_0_1(v):
                return False

    head_pose = face_behavior.get("head_pose")
    if head_pose is not None:
        if not isinstance(head_pose, dict):
            return False
        for key in ("yaw_deg", "pitch_deg", "roll_deg"):
            val = head_pose.get(key)
            if val is not None and not _is_number(val):
                return False
        transform = head_pose.get("transform_matrix")
        if transform is not None:
            if not isinstance(transform, list) or len(transform) != 16:
                return False
            if any(not _is_number(x) for x in transform):
                return False

    eye_state = face_behavior.get("eye_state")
    if eye_state is not None:
        if not isinstance(eye_state, dict):
            return False
        for key in ("left_closed_prob", "right_closed_prob"):
            val = eye_state.get(key)
            if val is not None and not _num_0_1(val):
                return False
        blink = eye_state.get("blink_detected")
        if blink is not None and not isinstance(blink, bool):
            return False

    engagement_proxy = face_behavior.get("engagement_proxy")
    if engagement_proxy is not None and not _num_0_1(engagement_proxy):
        return False

    return True
