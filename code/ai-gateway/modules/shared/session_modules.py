"""Per-session module enablement map (set from WS join payload)."""

from __future__ import annotations

from threading import Lock
from typing import Any

_lock = Lock()
_session_modules: dict[int, dict[str, bool]] = {}


def set_session_modules(session_id: int, modules: dict[str, Any]) -> None:
    normalized: dict[str, bool] = {}
    for k, v in modules.items():
        if isinstance(k, str):
            normalized[k.strip().lower()] = bool(v)
    with _lock:
        _session_modules[int(session_id)] = normalized


def is_module_enabled_for_session(session_id: int | None, module_name: str, *, default: bool = True) -> bool:
    if session_id is None:
        return default
    sid = int(session_id)
    key = module_name.strip().lower()
    with _lock:
        m = _session_modules.get(sid)
    if not m:
        return default
    if key not in m:
        return default
    return bool(m[key])

