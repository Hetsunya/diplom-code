import os
import time
from typing import Any, Protocol

from observability import incr, log_event
from modules.shared.session_modules import set_session_modules


class Plugin(Protocol):
    name: str

    def can_handle(self, msg: dict[str, Any]) -> bool: ...

    async def process(self, msg: dict[str, Any], ws: Any) -> None: ...


def _load_plugins() -> list[Plugin]:
    """
    Load analyzers from `modules/` (see `modules/registry.py`).

    Legacy `plugins/*` files are thin shims for compatibility only.
    """
    from modules.registry import iter_plugins

    return list(iter_plugins())


_PLUGINS: list[Plugin] = []
_LAST_CFG_POLL_MONO: float = 0.0
_logged_first_ws_audio: bool = False


def _get_plugins() -> list[Plugin]:
    global _PLUGINS
    if not _PLUGINS:
        _PLUGINS = _load_plugins()
    return _PLUGINS


def _plugin_sort_key(p: Plugin) -> int:
    return int(getattr(p, "priority", 500))


async def handle_message(msg: dict[str, Any], ws: Any) -> None:
    """Dispatch to all plugins that can handle the message (sorted by priority)."""
    global _LAST_CFG_POLL_MONO, _logged_first_ws_audio
    if msg.get("type") == "join":
        payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
        modules = payload.get("analysis_modules") if isinstance(payload.get("analysis_modules"), dict) else None
        sid = msg.get("session_id")
        if modules is not None and isinstance(sid, int):
            set_session_modules(sid, modules)

    if msg.get("type") == "audio":
        incr("inbound_ws_audio")
        if not _logged_first_ws_audio:
            _logged_first_ws_audio = True
            pl = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
            b64 = pl.get("chunk_base64") if isinstance(pl.get("chunk_base64"), str) else ""
            log_event(
                "first_inbound_ws_audio",
                module="gateway",
                extra={
                    "session_id": msg.get("session_id"),
                    "participant_id": msg.get("participant_id"),
                    "b64_chars": len(b64),
                },
            )

    poll = float(os.getenv("AI_GATEWAY_CONFIG_POLL_SEC", "10"))
    if poll > 0:
        now = time.monotonic()
        if now - _LAST_CFG_POLL_MONO >= poll:
            _LAST_CFG_POLL_MONO = now
            from gateway_config import maybe_reload_gateway_config

            if maybe_reload_gateway_config():
                log_event("gateway_config_reloaded")

    for plugin in sorted(_get_plugins(), key=_plugin_sort_key):
        if plugin.can_handle(msg):
            await plugin.process(msg, ws)
