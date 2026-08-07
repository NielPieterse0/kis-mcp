from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, TypeAlias

PUBLIC_SCHEMA_VERSION = 1
_PROVIDER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class ProviderKind(StrEnum):
    CONNECTOR = "connector"
    LOCAL_BACKEND = "local_backend"
    SEMANTIC = "semantic"
    PLATFORM = "platform"


class ProviderBoundary(StrEnum):
    WORK_BACKEND = "work_backend"
    APPROVED_EXTERNAL_CONNECTOR = "approved_external_connector"
    LOCAL_READ_ONLY = "local_read_only"
    PLATFORM_INTERNAL = "platform_internal"


class ProviderState(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _provider_id(value: str) -> str:
    normalized = _required_text(value, "provider_id")
    if not _PROVIDER_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "provider_id must use lower-case kebab-case beginning with a letter"
        )
    return normalized


def _require_enum(value: Any, enum_type: type[StrEnum], label: str) -> StrEnum:
    if not isinstance(value, enum_type):
        raise ValueError(f"{label} must be a {enum_type.__name__} value")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _unique_text(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(_required_text(value, label) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} values must be unique")
    return tuple(sorted(normalized))


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if hasattr(value, "to_json_dict"):
        return _freeze_json_value(value.to_json_dict())
    if isinstance(value, Mapping):
        normalized = {
            str(key): _freeze_json_value(item) for key, item in value.items()
        }
        return MappingProxyType(normalized)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_json_value(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"value is not JSON-compatible: {type(value).__name__}")


def _json_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if hasattr(value, "to_json_dict"):
        return _json_value(value.to_json_dict())
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"value is not JSON-compatible: {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    capability_id: str
    description: str
    effects: tuple[str, ...] = ()
    tool_names: tuple[str, ...] = ()
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("provider capability schema_version must be 1")
        object.__setattr__(
            self,
            "capability_id",
            _required_text(self.capability_id, "capability_id"),
        )
        object.__setattr__(
            self,
            "description",
            _required_text(self.description, "capability description"),
        )
        object.__setattr__(self, "effects", _unique_text(self.effects, "effect"))
        object.__setattr__(
            self,
            "tool_names",
            _unique_text(self.tool_names, "tool_name"),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "description": self.description,
            "effects": list(self.effects),
            "tool_names": list(self.tool_names),
        }


@dataclass(frozen=True, slots=True)
class ProviderReadiness:
    provider_id: str
    state: ProviderState
    summary: str
    details: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("provider readiness schema_version must be 1")
        object.__setattr__(self, "provider_id", _provider_id(self.provider_id))
        _require_enum(self.state, ProviderState, "state")
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        if not isinstance(self.details, Mapping):
            raise ValueError("details must be a mapping")
        normalized_details = _freeze_json_value(self.details)
        object.__setattr__(self, "details", normalized_details)

    @property
    def ready(self) -> bool:
        return self.state is ProviderState.READY

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "state": self.state.value,
            "summary": self.summary,
            "details": _json_value(self.details),
        }


ProviderBuilder: TypeAlias = Callable[[], Any]
ProviderReadinessProbe: TypeAlias = Callable[[], ProviderReadiness]
ProviderRuntimeToolsProbe: TypeAlias = Callable[[], Sequence[Any]]


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    display_name: str
    provider_kind: ProviderKind
    boundary: ProviderBoundary
    authoritative_source: str
    source_revision: str
    capabilities: tuple[ProviderCapability, ...]
    builder: ProviderBuilder
    readiness_probe: ProviderReadinessProbe
    runtime_tools_probe: ProviderRuntimeToolsProbe | None = None
    enabled: bool = True
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("provider descriptor schema_version must be 1")
        object.__setattr__(self, "provider_id", _provider_id(self.provider_id))
        object.__setattr__(
            self,
            "display_name",
            _required_text(self.display_name, "display_name"),
        )
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
        _require_enum(self.provider_kind, ProviderKind, "provider_kind")
        _require_enum(self.boundary, ProviderBoundary, "boundary")
        _require_bool(self.enabled, "enabled")
        if not callable(self.builder):
            raise ValueError("builder must be callable")
        if not callable(self.readiness_probe):
            raise ValueError("readiness_probe must be callable")
        if self.runtime_tools_probe is not None and not callable(
            self.runtime_tools_probe
        ):
            raise ValueError("runtime_tools_probe must be callable when provided")
        if any(
            not isinstance(item, ProviderCapability) for item in self.capabilities
        ):
            raise ValueError("capabilities must contain ProviderCapability values")
        capability_ids = [item.capability_id for item in self.capabilities]
        if len(set(capability_ids)) != len(capability_ids):
            raise ValueError("duplicate capability_id in provider descriptor")
        object.__setattr__(
            self,
            "capabilities",
            tuple(sorted(self.capabilities, key=lambda item: item.capability_id)),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "provider_kind": self.provider_kind.value,
            "boundary": self.boundary.value,
            "authoritative_source": self.authoritative_source,
            "source_revision": self.source_revision,
            "enabled": self.enabled,
            "capabilities": [item.to_json_dict() for item in self.capabilities],
        }


__all__ = [
    "PUBLIC_SCHEMA_VERSION",
    "ProviderBoundary",
    "ProviderBuilder",
    "ProviderCapability",
    "ProviderDescriptor",
    "ProviderKind",
    "ProviderReadiness",
    "ProviderReadinessProbe",
    "ProviderRuntimeToolsProbe",
    "ProviderState",
]
