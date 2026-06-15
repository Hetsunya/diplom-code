"""Time-bucket + trace_id index for fusing multimodal feature streams (report v1)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def compute_fusion_meta(features: list[dict[str, Any]], bucket_sec: float) -> dict[str, Any]:
    """
    Join hints for the report NN / UI: per-participant trace_ids and per-bucket kind counts.

    `bucket_sec` <= 0 disables bucket breakdown (trace index still computed).
    """
    trace_by_participant: dict[str, set[str]] = defaultdict(set)
    for f in features:
        tid = f.get("trace_id")
        if isinstance(tid, str) and tid.strip():
            pid = str(f.get("participant_id") or "unknown")
            trace_by_participant[pid].add(tid.strip())

    buckets: list[dict[str, Any]] = []
    if bucket_sec > 0:
        by_key: dict[str, dict[str, Any]] = {}
        for f in features:
            ts_raw = f.get("ts")
            try:
                ts = float(ts_raw) if ts_raw is not None else 0.0
            except (TypeError, ValueError):
                ts = 0.0
            b = int(ts // bucket_sec)
            pid = str(f.get("participant_id") or "unknown")
            key = f"{pid}|{b}"
            slot = by_key.setdefault(
                key,
                {
                    "participant_id": pid,
                    "bucket_index": b,
                    "bucket_start_ts": round(b * bucket_sec, 3),
                    "kinds": defaultdict(int),
                    "trace_ids": set(),
                },
            )
            kind = f.get("kind") or "unknown"
            if isinstance(kind, str):
                slot["kinds"][kind] += 1
            tid = f.get("trace_id")
            if isinstance(tid, str) and tid.strip():
                slot["trace_ids"].add(tid.strip())

        for slot in by_key.values():
            kinds_map = slot["kinds"]
            traces = slot["trace_ids"]
            buckets.append(
                {
                    "participant_id": slot["participant_id"],
                    "bucket_index": slot["bucket_index"],
                    "bucket_start_ts": slot["bucket_start_ts"],
                    "kinds": dict(kinds_map),
                    "trace_ids": sorted(traces),
                }
            )
        buckets.sort(key=lambda x: (x["participant_id"], x["bucket_index"]))

    return {
        "bucket_sec": round(bucket_sec, 3) if bucket_sec > 0 else 0.0,
        "trace_ids_by_participant": {k: sorted(v) for k, v in sorted(trace_by_participant.items())},
        "buckets": buckets,
    }
