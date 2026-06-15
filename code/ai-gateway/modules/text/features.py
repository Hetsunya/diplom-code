"""Lightweight `text_features` enrichment when ASR omits NLP fields (v1 heuristic)."""

from __future__ import annotations

import re
from typing import Any

_POS_HINTS = (
    "спасибо",
    "хорошо",
    "отлично",
    "рад",
    "thanks",
    "great",
    "good",
    "love",
    "happy",
    "excellent",
)
_NEG_HINTS = (
    "плохо",
    "нет",
    "ошибк",
    "проблем",
    "bad",
    "hate",
    "sorry",
    "fail",
    "ugly",
    "error",
)


def _guess_sentiment(text: str) -> str:
    tl = text.lower()
    score = 0
    for w in _POS_HINTS:
        if w in tl:
            score += 1
    for w in _NEG_HINTS:
        if w in tl:
            score -= 1
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


def _keyphrases(text: str, limit: int = 8) -> list[str]:
    words = [w for w in re.split(r"\W+", text, flags=re.UNICODE) if len(w) > 2]
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        wl = w.lower()
        if wl in seen:
            continue
        seen.add(wl)
        out.append(w)
        if len(out) >= limit:
            break
    return out


def enrich_text_features(
    *,
    transcript_partial: str | None,
    transcript_final: str | None,
    text_features: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Merge ASR-provided features with defaults / heuristics (never overwrites non-empty sentiment).
    """
    out: dict[str, Any] = dict(text_features or {})
    text = (transcript_final or transcript_partial or "").strip()
    if not text:
        return out

    if "sentiment" not in out or not str(out.get("sentiment") or "").strip():
        out["sentiment"] = _guess_sentiment(text)

    if out.get("confidence") is None:
        # Rough proxy: longer partials slightly higher baseline (still 0..1).
        out["confidence"] = round(min(0.95, 0.25 + min(len(text), 200) / 400.0), 3)

    topics = out.get("topics")
    if not isinstance(topics, list):
        out["topics"] = []

    kph = out.get("keyphrases")
    if not isinstance(kph, list) or not kph:
        out["keyphrases"] = _keyphrases(text)

    return out
