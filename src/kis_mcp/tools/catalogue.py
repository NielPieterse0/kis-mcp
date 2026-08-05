from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import (
    PUBLIC_SCHEMA_VERSION,
    ToolBoundary,
    ToolDescriptor,
    ToolKind,
    _tool_id,
    _require_bool,
    _require_enum,
    _required_text,
    _unique_text,
)
from .registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class ToolCatalogueEntry:
    tool_id: str
    display_name: str
    tool_kind: ToolKind
    boundary: ToolBoundary
    enabled: bool
    authoritative_source: str
    source_revision: str
    capabilities: tuple[str, ...]
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("tool catalogue entry schema_version must be 1")
        object.__setattr__(self, "tool_id", _tool_id(self.tool_id))
        object.__setattr__(
            self,
            "display_name",
            _required_text(self.display_name, "display_name"),
        )
        _require_enum(self.tool_kind, ToolKind, "tool_kind")
        _require_enum(self.boundary, ToolBoundary, "boundary")
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
    def from_descriptor(cls, descriptor: ToolDescriptor) -> "ToolCatalogueEntry":
        return cls(
            tool_id=descriptor.tool_id,
            display_name=descriptor.display_name,
            tool_kind=descriptor.tool_kind,
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
            "tool_id": self.tool_id,
            "display_name": self.display_name,
            "tool_kind": self.tool_kind.value,
            "boundary": self.boundary.value,
            "enabled": self.enabled,
            "authoritative_source": self.authoritative_source,
            "source_revision": self.source_revision,
            "capabilities": list(self.capabilities),
        }


class ToolCatalogue:
    """Immutable tool metadata projection that never starts tools."""

    def __init__(self, entries: tuple[ToolCatalogueEntry, ...]) -> None:
        self._entries = tuple(sorted(entries, key=lambda item: item.tool_id))

    @classmethod
    def from_registry(cls, registry: ToolRegistry) -> "ToolCatalogue":
        return cls(
            tuple(
                ToolCatalogueEntry.from_descriptor(descriptor)
                for descriptor in registry.list()
            )
        )

    def entries(self) -> tuple[ToolCatalogueEntry, ...]:
        return self._entries

    def find_by_capability(
        self,
        capability_id: str,
    ) -> tuple[ToolCatalogueEntry, ...]:
        return tuple(
            entry for entry in self._entries if capability_id in entry.capabilities
        )


__all__ = ["ToolCatalogue", "ToolCatalogueEntry"]
