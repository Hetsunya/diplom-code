"""ASR HTTP service for ai-gateway (stub or faster-whisper)."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

from asr_whisper import (
    decode_media_bytes_to_mono16k_float32,
    suffix_from_mime,
    transcribe_float32_window,
)

app = FastAPI(title="emeeting-speech-service", version="0.2.0")

def _canonical_asr_engine(raw: str | None) -> str:
    """Normalize env values: `faster_whisper`, `FAST-WHISPER` → whisper (faster-whisper path)."""
    if raw is None or not str(raw).strip():
        return "stub"
    e = str(raw).strip().lower().replace("_", "-")
    if e in ("", "none"):
        return "stub"
    if e in ("faster-whisper", "fast-whisper"):
        return "whisper"
    return e


_ENGINE_RAW = os.getenv("SPEECH_ASR_ENGINE", "stub")
_engine = _canonical_asr_engine(_ENGINE_RAW)
_executor = ThreadPoolExecutor(max_workers=int(os.getenv("SPEECH_ASR_WORKERS", "1")))
_logger = logging.getLogger("speech_service")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)
_logger.info(
    "speech_service engine=%r (raw SPEECH_ASR_ENGINE=%r)",
    _engine,
    _ENGINE_RAW,
)

_stream_lock = threading.Lock()
_stream_state: dict[str, dict[str, Any]] = {}


class TranscribeRequest(BaseModel):
    session_id: int
    participant_id: str
    trace_id: str
    audio: dict[str, Any] = {}


def _stub_response(req: TranscribeRequest) -> dict[str, Any]:
    return {
        "transcript_partial": f"[stub] session={req.session_id} participant={req.participant_id}",
        "transcript_final": None,
        "language": "ru",
        "text_features": {"confidence": 0.42, "sentiment": "neutral"},
    }


def _whisper_sync(req: TranscribeRequest) -> dict[str, Any]:
    audio = req.audio or {}
    b64 = audio.get("chunk_base64") or audio.get("data_base64") or audio.get("base64")
    if not isinstance(b64, str) or not b64.strip():
        return {
            "transcript_partial": "",
            "transcript_final": None,
            "language": audio.get("language") or "unknown",
            "text_features": {"confidence": 0.0, "note": "empty_chunk"},
        }

    mime = str(audio.get("mime") or audio.get("mime_type") or "audio/webm")
    lang_in = audio.get("language")
    lang = str(lang_in) if isinstance(lang_in, str) and lang_in else None

    try:
        raw = base64.b64decode(b64, validate=False)
    except Exception:
        return {
            "transcript_partial": "",
            "transcript_final": None,
            "language": "unknown",
            "text_features": {"confidence": 0.0, "note": "base64_decode_failed"},
        }

    if len(raw) < 256:
        return {
            "transcript_partial": "",
            "transcript_final": None,
            "language": lang or "unknown",
            "text_features": {"confidence": 0.0, "note": "chunk_too_small"},
        }

    suffix = suffix_from_mime(mime)
    pcm, decode_meta = decode_media_bytes_to_mono16k_float32(raw, suffix)
    if decode_meta.get("error"):
        return {
            "transcript_partial": "",
            "transcript_final": None,
            "language": lang or "unknown",
            "text_features": {
                "confidence": 0.0,
                "note": "decode_failed",
                "error": decode_meta.get("error"),
                "message": decode_meta.get("message"),
            },
        }
    if pcm.size == 0:
        return {
            "transcript_partial": "",
            "transcript_final": None,
            "language": lang or "unknown",
            "text_features": {"confidence": 0.0, "note": "empty_pcm"},
        }

    window_seconds = float(os.getenv("WHISPER_WINDOW_SECONDS", "4.0"))
    step_seconds = float(os.getenv("WHISPER_STEP_SECONDS", "2.0"))
    sample_rate = int(decode_meta.get("sample_rate", 16000) or 16000)
    duration_sec = float(pcm.size) / float(sample_rate)

    stream_key = f"{req.session_id}:{req.participant_id}"
    with _stream_lock:
        st = _stream_state.get(stream_key, {"last_text": "", "last_duration": 0.0})
        last_duration = float(st.get("last_duration", 0.0))
        last_text = str(st.get("last_text", ""))

    final_marker = bool(audio.get("final_chunk")) or bool(audio.get("is_final"))
    should_run = final_marker or (
        duration_sec >= window_seconds and (duration_sec - last_duration >= step_seconds)
    )
    if not should_run:
        return {
            "transcript_partial": "",
            "transcript_final": None,
            "language": lang or "unknown",
            "text_features": {"confidence": 0.0, "note": "step_wait"},
        }

    window_samples = max(1, int(window_seconds * sample_rate))
    segment = pcm[-window_samples:] if pcm.size > window_samples else pcm
    text, meta = transcribe_float32_window(segment.astype(np.float32), language=lang)
    if meta.get("error"):
        _logger.warning(
            "whisper_transcribe_failed trace_id=%s participant=%s error=%s msg=%s",
            req.trace_id,
            req.participant_id,
            meta.get("error"),
            meta.get("message"),
        )
    emit_text = text.strip()
    if emit_text and emit_text == last_text and not final_marker:
        emit_text = ""

    with _stream_lock:
        if final_marker:
            _stream_state.pop(stream_key, None)
        else:
            _stream_state[stream_key] = {
                "last_text": text.strip() or last_text,
                "last_duration": duration_sec,
            }

    text_features: dict[str, object] = {
        "confidence": meta.get("confidence"),
        "model_size": meta.get("model_size"),
        "sentiment": "neutral",
        "window_seconds": window_seconds,
        "step_seconds": step_seconds,
    }
    if meta.get("error"):
        text_features["error"] = meta["error"]
        text_features["message"] = meta.get("message")
    return {
        "transcript_partial": emit_text,
        "transcript_final": emit_text if final_marker and emit_text else None,
        "language": meta.get("language") or lang or "unknown",
        "text_features": text_features,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "engine": _engine, "engine_env": _ENGINE_RAW}


@app.post("/v1/transcribe")
async def transcribe(req: TranscribeRequest) -> dict[str, Any]:
    if _engine in ("stub", "", "none"):
        return _stub_response(req)
    if _engine == "whisper":
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_executor, _whisper_sync, req)
    _logger.warning("unknown SPEECH_ASR_ENGINE=%r → stub", _ENGINE_RAW)
    return _stub_response(req)
