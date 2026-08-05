from __future__ import annotations

from typing import Any

from .catalogue import ToolCatalogue, ToolCatalogueEntry
from .health import ToolHealthSummary, aggregate_tool_health
from .registry import ToolRegistry


class ToolService:
    """Thin tool-neutral facade over registry, catalogue, health, and build."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def catalogue(self) -> ToolCatalogue:
        return ToolCatalogue.from_registry(self._registry)

    def find_by_capability(
        self,
        capability_id: str,
    ) -> tuple[ToolCatalogueEntry, ...]:
        return self.catalogue().find_by_capability(capability_id)

    def health(self) -> ToolHealthSummary:
        return aggregate_tool_health(self._registry.list())

    def build(self, tool_id: str) -> Any:
        return self._registry.get(tool_id).builder()


__all__ = ["ToolService"]
