from typing import Any

from observability import incr, log_event


class PingPlugin:
    name = "ping"
    priority = 50

    def metadata(self) -> dict[str, str]:
        return {
            "module": "gateway",
            "provider": "",
            "model": "",
            "version": "1",
        }

    def can_handle(self, msg: dict[str, Any]) -> bool:
        return msg.get("type") == "ping"

    async def process(self, msg: dict[str, Any], ws: Any) -> None:
        session_id = msg.get("session_id")
        incr("ws_ping_received")
        log_event("ws_ping", module="gateway", extra={"session_id": session_id})


plugin = PingPlugin()
