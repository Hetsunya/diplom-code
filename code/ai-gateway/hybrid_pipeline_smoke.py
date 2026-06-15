#!/usr/bin/env python3
"""
BL-036 hybrid smoke: local WS hub + ai-gateway worker.

Validates (when deps installed: numpy, opencv, deepface, tf…):
  frame -> face_analysis + legacy emotion
  audio -> audio_analysis + text_analysis (stub HTTP speech-service)
  report_loop -> analysis_report_partial, then analysis_report (final on shutdown)

Run from `code/ai-gateway`:
  python hybrid_pipeline_smoke.py

Requires heavy ML stack like `smoke_ws_emotion_test.py`. Contract checks always via `hybrid_contract`.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import websockets
from PIL import Image


PORT = 8767
SESSION_ID = 77
PARTICIPANT_ID = "p_hybrid_smoke"

clients: set[websockets.WebSocketServerProtocol] = set()


async def broadcast_server_handler(ws: websockets.WebSocketServerProtocol) -> None:
    clients.add(ws)
    try:
        async for raw in ws:
            dead: list[websockets.WebSocketServerProtocol] = []
            for c in clients:
                try:
                    if c.open:
                        await c.send(raw)
                except Exception:
                    dead.append(c)
            for c in dead:
                clients.discard(c)
    finally:
        clients.discard(ws)


def _start_speech_stub() -> tuple[HTTPServer, threading.Thread, int]:
    class TranscribeHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            if path.rstrip("/").endswith("/v1/transcribe"):
                body_obj = {
                    "transcript_partial": "hybrid smoke transcript",
                    "transcript_final": None,
                    "language": "en",
                    "text_features": {},
                }
                body = json.dumps(body_obj).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *_args: Any) -> None:
            return

    srv = HTTPServer(("127.0.0.1", 0), TranscribeHandler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    port = int(srv.server_address[1])
    return srv, th, port


def _write_hybrid_modules(speech_port: int) -> str:
    cfg = {
        "modules": {
            "text": {
                "enabled": True,
                "provider": "http",
                "model": "hybrid-smoke-v1",
                "params": {
                    "speech_service_url": f"http://127.0.0.1:{speech_port}",
                    "timeout_sec": 10,
                    "retries": 1,
                    "backoff_sec": 0.1,
                },
            },
            "audio": {
                "enabled": True,
                "provider": "baseline",
                "model": "audio-features-v2",
                "params": {
                    "min_chunk_bytes": 400,
                    "max_rms_samples": 8000,
                    "pause_threshold_ms": 2000,
                },
            },
            "face": {
                "enabled": True,
                "provider": "deepface",
                "model": "emotion-v1",
                "params": {
                    "min_interval_sec": 0.0,
                    "min_confidence": 0.0,
                    "enforce_detection": False,
                    "detector_backend": "opencv",
                    "align": False,
                    "min_laplacian_var": 0.0,
                    "min_face_side_px": 0,
                    "emit_no_face_face_analysis": False,
                },
            },
            "report": {
                "enabled": True,
                "provider": "stub-nn",
                "model": "hybrid-report-v1",
                "params": {
                    "interval_sec": 1,
                    "own_nn_url": "",
                    "report_bucket_sec": 60,
                    "report_wake_floor_sec": 1,
                },
            },
        }
    }
    fd, path = tempfile.mkstemp(suffix=".modules.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return path


async def main() -> None:
    from hybrid_contract import (
        HybridContractError,
        validate_audio_analysis,
        validate_face_analysis,
        validate_report_message,
        validate_text_analysis,
    )

    speech_srv, _speech_th, speech_port = _start_speech_stub()
    cfg_path = _write_hybrid_modules(speech_port)
    os.environ["AI_GATEWAY_MODULES_CONFIG"] = cfg_path

    from gateway_config import load_gateway_config, set_gateway_config

    set_gateway_config(load_gateway_config())

    from handlers import handle_message
    from ws_client import SessionWSClient

    server = await websockets.serve(broadcast_server_handler, "127.0.0.1", PORT)

    gateway_url = f"ws://127.0.0.1:{PORT}/ws/sessions/{SESSION_ID}"
    gateway = SessionWSClient(
        url=gateway_url,
        on_message=handle_message,
        session_id=SESSION_ID,
        enable_report_loop=True,
    )
    gateway_task = asyncio.create_task(gateway.connect())

    got: dict[str, dict[str, Any]] = {}

    try:
        async with websockets.connect(gateway_url) as test_ws:
            await test_ws.send(
                json.dumps(
                    {
                        "type": "join",
                        "session_id": SESSION_ID,
                        "participant_id": PARTICIPANT_ID,
                        "payload": {"name": "HybridSmoke"},
                        "timestamp": "2026-01-01T00:00:00Z",
                    }
                )
            )

            img = Image.new("RGB", (224, 224), (40, 40, 40))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

            await test_ws.send(
                json.dumps(
                    {
                        "type": "frame",
                        "session_id": SESSION_ID,
                        "participant_id": PARTICIPANT_ID,
                        "payload": {"frame": data_url},
                        "timestamp": "2026-01-01T00:00:01Z",
                    }
                )
            )

            chunk_b64 = base64.b64encode(os.urandom(800)).decode("ascii")
            await test_ws.send(
                json.dumps(
                    {
                        "type": "audio",
                        "session_id": SESSION_ID,
                        "participant_id": PARTICIPANT_ID,
                        "payload": {
                            "chunk_base64": chunk_b64,
                            "mime": "audio/webm",
                            "timeslice_ms": 500,
                        },
                        "timestamp": "2026-01-01T00:00:02Z",
                    }
                )
            )

            # Face + audio outputs + first partial report (wake_floor 1s + processing).
            deadline = asyncio.get_event_loop().time() + 90.0
            while asyncio.get_event_loop().time() < deadline:
                raw = await asyncio.wait_for(test_ws.recv(), timeout=3.0)
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                typ = msg.get("type")
                if isinstance(typ, str) and typ not in got:
                    got[typ] = msg

                if all(
                    k in got
                    for k in (
                        "face_analysis",
                        "emotion",
                        "audio_analysis",
                        "text_analysis",
                        "analysis_report_partial",
                    )
                ):
                    break

            if "face_analysis" not in got:
                raise RuntimeError("hybrid smoke: no face_analysis (need deepface/tf stack?)")
            if "emotion" not in got:
                raise RuntimeError("hybrid smoke: no legacy emotion")
            if "audio_analysis" not in got:
                raise RuntimeError("hybrid smoke: no audio_analysis")
            if "text_analysis" not in got:
                raise RuntimeError("hybrid smoke: no text_analysis (speech stub / URL mismatch?)")
            if "analysis_report_partial" not in got:
                raise RuntimeError("hybrid smoke: no analysis_report_partial")

            validate_face_analysis(got["face_analysis"])
            validate_audio_analysis(got["audio_analysis"])
            validate_text_analysis(got["text_analysis"])
            validate_report_message(got["analysis_report_partial"], expect_final=False)

            rep = got["analysis_report_partial"].get("payload", {}).get("report")
            if isinstance(rep, dict) and "fusion" in rep:
                fu = rep["fusion"]
                if not isinstance(fu, dict):
                    raise HybridContractError("report.fusion must be object")

            gateway_task.cancel()
            try:
                await gateway_task
            except asyncio.CancelledError:
                pass

            final_msg: dict[str, Any] | None = None
            fd_until = asyncio.get_event_loop().time() + 20.0
            while asyncio.get_event_loop().time() < fd_until:
                try:
                    raw = await asyncio.wait_for(test_ws.recv(), timeout=3.0)
                except asyncio.TimeoutError:
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "analysis_report":
                    final_msg = msg
                    break

            if final_msg is None:
                raise RuntimeError(
                    "hybrid smoke: no analysis_report final on hub after gateway shutdown "
                    "(report_loop should emit final on CancelledError)."
                )
            validate_report_message(final_msg, expect_final=True)

            print(
                "OK: hybrid_pipeline_smoke — face, emotion, audio, text, partial+final report envelopes validated."
            )
    finally:
        server.close()
        await server.wait_closed()
        speech_srv.shutdown()
        try:
            os.unlink(cfg_path)
        except OSError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
