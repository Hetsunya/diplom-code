"""Optional HTTP client for the proprietary report NN."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def generate_report(
    own_nn_url: str,
    *,
    session_id: int,
    features: list[dict[str, Any]],
    config_snapshot: dict[str, Any],
    stage: str,
    fusion: dict[str, Any] | None = None,
    timeout_sec: float = 60.0,
) -> dict[str, Any] | None:
    if not own_nn_url or not own_nn_url.startswith("http"):
        return None
    body: dict[str, Any] = {
        "session_id": session_id,
        "stage": stage,
        "features": features,
        "config_snapshot": config_snapshot,
        "fusion": fusion if isinstance(fusion, dict) else {},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        own_nn_url.rstrip("/") + "/v1/report",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
