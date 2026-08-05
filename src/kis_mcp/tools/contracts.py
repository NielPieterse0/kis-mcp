from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, TypeAlias

PUBLIC_SCHEMA_VERSION = 1
_TOOL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class ToolKind(StrEnum):
    LOCAL_EXECUTABLE = "local_executable"
    MCP_ADAPTER = "mcp_adapter"
    LIBRARY = "library"
    PLATFORM_INTERNAL = "platform_internal"


class ToolBoundary(StrEnum):
    LOCAL_PROCESS = "local_process"
    APPROVED_EXTERNAL_SERVICE = "approved_external_service"
    LOCAL_READ_ONLY = "local_read_only"
    PLATFORM_INTERNAL = "platform_internal"


class ToolState(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _tool_id(value: str) -> str:
    normalized = _required_text(value, "tool_id")
    if not _TOOL_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "tool_id must use lower-case kebab-case beginning with a letter"
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
class ToolCapability:
    capability_id: str
    description: str
    effects: tuple[str, ...] = ()
    operation_names: tuple[str, ...] = ()
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("tool capability schema_version must be 1")
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
            "operation_names",
            _unique_text(self.operation_names, "operation_name"),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "description": self.description,
            "effects": list(self.effects),
            "operation_names": list(self.operation_names),
        }


@dataclass(frozen=True, slots=True)
class ToolReadiness:
    tool_id: str
    state: ToolState
    summary: str
    details: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("tool readiness schema_version must be 1")
        object.__setattr__(self, "tool_id", _tool_id(self.tool_id))
        _require_enum(self.state, ToolState, "state")
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        if not isinstance(self.details, Mapping):
            raise ValueError("details must be a mapping")
        normalized_details = _freeze_json_value(self.details)
        object.__setattr__(self, "details", normalized_details)

    @property
    def ready(self) -> bool:
        return self.state is ToolState.READY

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool_id": self.tool_id,
            "state": self.state.value,
            "summary": self.summary,
            "details": _json_value(self.details),
        }


ToolBuilder: TypeAlias = Callable[[], Any]
ToolReadinessProbe: TypeAlias = Callable[[], ToolReadiness]


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    tool_id: str
    display_name: str
    tool_kind: ToolKind
    boundary: ToolBoundary
    authoritative_source: str
    source_revision: str
    capabilities: tuple[ToolCapability, ...]
    builder: ToolBuilder
    readiness_probe: ToolReadinessProbe
    enabled: bool = True
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("tool descriptor schema_version must be 1")
        object.__setattr__(self, "tool_id", _tool_id(self.tool_id))
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
        _require_enum(self.tool_kind, ToolKind, "tool_kind")
        _require_enum(self.boundary, ToolBoundary, "boundary")
        _require_bool(self.enabled, "enabled")
        if not callable(self.builder):
            raise ValueError("builder must be callable")
        if not callable(self.readiness_probe):
            raise ValueError("readiness_probe must be callable")
        if any(
            not isinstance(item, ToolCapability) for item in self.capabilities
        ):
            raise ValueError("capabilities must contain ToolCapability values")
        capability_ids = [item.capability_id for item in self.capabilities]
        if len(set(capability_ids)) != len(capability_ids):
            raise ValueError("duplicate capability_id in tool descriptor")
        object.__setattr__(
            self,
            "capabilities",
            tuple(sorted(self.capabilities, key=lambda item: item.capability_id)),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool_id": self.tool_id,
            "display_name": self.display_name,
            "tool_kind": self.tool_kind.value,
            "boundary": self.boundary.value,
            "authoritative_source": self.authoritative_source,
            "source_revision": self.source_revision,
            "enabled": self.enabled,
            "capabilities": [item.to_json_dict() for item in self.capabilities],
        }


__all__ = [
    "PUBLIC_SCHEMA_VERSION",
    "ToolBoundary",
    "ToolBuilder",
    "ToolCapability",
    "ToolDescriptor",
    "ToolKind",
    "ToolReadiness",
    "ToolReadinessProbe",
    "ToolState",
]
