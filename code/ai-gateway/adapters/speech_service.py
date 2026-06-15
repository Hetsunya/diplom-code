"""HTTP client for external speech-service (ASR)."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from observability import incr

_lock = threading.Lock()
# Per speech-service base URL: consecutive failures and circuit-open deadline (monotonic sec).
_circuit: dict[str, tuple[int, float]] = {}


def transcribe_audio_chunk(
    base_url: str,
    *,
    session_id: int,
    participant_id: str,
    trace_id: str,
    audio_payload: dict[str, Any],
    timeout_sec: float = 15.0,
    retries: int = 2,
    backoff_sec: float = 0.5,
    circuit_failure_threshold: int = 5,
    circuit_open_sec: float = 30.0,
) -> dict[str, Any] | None:
    """
    POST {base_url}/v1/transcribe

    Optional circuit breaker: after `circuit_failure_threshold` consecutive failures,
    returns fast with `_error` / `_circuit_open` for `circuit_open_sec` seconds.

    Expected JSON body:
      { "session_id", "participant_id", "trace_id", "audio": { ... same as WS audio payload ... } }

    Expected JSON response (stub or real):
      {
        "transcript_partial": "...",
        "transcript_final": "...",
        "language": "ru",
        "text_features": { ... }
      }
    """
    key = base_url.rstrip("/")
    now = time.monotonic()
    with _lock:
        fails, open_until = _circuit.get(key, (0, 0.0))
        if now < open_until:
            return {
                "_error": "circuit_open",
                "_circuit_open": True,
                "_open_until": open_until,
            }

    url = key + "/v1/transcribe"
    body = {
        "session_id": session_id,
        "participant_id": participant_id,
        "trace_id": trace_id,
        "audio": audio_payload,
    }
    data = json.dumps(body).encode("utf-8")
    attempt = 0
    while attempt <= retries:
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw = resp.read().decode("utf-8")
                out = json.loads(raw)
                with _lock:
                    _circuit[key] = (0, 0.0)
                incr("speech_adapter_http_ok")
                return out
        except urllib.error.HTTPError as e:
            snippet = ""
            try:
                snippet = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            if attempt >= retries:
                incr("speech_adapter_http_error")
                err: dict[str, Any] = {
                    "_error": f"HTTPError {e.code}",
                    "_http_body_preview": snippet,
                    "_attempts": attempt + 1,
                }
                with _lock:
                    prev = _circuit.get(key, (0, 0.0))
                    nfails = prev[0] + 1
                    open_until = prev[1]
                    thr = max(1, int(circuit_failure_threshold))
                    if nfails >= thr:
                        open_until = time.monotonic() + max(1.0, float(circuit_open_sec))
                        nfails = 0
                    _circuit[key] = (nfails, open_until)
                return err
            sleep_for = backoff_sec * (2**attempt)
            time.sleep(sleep_for)
            attempt += 1
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            if attempt >= retries:
                incr("speech_adapter_transport_error")
                err = {"_error": str(e), "_attempts": attempt + 1}
                with _lock:
                    prev = _circuit.get(key, (0, 0.0))
                    nfails = prev[0] + 1
                    open_until = prev[1]
                    thr = max(1, int(circuit_failure_threshold))
                    if nfails >= thr:
                        open_until = time.monotonic() + max(1.0, float(circuit_open_sec))
                        nfails = 0
                    _circuit[key] = (nfails, open_until)
                return err
            sleep_for = backoff_sec * (2**attempt)
            time.sleep(sleep_for)
            attempt += 1
    return {"_error": "unexpected asr adapter state"}
