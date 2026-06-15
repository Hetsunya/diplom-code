"""Shared typing for WS analysis workers loaded from `modules/`."""

from __future__ import annotations

from typing import Any, Protocol, TypedDict


class ModuleMetadata(TypedDict, total=False):
    """Optional descriptor for logging / observability (not required on wire)."""

    module: str
    provider: str
    model: str
    version: str


class AnalysisPlugin(Protocol):
    """Contract for a single WS message handler (same as legacy plugins)."""

    name: str
    priority: int

    def can_handle(self, msg: dict[str, Any]) -> bool: ...

    async def process(self, msg: dict[str, Any], ws: Any) -> None: ...

    def metadata(self) -> ModuleMetadata: ...
