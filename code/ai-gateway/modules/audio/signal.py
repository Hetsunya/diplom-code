"""Audio chunk descriptors: size/bitrate proxies + lightweight PCM-like stats on raw bytes."""

from __future__ import annotations

import base64
from typing import Any

import numpy as np


def _decode_b64_chunk(payload: dict[str, Any]) -> bytes:
    b64_raw = payload.get("chunk_base64") or payload.get("data_base64") or payload.get("base64")
    if not isinstance(b64_raw, str) or not b64_raw.strip():
        return b""
    try:
        return base64.b64decode(b64_raw, validate=False)
    except Exception:
        return b""


def _s16le_window_stats(buf: bytes, max_samples: int) -> dict[str, Any]:
    if len(buf) < 4:
        return {
            "energy_rms_norm": 0.0,
            "zero_crossing_rate": 0.0,
            "pcm_samples_used": 0,
            "pcm_s16_like": False,
        }
    n_bytes = min(len(buf), max(4, max_samples * 2))
    n_bytes -= n_bytes % 2
    raw = np.frombuffer(memoryview(buf)[:n_bytes], dtype="<i2")
    if raw.size == 0:
        return {
            "energy_rms_norm": 0.0,
            "zero_crossing_rate": 0.0,
            "pcm_samples_used": 0,
            "pcm_s16_like": False,
        }
    x = raw.astype(np.float64)
    rms = float(np.sqrt(np.mean(x * x)))
    energy_rms_norm = min(1.0, rms / 32768.0)
    signs = np.sign(x)
    changes = int(np.sum(np.abs(np.diff(signs)) > 0))
    zcr = float(changes) / float(max(1, raw.size - 1))
    return {
        "energy_rms_norm": round(energy_rms_norm, 4),
        "zero_crossing_rate": round(zcr, 4),
        "pcm_samples_used": int(raw.size),
        "pcm_s16_like": True,
    }


def extract_audio_features(
    payload: dict[str, Any],
    params: dict[str, Any] | None = None,
    *,
    inter_arrival_ms: float | None = None,
    duration_ms_override: float | None = None,
    rms_history_for_shimmer: list[float] | None = None,
    iat_history_ms: list[float] | None = None,
) -> dict[str, Any]:
    """
    Proxy metrics from chunk metadata/size + int16-le heuristic on decoded bytes
    (WebM/Opus containers are not decoded; stats are best-effort).
    """
    params = params or {}
    min_chunk_bytes = int(params.get("min_chunk_bytes", 400))
    max_rms_samples = int(params.get("max_rms_samples", 8000))
    pause_threshold_ms = float(params.get("pause_threshold_ms", 2000))

    raw_bytes = _decode_b64_chunk(payload)
    chunk_size_bytes = len(raw_bytes)

    if duration_ms_override is not None and duration_ms_override > 0:
        duration_ms = float(duration_ms_override)
    else:
        timeslice_ms_raw = payload.get("timeslice_ms")
        if isinstance(timeslice_ms_raw, (int, float)) and timeslice_ms_raw > 0:
            duration_ms = float(timeslice_ms_raw)
        else:
            duration_ms = 3500.0

    bitrate_kbps_est = 0.0
    if duration_ms > 0:
        bitrate_kbps_est = round((chunk_size_bytes * 8.0) / duration_ms, 2)

    speech_proxy = min(1.0, round(chunk_size_bytes / 12000.0, 3))
    if chunk_size_bytes < min_chunk_bytes:
        speech_proxy = 0.0

    pcm_stats = _s16le_window_stats(raw_bytes, max_rms_samples)

    pause_ratio = 0.0
    if inter_arrival_ms is not None and inter_arrival_ms > pause_threshold_ms:
        pause_ratio = min(1.0, inter_arrival_ms / (inter_arrival_ms + max(duration_ms, 1.0)))

    chunk_interval_ms = round(inter_arrival_ms, 2) if inter_arrival_ms is not None else None
    activity_ppm: float | None = None
    if inter_arrival_ms is not None and inter_arrival_ms > 0:
        activity_ppm = round(60000.0 / inter_arrival_ms, 2)

    timing_jitter_ms = 0.0
    if iat_history_ms is not None and len(iat_history_ms) >= 2:
        arr = np.asarray(iat_history_ms, dtype=np.float64)
        timing_jitter_ms = round(float(np.std(arr)), 2)

    shimmer_proxy = 0.0
    if rms_history_for_shimmer is not None and len(rms_history_for_shimmer) >= 2:
        arr = np.asarray(rms_history_for_shimmer, dtype=np.float64)
        m = float(np.mean(arr))
        shimmer_proxy = round(float(np.std(arr)) / (m + 1e-6), 4)

    final_chunk = bool(payload.get("final_chunk") or payload.get("is_final"))
    mime = payload.get("mime")

    return {
        "chunk_size_bytes": chunk_size_bytes,
        "duration_ms": duration_ms,
        "bitrate_kbps_est": bitrate_kbps_est,
        "speech_activity_proxy": speech_proxy,
        "energy_rms_norm": pcm_stats["energy_rms_norm"],
        "zero_crossing_rate": pcm_stats["zero_crossing_rate"],
        "pcm_samples_used": pcm_stats["pcm_samples_used"],
        "pcm_s16_like": pcm_stats["pcm_s16_like"],
        "pause_ratio": round(pause_ratio, 4),
        "chunk_interval_ms": chunk_interval_ms,
        "activity_pulses_per_min": activity_ppm,
        "timing_jitter_ms": timing_jitter_ms,
        "shimmer_proxy": shimmer_proxy,
        "final_chunk": final_chunk,
        "mime": str(mime) if isinstance(mime, str) else "audio/webm",
        "note": "baseline-v3; int16-heuristic on raw chunk bytes; container codecs not demuxed",
    }


def extract_audio_features_safe(
    payload: dict[str, Any],
    params: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        return extract_audio_features(payload, params, **kwargs)
    except Exception:
        try:
            ts = payload.get("timeslice_ms")
        except Exception:
            ts = None
        duration_ms = float(ts) if isinstance(ts, (int, float)) and ts and float(ts) > 0 else 3500.0
        return {
            "chunk_size_bytes": 0,
            "duration_ms": duration_ms,
            "bitrate_kbps_est": 0.0,
            "speech_activity_proxy": 0.0,
            "energy_rms_norm": 0.0,
            "zero_crossing_rate": 0.0,
            "pcm_samples_used": 0,
            "pcm_s16_like": False,
            "pause_ratio": 0.0,
            "chunk_interval_ms": None,
            "activity_pulses_per_min": None,
            "timing_jitter_ms": 0.0,
            "shimmer_proxy": 0.0,
            "final_chunk": bool(payload.get("final_chunk") or payload.get("is_final")),
            "mime": "audio/webm",
            "note": "degraded: extraction failed",
            "degraded": True,
        }
