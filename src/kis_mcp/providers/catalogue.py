from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import (
    PUBLIC_SCHEMA_VERSION,
    ProviderBoundary,
    ProviderDescriptor,
    ProviderKind,
    _provider_id,
    _require_bool,
    _require_enum,
    _required_text,
    _unique_text,
)
from .registry import ProviderRegistry


@dataclass(frozen=True, slots=True)
class ProviderCatalogueEntry:
    provider_id: str
    display_name: str
    provider_kind: ProviderKind
    boundary: ProviderBoundary
    enabled: bool
    authoritative_source: str
    source_revision: str
    capabilities: tuple[str, ...]
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("provider catalogue entry schema_version must be 1")
        object.__setattr__(self, "provider_id", _provider_id(self.provider_id))
        object.__setattr__(
            self,
            "display_name",
            _required_text(self.display_name, "display_name"),
        )
        _require_enum(self.provider_kind, ProviderKind, "provider_kind")
        _require_enum(self.boundary, ProviderBoundary, "boundary")
        _require_bool(self.enabled, "enabled")
        object.__setattr__(
            self,
            "authoritative_source",
            _required_text(self.authoritative_source, "authoritative_source"),
        )
        object.__setattr__(
            self,
            "source_revision",
            _required_text(self.source_revision, "source_revision"),
        )
        object.__setattr__(
            self,
            "capabilities",
            _unique_text(self.capabilities, "capability_id"),
        )

    @classmethod
    def from_descriptor(cls, descriptor: ProviderDescriptor) -> "ProviderCatalogueEntry":
        return cls(
            provider_id=descriptor.provider_id,
            display_name=descriptor.display_name,
            provider_kind=descriptor.provider_kind,
            boundary=descriptor.boundary,
            enabled=descriptor.enabled,
            authoritative_source=descriptor.authoritative_source,
            source_revision=descriptor.source_revision,
            capabilities=tuple(
                capability.capability_id for capability in descriptor.capabilities
            ),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "provider_kind": self.provider_kind.value,
            "boundary": self.boundary.value,
            "enabled": self.enabled,
            "authoritative_source": self.authoritative_source,
            "source_revision": self.source_revision,
            "capabilities": list(self.capabilities),
        }


class ProviderCatalogue:
    """Immutable provider metadata projection that never starts providers."""

    def __init__(self, entries: tuple[ProviderCatalogueEntry, ...]) -> None:
        self._entries = tuple(sorted(entries, key=lambda item: item.provider_id))

    @classmethod
    def from_registry(cls, registry: ProviderRegistry) -> "ProviderCatalogue":
        return cls(
            tuple(
                ProviderCatalogueEntry.from_descriptor(descriptor)
                for descriptor in registry.list()
            )
        )

    def entries(self) -> tuple[ProviderCatalogueEntry, ...]:
        return self._entries

    def find_by_capability(
        self,
        capability_id: str,
    ) -> tuple[ProviderCatalogueEntry, ...]:
        return tuple(
            entry for entry in self._entries if capability_id in entry.capabilities
        )


__all__ = ["ProviderCatalogue", "ProviderCatalogueEntry"]
