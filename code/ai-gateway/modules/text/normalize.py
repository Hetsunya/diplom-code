"""Map heterogeneous speech-service JSON into the internal ASR shape."""

from __future__ import annotations

from typing import Any


def _str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def normalize_asr_response(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize external ASR JSON to keys expected by `text_analysis` builder.

    Supports canonical speech-service fields plus common aliases (Whisper-style `text`, etc.).
    """
    partial = _str_or_none(raw.get("transcript_partial"))
    if partial is None:
        partial = _str_or_none(raw.get("text") or raw.get("transcription") or raw.get("hypothesis"))

    final = _str_or_none(raw.get("transcript_final"))
    if final is None:
        final = _str_or_none(raw.get("final_transcript") or raw.get("final"))

    segs = raw.get("segments")
    if isinstance(segs, list) and segs and not partial:
        parts: list[str] = []
        for s in segs:
            if isinstance(s, dict):
                t = _str_or_none(s.get("text"))
                if t:
                    parts.append(t)
        if parts:
            partial = " ".join(parts)

    lang = raw.get("language")
    language = str(lang) if isinstance(lang, str) and lang.strip() else None

    tf = raw.get("text_features")
    text_features: dict[str, Any] = {}
    if isinstance(tf, dict):
        text_features = dict(tf)

    return {
        "transcript_partial": partial,
        "transcript_final": final,
        "language": language,
        "text_features": text_features,
    }


def has_transcript_content(norm: dict[str, Any]) -> bool:
    """True if we should emit a `text_analysis` message (non-empty partial or final)."""
    p = norm.get("transcript_partial")
    f = norm.get("transcript_final")
    return bool((isinstance(p, str) and p.strip()) or (isinstance(f, str) and f.strip()))
