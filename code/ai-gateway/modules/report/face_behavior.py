"""Aggregate face behavior events into report-friendly summary."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _mean(vals: list[float]) -> float | None:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 3)


def build_face_behavior_summary(features: list[dict[str, Any]]) -> dict[str, Any] | None:
    totals = {
        "events": 0,
        "trackable_events": 0,
    }
    guard_reasons: Counter[str] = Counter()
    engagement_by_participant: dict[str, list[float]] = defaultdict(list)
    participant_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"events": 0, "trackable_events": 0})

    for f in features:
        if f.get("kind") != "face":
            continue
        data = f.get("data") if isinstance(f.get("data"), dict) else {}
        behavior = data.get("face_behavior")
        if not isinstance(behavior, dict):
            continue
        quality = behavior.get("quality") if isinstance(behavior.get("quality"), dict) else {}
        if not isinstance(quality, dict):
            continue

        pid = str(f.get("participant_id") or "unknown")
        totals["events"] += 1
        participant_totals[pid]["events"] += 1

        trackable = quality.get("trackable") is True
        if trackable:
            totals["trackable_events"] += 1
            participant_totals[pid]["trackable_events"] += 1
            ep = behavior.get("engagement_proxy")
            if isinstance(ep, (int, float)):
                engagement_by_participant[pid].append(float(ep))
        else:
            reason = quality.get("guard_reason")
            if isinstance(reason, str) and reason.strip():
                guard_reasons[reason.strip()] += 1

    if totals["events"] == 0:
        return None

    participants = []
    for pid, p_totals in participant_totals.items():
        events = p_totals["events"]
        trackable = p_totals["trackable_events"]
        participants.append(
            {
                "participant_id": pid,
                "events": events,
                "trackable_events": trackable,
                "trackable_ratio": round(trackable / events, 3) if events > 0 else 0.0,
                "avg_engagement_proxy": _mean(engagement_by_participant[pid]),
            }
        )
    participants.sort(key=lambda p: p.get("events", 0), reverse=True)

    return {
        "events": totals["events"],
        "trackable_events": totals["trackable_events"],
        "trackable_ratio": round(totals["trackable_events"] / totals["events"], 3) if totals["events"] > 0 else 0.0,
        "guard_reasons": dict(guard_reasons),
        "participants": participants,
    }

