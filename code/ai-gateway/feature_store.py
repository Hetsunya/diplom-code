"""In-memory rolling buffer of recent analysis features per session (for report orchestrator)."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

_MAX_PER_KIND = 64


class FeatureStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # session_id -> deque of records
        self._by_session: dict[int, deque[dict[str, Any]]] = {}

    def push(
        self,
        session_id: int,
        *,
        kind: str,
        participant_id: str | None,
        trace_id: str | None,
        data: dict[str, Any],
    ) -> None:
        rec = {
            "ts": time.time(),
            "kind": kind,
            "participant_id": participant_id,
            "trace_id": trace_id,
            "data": data,
        }
        with self._lock:
            dq = self._by_session.setdefault(session_id, deque(maxlen=512))
            dq.append(rec)
            # trim same-kind tail? keep simple: global maxlen on deque

    def snapshot_session(self, session_id: int) -> list[dict[str, Any]]:
        with self._lock:
            dq = self._by_session.get(session_id)
            if not dq:
                return []
            return list(dq)[-_MAX_PER_KIND * 8 :]

    def session_ids(self) -> list[int]:
        with self._lock:
            return sorted(self._by_session.keys())


_store = FeatureStore()


def get_feature_store() -> FeatureStore:
    return _store
