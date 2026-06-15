"""Attach `data_quality` hints to stub / merged reports (prod degradation visibility)."""

from __future__ import annotations

from typing import Any


def augment_report_data_quality(
    report_body: dict[str, Any],
    counters_curr: dict[str, int],
    counters_prev: dict[str, int] | None,
) -> dict[str, Any]:
    """
    Compare ai-gateway counters since last report tick.

    `counters_prev` None treated as equal to `counters_curr` (first tick → zero deltas).
    """
    out = dict(report_body)
    prev = counters_prev if counters_prev is not None else counters_curr

    def delta(key: str) -> int:
        return max(0, counters_curr.get(key, 0) - prev.get(key, 0))

    degraded: list[str] = []
    notes: list[str] = []

    if delta("text_analysis_errors") > 0:
        degraded.append("text_asr")
        notes.append("text_analysis_errors_since_last_report")
    if delta("speech_service_circuit_open") > 0:
        degraded.append("text_asr")
        notes.append("speech_service_circuit_open_since_last_report")

    if delta("face_inference_errors") > 0:
        degraded.append("face_inference")
        notes.append("face_inference_errors_since_last_report")

    if delta("audio_features_degraded") > 0:
        notes.append("audio_features_degraded_since_last_report")

    if delta("report_partial_errors") > 0 or delta("report_final_errors") > 0:
        notes.append("report_emit_errors_since_last_report")

    window_keys = (
        "text_analysis_errors",
        "speech_service_circuit_open",
        "face_inference_errors",
        "audio_features_degraded",
        "report_partial_errors",
        "report_final_errors",
    )

    out["data_quality"] = {
        "complete": len(degraded) == 0,
        "degraded_sources": sorted(set(degraded)),
        "notes": notes,
        "counters_window": {k: delta(k) for k in window_keys},
    }
    return out
