from __future__ import annotations

import asyncio
import json
import os
import urllib.request
import urllib.error
import websockets
from typing import Awaitable, Callable, Any


class SessionWSClient:
    def __init__(
        self,
        url: str,
        on_message: Callable[[dict, websockets.WebSocketClientProtocol], Awaitable[None]],
        session_id: int = 0,
        enable_report_loop: bool = True,
    ):
        self.url = url
        self.on_message = on_message
        self.session_id = session_id
        self.enable_report_loop = enable_report_loop
        self.access_token: str | None = None

    def _http_base(self) -> str:
        # ws://backend:8080 -> http://backend:8080
        if self.url.startswith("ws://"):
            return "http://" + self.url[len("ws://") :].split("/ws/")[0]
        if self.url.startswith("wss://"):
            return "https://" + self.url[len("wss://") :].split("/ws/")[0]
        # fallback
        return "http://backend:8080"

    def _connect_max_msg_size(self) -> int | None:
        """
        Default websockets.recv limit is ~1 MiB — room-wide `audio` JSON with stacked WebM exceeds it.
        0 / none → unlimited (not recommended production); default 52 MiB.
        """
        raw = os.getenv("AI_GATEWAY_WS_MAX_MSG_BYTES", str(52 * 1024 * 1024)).strip().lower()
        if raw in ("0", "", "none", "unlimited", "inf"):
            return None
        try:
            n = int(raw)
        except ValueError:
            return 52 * 1024 * 1024
        return None if n <= 0 else n

    def _connect_ping_kw(self) -> dict[str, Any]:
        """Avoid keepalive ping timeouts while DeepFace / ASR handlers run for many seconds."""
        out: dict[str, Any] = {}
        try:
            pi = float(os.getenv("AI_GATEWAY_WS_PING_INTERVAL", "25").strip())
            out["ping_interval"] = None if pi <= 0 else pi
        except ValueError:
            out["ping_interval"] = 25.0
        try:
            pt = float(os.getenv("AI_GATEWAY_WS_PING_TIMEOUT", "300").strip())
            out["ping_timeout"] = None if pt <= 0 else pt
        except ValueError:
            out["ping_timeout"] = 300.0
        try:
            out["close_timeout"] = max(5.0, float(os.getenv("AI_GATEWAY_WS_CLOSE_TIMEOUT", "30").strip()))
        except ValueError:
            out["close_timeout"] = 30.0
        return out

    def _fetch_access_token(self) -> str | None:
        email = os.getenv("AI_GATEWAY_EMAIL", "demo1@example.com")
        password = os.getenv("AI_GATEWAY_PASSWORD", "demo1pass")
        body = json.dumps({"email": email, "password": password}).encode("utf-8")

        req = urllib.request.Request(
            self._http_base() + "/auth/token",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("accessToken")
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            print(f"[AUTH] failed to fetch token: {e}")
            return None

    async def connect(self):
        backoff = 1
        while True:
            try:
                if not self.access_token:
                    self.access_token = self._fetch_access_token()

                headers = None
                if self.access_token:
                    headers = {"Authorization": f"Bearer {self.access_token}"}

                connect_kw: dict[str, Any] = {
                    "max_size": self._connect_max_msg_size(),
                    **self._connect_ping_kw(),
                }
                if headers:
                    connect_kw["additional_headers"] = headers
                async with websockets.connect(self.url, **connect_kw) as ws:
                    print(f"[WS] connected to {self.url}")
                    backoff = 1

                    bg_tasks: list[asyncio.Task[Any]] = []
                    if self.enable_report_loop:
                        from report_loop import report_loop

                        holder: list[Any] = [ws]
                        bg_tasks.append(
                            asyncio.create_task(
                                report_loop(holder, self.session_id),
                                name="report_loop",
                            )
                        )

                    queue: asyncio.Queue[str | bytes | None] = asyncio.Queue()

                    async def reader_loop() -> None:
                        try:
                            async for raw in ws:
                                await queue.put(raw)
                        finally:
                            await queue.put(None)

                    reader_task = asyncio.create_task(reader_loop(), name="ws_reader")

                    try:
                        while True:
                            raw = await queue.get()
                            if raw is None:
                                break
                            try:
                                msg = json.loads(raw)
                            except json.JSONDecodeError:
                                snippet = raw[:240] if isinstance(raw, str) else raw
                                print("[WS] invalid json:", snippet)
                                continue

                            await self.on_message(msg, ws)
                    finally:
                        reader_task.cancel()
                        try:
                            await reader_task
                        except asyncio.CancelledError:
                            pass
                        for t in bg_tasks:
                            t.cancel()
                        if bg_tasks:
                            await asyncio.gather(*bg_tasks, return_exceptions=True)
            except Exception as e:
                print(f"[WS] connect failed: {e} (retry in {backoff}s)")
                self.access_token = None
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
