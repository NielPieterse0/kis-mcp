from __future__ import annotations

from typing import Any

from .catalogue import ProviderCatalogue, ProviderCatalogueEntry
from .health import ProviderHealthSummary, aggregate_provider_health
from .registry import ProviderRegistry


class ProviderService:
    """Thin provider-neutral facade over registry, catalogue, health, and build."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    def catalogue(self) -> ProviderCatalogue:
        return ProviderCatalogue.from_registry(self._registry)

    def find_by_capability(
        self,
        capability_id: str,
    ) -> tuple[ProviderCatalogueEntry, ...]:
        return self.catalogue().find_by_capability(capability_id)

    def health(self) -> ProviderHealthSummary:
        return aggregate_provider_health(self._registry.list())

    def build(self, provider_id: str) -> Any:
        return self._registry.get(provider_id).builder()


__all__ = ["ProviderService"]
