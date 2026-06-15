import asyncio
import json
import os
from datetime import datetime, timezone
from urllib import error, request

import websockets


def _http_base(ws_base_url: str) -> str:
    if ws_base_url.startswith("ws://"):
        return "http://" + ws_base_url[len("ws://") :]
    if ws_base_url.startswith("wss://"):
        return "https://" + ws_base_url[len("wss://") :]
    return "http://localhost:8080"


def _fetch_token(http_base: str, email: str, password: str) -> str:
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = request.Request(
        http_base.rstrip("/") + "/auth/token",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = data.get("accessToken")
    if not isinstance(token, str) or not token:
        raise RuntimeError("No accessToken returned by /auth/token")
    return token


def _http_get_json(url: str, token: str) -> object:
    req = request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    with request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def main() -> None:
    ws_base_url = os.getenv("BACKEND_WS_BASE_URL", "ws://localhost:8080")
    session_id = int(os.getenv("SESSION_ID", "2"))
    email = os.getenv("AI_GATEWAY_EMAIL", "demo1@example.com")
    password = os.getenv("AI_GATEWAY_PASSWORD", "demo1pass")
    participant = os.getenv("AI_GATEWAY_E2E_PARTICIPANT_ID", "p_e2e_check")
    trace_id = f"e2e-{int(datetime.now(timezone.utc).timestamp())}"

    http_base = _http_base(ws_base_url)
    token = _fetch_token(http_base, email, password)
    ws_url = f"{ws_base_url.rstrip('/')}/ws/sessions/{session_id}"
    now = datetime.now(timezone.utc).isoformat()

    face_msg = {
        "type": "face_analysis",
        "session_id": session_id,
        "participant_id": participant,
        "payload": {
            "module": "face",
            "version": "e2e-v1",
            "stage": "partial",
            "trace_id": trace_id,
            "face_features": {
                "dominant_emotion": "neutral",
                "probs": {"neutral": 99.0},
                "face_detected": True,
                "confidence": 99.0,
            },
        },
        "timestamp": now,
    }
    report_msg = {
        "type": "analysis_report_partial",
        "session_id": session_id,
        "participant_id": "",
        "payload": {
            "module": "report",
            "version": "e2e-v1",
            "stage": "partial",
            "trace_id": trace_id,
            "report": {
                "summary": "e2e synthetic report",
                "participants": [{"participant_id": participant, "state": "ok"}],
            },
            "model_version": "e2e-v1",
            "generated_at": now,
            "config_snapshot": {"source": "e2e_analysis_readpath_check"},
        },
        "timestamp": now,
    }

    headers = {"Authorization": f"Bearer {token}"}
    async with websockets.connect(ws_url, additional_headers=headers) as ws:
        await ws.send(json.dumps(face_msg))
        await ws.send(json.dumps(report_msg))
        # Allow backend hub/store to process.
        await asyncio.sleep(1.0)

    events_url = f"{http_base.rstrip('/')}/sessions/{session_id}/analysis/events?limit=200"
    report_url = f"{http_base.rstrip('/')}/sessions/{session_id}/analysis/report"

    events = _http_get_json(events_url, token)
    if not isinstance(events, list):
        raise RuntimeError("Invalid /analysis/events response shape")
    has_face = any(
        isinstance(e, dict) and e.get("event_type") == "face_analysis" and e.get("trace_id") == trace_id
        for e in events
    )
    has_report_event = any(
        isinstance(e, dict)
        and e.get("event_type") == "analysis_report_partial"
        and e.get("trace_id") == trace_id
        for e in events
    )
    if not has_face:
        raise RuntimeError("Stored events do not contain synthetic face_analysis event")
    if has_report_event:
        # report events are stored in dedicated table; this may appear only if strategy changes.
        pass

    report = _http_get_json(report_url, token)
    if not isinstance(report, dict):
        raise RuntimeError("Invalid /analysis/report response shape")
    if report.get("trace_id") != trace_id:
        raise RuntimeError("Latest analysis report does not match E2E trace_id")

    print(
        "OK: analysis read-path verified",
        f"session={session_id}",
        f"trace_id={trace_id}",
        f"events={len(events)}",
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except error.HTTPError as e:
        raise SystemExit(f"HTTP error during E2E check: {e.code} {e.reason}") from e
