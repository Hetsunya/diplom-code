"""Optional faster-whisper backend for speech-service.

Live ASR from ai-gateway sends **growing** WebM chunks (re-decode full buffer each tick).
For that pattern, OpenAI recommends turning off ``condition_on_previous_text`` to avoid
feedback loops / repeated phrases, and using VAD to strip silence (fewer "phantom" words).

See also: https://github.com/davabase/whisper_real_time (cumulative buffer idea).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

_model_cache: dict[str, Any] = {}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    v = str(raw).strip().lower()
    if v in ("0", "false", "no", "off", "n"):
        return False
    if v in ("1", "true", "yes", "on", "y"):
        return True
    return default


def _env_float_optional(name: str) -> float | None:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return None
    try:
        return float(str(raw).strip())
    except ValueError:
        return None


def _effective_asr_language(explicit: str | None) -> str | None:
    """
    ISO 639-1 code passed to faster-whisper, or None for auto-detect.
    Default is Russian (diploma UI); set WHISPER_LANGUAGE=auto to restore detection.
    """
    if explicit and str(explicit).strip():
        v = str(explicit).strip().lower()
        if v in ("auto", "detect", "none"):
            return None
        return v
    raw = os.getenv("WHISPER_LANGUAGE")
    if raw is None or not str(raw).strip():
        return "ru"
    v = str(raw).strip().lower()
    if v in ("auto", "detect", "none"):
        return None
    return v


def _get_model(model_size: str):
    """Lazy singleton per model size."""
    from faster_whisper import WhisperModel

    global _model_cache
    if model_size not in _model_cache:
        device = os.getenv("WHISPER_DEVICE", "cpu")
        ctype = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        _model_cache[model_size] = WhisperModel(model_size, device=device, compute_type=ctype)
    return _model_cache[model_size]


def transcribe_media_bytes(data: bytes, suffix: str, *, language: str | None) -> tuple[str, dict[str, Any]]:
    """
    Write bytes to a temp file and run Whisper. suffix should match mime (.webm, .wav, …).
    Returns (text, info dict for text_features).
    """
    model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
    model = _get_model(model_size)

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = Path(tmp.name)
    try:
        tmp.write(data)
        tmp.close()

        kwargs: dict[str, Any] = {"beam_size": int(os.getenv("WHISPER_BEAM_SIZE", "1"))}
        lang = _effective_asr_language(language)
        if lang:
            kwargs["language"] = lang

        # Streaming-ish chunks: defaults tuned vs original faster-whisper (vad off, condition on).
        kwargs["vad_filter"] = _env_bool("WHISPER_VAD_FILTER", True)
        kwargs["vad_parameters"] = {
            "min_silence_duration_ms": int(os.getenv("WHISPER_VAD_MIN_SILENCE_MS", "500"))
        }
        kwargs["condition_on_previous_text"] = _env_bool("WHISPER_CONDITION_ON_PREVIOUS_TEXT", False)

        nst = _env_float_optional("WHISPER_NO_SPEECH_THRESHOLD")
        if nst is not None:
            kwargs["no_speech_threshold"] = nst
        crt = _env_float_optional("WHISPER_COMPRESSION_RATIO_THRESHOLD")
        if crt is not None:
            kwargs["compression_ratio_threshold"] = crt
        lpt = _env_float_optional("WHISPER_LOG_PROB_THRESHOLD")
        if lpt is not None:
            kwargs["log_prob_threshold"] = lpt
        hst = _env_float_optional("WHISPER_HALLUCINATION_SILENCE_THRESHOLD")
        if hst is not None:
            kwargs["hallucination_silence_threshold"] = hst

        try:
            segments, info = model.transcribe(str(path), **kwargs)
        except Exception as exc:
            return "", {
                "confidence": 0.0,
                "language": lang or "unknown",
                "model_size": model_size,
                "error": type(exc).__name__,
                "message": str(exc)[:240],
            }

        parts: list[str] = []
        for seg in segments:
            t = (seg.text or "").strip()
            if t:
                parts.append(t)
        text = " ".join(parts).strip()

        meta = {
            "confidence": float(getattr(info, "language_probability", 0.5) or 0.5),
            "language": getattr(info, "language", None) or lang or "unknown",
            "duration_after_vad": getattr(info, "duration", None),
            "model_size": model_size,
        }
        return text, meta
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def decode_media_bytes_to_mono16k_float32(data: bytes, suffix: str) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Decode container bytes (webm/ogg/...) to mono 16k PCM float32 via ffmpeg.
    Returns waveform in [-1, 1] and diagnostics meta.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = Path(tmp.name)
    try:
        tmp.write(data)
        tmp.close()
        proc = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(path),
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-ac",
                "1",
                "-ar",
                "16000",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            msg = (proc.stderr.decode("utf-8", errors="replace") or "ffmpeg decode failed").strip()[:240]
            return np.array([], dtype=np.float32), {"error": "FFmpegDecodeError", "message": msg}
        pcm = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
        return pcm, {"sample_rate": 16000}
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def transcribe_float32_window(segment: np.ndarray, *, language: str | None) -> tuple[str, dict[str, Any]]:
    """Transcribe already-decoded 16k mono float32 segment."""
    model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
    model = _get_model(model_size)
    kwargs: dict[str, Any] = {"beam_size": int(os.getenv("WHISPER_BEAM_SIZE", "1"))}
    lang = _effective_asr_language(language)
    if lang:
        kwargs["language"] = lang
    kwargs["vad_filter"] = _env_bool("WHISPER_VAD_FILTER", True)
    kwargs["vad_parameters"] = {
        "min_silence_duration_ms": int(os.getenv("WHISPER_VAD_MIN_SILENCE_MS", "500"))
    }
    kwargs["condition_on_previous_text"] = _env_bool("WHISPER_CONDITION_ON_PREVIOUS_TEXT", False)
    try:
        segments, info = model.transcribe(segment, **kwargs)
    except Exception as exc:
        return "", {
            "confidence": 0.0,
            "language": lang or "unknown",
            "model_size": model_size,
            "error": type(exc).__name__,
            "message": str(exc)[:240],
        }
    parts: list[str] = []
    for seg in segments:
        t = (seg.text or "").strip()
        if t:
            parts.append(t)
    text = " ".join(parts).strip()
    meta = {
        "confidence": float(getattr(info, "language_probability", 0.5) or 0.5),
        "language": getattr(info, "language", None) or lang or "unknown",
        "duration_after_vad": getattr(info, "duration", None),
        "model_size": model_size,
    }
    return text, meta


def suffix_from_mime(mime: str) -> str:
    m = (mime or "").split(";")[0].strip().lower()
    if "wav" in m:
        return ".wav"
    if "ogg" in m:
        return ".ogg"
    if "mp4" in m or "m4a" in m:
        return ".m4a"
    return ".webm"
