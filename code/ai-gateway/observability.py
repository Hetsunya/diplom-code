"""Lightweight metrics + structured logs for the hybrid analysis pipeline."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any

_log = logging.getLogger("ai_gateway")
if not _log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    _log.addHandler(h)
    _log.setLevel(logging.INFO)

_lock = threading.Lock()
_counters: dict[str, int] = {}
_latency_ring: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=256))


def incr(metric: str, n: int = 1) -> None:
    with _lock:
        _counters[metric] = _counters.get(metric, 0) + n


def snapshot_metrics() -> dict[str, int]:
    with _lock:
        return dict(_counters)


def observe_module_latency(module: str, elapsed_ms: float) -> None:
    """Rolling latency samples per module (for ops / snapshot_health)."""
    if elapsed_ms < 0:
        return
    key = (module or "unknown").strip().lower() or "unknown"
    with _lock:
        _latency_ring[key].append(round(float(elapsed_ms), 3))


def latency_summary(module: str) -> dict[str, Any]:
    with _lock:
        ring = _latency_ring.get(module)
        vals = sorted(ring) if ring else []
    if not vals:
        return {}
    n = len(vals)
    idx = min(n - 1, max(0, int(round(0.95 * (n - 1)))))
    return {
        "count": n,
        "p95_ms": vals[idx],
        "max_ms": vals[-1],
        "avg_ms": round(sum(vals) / n, 3),
    }


def _latency_stats(vals_sorted: list[float]) -> dict[str, Any]:
    n = len(vals_sorted)
    idx = min(n - 1, max(0, int(round(0.95 * (n - 1)))))
    return {
        "count": n,
        "p95_ms": vals_sorted[idx],
        "max_ms": vals_sorted[-1],
        "avg_ms": round(sum(vals_sorted) / n, 3),
    }


def snapshot_health() -> dict[str, Any]:
    """Counters + approximate latency rings — scrape/log periodically if needed."""
    with _lock:
        ctr = dict(_counters)
        lat: dict[str, Any] = {}
        for m in sorted(_latency_ring.keys()):
            ring = _latency_ring[m]
            vals = sorted(ring) if ring else []
            if vals:
                lat[m] = _latency_stats(vals)
    return {"counters": ctr, "latency_ms": lat}


def log_event(
    event: str,
    *,
    trace_id: str | None = None,
    module: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    parts = [f"event={event}"]
    if trace_id:
        parts.append(f"trace_id={trace_id}")
    if module:
        parts.append(f"module={module}")
    if extra:
        for k, v in extra.items():
            parts.append(f"{k}={v}")
    _log.info(" ".join(parts))


def monotonic_ms() -> float:
    return time.monotonic() * 1000.0
