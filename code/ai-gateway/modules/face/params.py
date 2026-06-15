"""Typed defaults for `modules.face.params` (see modules.default.json)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FaceRuntimeParams:
    min_interval_sec: float
    min_confidence: float
    enforce_detection: bool
    detector_backend: str
    align: bool
    min_laplacian_var: float
    min_face_side_px: int
    emit_no_face_face_analysis: bool
    max_concurrent_inferences: int
    emit_debug_face: bool
    log_face_inference: bool
    debug_bbox_smooth_alpha: float
    debug_max_face_area_frac: float
    emit_face_behavior: bool
    face_behavior_schema_version: str
    mediapipe_enabled: bool
    mediapipe_model_path: str
    mediapipe_model_url: str
    mediapipe_max_landmarks: int

    @staticmethod
    def from_dict(p: dict[str, Any]) -> FaceRuntimeParams:
        return FaceRuntimeParams(
            min_interval_sec=float(p.get("min_interval_sec", 0.2)),
            min_confidence=float(p.get("min_confidence", 0.0)),
            enforce_detection=bool(p.get("enforce_detection", False)),
            detector_backend=str(p.get("detector_backend", "opencv") or "opencv"),
            align=bool(p.get("align", False)),
            min_laplacian_var=float(p.get("min_laplacian_var", 0.0)),
            min_face_side_px=int(p.get("min_face_side_px", 0)),
            emit_no_face_face_analysis=bool(p.get("emit_no_face_face_analysis", False)),
            max_concurrent_inferences=max(1, int(p.get("max_concurrent_inferences", 2))),
            emit_debug_face=bool(p.get("emit_debug_face", False)),
            log_face_inference=bool(p.get("log_face_inference", False)),
            debug_bbox_smooth_alpha=float(p.get("debug_bbox_smooth_alpha", 0.35)),
            debug_max_face_area_frac=float(p.get("debug_max_face_area_frac", 0.45)),
            emit_face_behavior=bool(p.get("emit_face_behavior", False)),
            face_behavior_schema_version=str(p.get("face_behavior_schema_version", "face_behavior.v1")),
            mediapipe_enabled=bool(p.get("mediapipe_enabled", False)),
            mediapipe_model_path=str(p.get("mediapipe_model_path", "") or ""),
            mediapipe_model_url=str(p.get("mediapipe_model_url", "") or ""),
            mediapipe_max_landmarks=max(0, int(p.get("mediapipe_max_landmarks", 120))),
        )
