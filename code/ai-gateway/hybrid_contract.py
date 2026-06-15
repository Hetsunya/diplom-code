"""Validate WS analytics payloads (docs/ANALYSIS_WS_CONTRACTS.md) for hybrid smoke / CI helpers."""

from __future__ import annotations

from typing import Any

from contracts import is_valid_face_behavior_v1


class HybridContractError(Exception):
    pass


def _req_keys(obj: Any, keys: tuple[str, ...], *, ctx: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise HybridContractError(f"{ctx}: expected object, got {type(obj).__name__}")
    for k in keys:
        if k not in obj:
            raise HybridContractError(f"{ctx}: missing {k!r}")
        v = obj[k]
        if k in ("module", "version", "stage", "trace_id") and (not isinstance(v, str) or not str(v).strip()):
            raise HybridContractError(f"{ctx}: invalid empty {k!r}")
    return obj


def validate_face_analysis(msg: dict[str, Any]) -> None:
    p = _req_keys(msg.get("payload"), ("module", "version", "stage", "trace_id", "face_features"), ctx="face_analysis.payload")
    ff = p.get("face_features")
    if not isinstance(ff, dict):
        raise HybridContractError("face_analysis.face_features must be object")
    fb = p.get("face_behavior")
    if fb is not None and not is_valid_face_behavior_v1(fb):
        raise HybridContractError("face_analysis.face_behavior is invalid for face_behavior.v1")


def validate_audio_analysis(msg: dict[str, Any]) -> None:
    p = _req_keys(msg.get("payload"), ("module", "version", "stage", "trace_id", "audio_features"), ctx="audio_analysis.payload")
    af = p.get("audio_features")
    if not isinstance(af, dict):
        raise HybridContractError("audio_analysis.audio_features must be object")


def validate_text_analysis(msg: dict[str, Any]) -> None:
    _req_keys(msg.get("payload"), ("module", "version", "stage", "trace_id"), ctx="text_analysis.payload")


def validate_report_message(msg: dict[str, Any], *, expect_final: bool) -> None:
    typ = msg.get("type")
    want_type = "analysis_report" if expect_final else "analysis_report_partial"
    if typ != want_type:
        raise HybridContractError(f"report type: want {want_type!r}, got {typ!r}")
    p = _req_keys(
        msg.get("payload"),
        ("module", "version", "stage", "trace_id", "report", "report_source", "model_version", "generated_at", "config_snapshot"),
        ctx=f"{typ}.payload",
    )
    if not isinstance(p.get("report"), dict):
        raise HybridContractError(f"{typ}: report must be object")
    stage = p.get("stage")
    if expect_final:
        if stage != "final":
            raise HybridContractError(f"{typ}: envelope stage must be 'final', got {stage!r}")
    else:
        if stage != "partial":
            raise HybridContractError(f"{typ}: envelope stage must be 'partial', got {stage!r}")
