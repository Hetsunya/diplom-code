"""Central registration of analysis plugins under `modules/`."""

from __future__ import annotations

from typing import Any

from modules.audio.pipeline import plugin as audio_plugin
from modules.face.analysis import plugin as face_plugin
from modules.ping.handler import plugin as ping_plugin


def iter_plugins() -> list[Any]:
    """Deterministic order; `handlers` sorts by priority."""
    return [ping_plugin, face_plugin, audio_plugin]
