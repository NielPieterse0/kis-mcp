from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, TypeAlias

SCHEMA_VERSION = 1
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


class CapabilityDomain(StrEnum):
    PROVIDER = "provider"
    TOOL = "tool"
    DISCOVER = "discover"
    SKILL = "skill"
    WORKFLOW = "workflow"


class OperationEffect(StrEnum):
    READ_ONLY = "read_only"
    LOCAL_CHANGE = "local_change"
    EXTERNAL = "external"
    QUARANTINE = "quarantine"
    PROCESS = "process"


class ReadinessState(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    AUTHENTICATION_REQUIRED = "authentication_required"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    BUILD_FAILED = "build_failed"
    MOUNT_FAILED = "mount_failed"


class ExposureMode(StrEnum):
    DIRECT = "direct"
    DISCOVERABLE = "discoverable"
    STATUS_ONLY = "status_only"
    HIDDEN = "hidden"


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _identifier(value: str, label: str) -> str:
    normalized = _required_text(value, label)
    if not _ID_PATTERN.fullmatch(normalized):
        raise ValueError(f"{label} must be lower-case dotted, snake, or kebab-case")
    return normalized


def _unique_text(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(_identifier(value, label) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} values must be unique")
    return tuple(sorted(normalized))


def _json_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"value is not JSON-compatible: {type(value).__name__}")


def _freeze_mapping(value: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return MappingProxyType({str(key): _json_value(item) for key, item in value.items()})


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    capability_id: str
    optional: bool = False
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("capability requirement schema_version must be 1")
        object.__setattr__(self, "capability_id", _identifier(self.capability_id, "capability_id"))
        if not isinstance(self.optional, bool):
            raise ValueError("optional must be a boolean")

    def to_json_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "capability_id": self.capability_id, "optional": self.optional}


@dataclass(frozen=True, slots=True)
class ExposurePolicy:
    mode: ExposureMode
    priority: int = 50
    status_visible: bool = True
    explicit_request_allowed: bool = True
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("exposure policy schema_version must be 1")
        if not isinstance(self.mode, ExposureMode):
            raise ValueError("mode must be an ExposureMode value")
        if not isinstance(self.priority, int) or not 0 <= self.priority <= 100:
            raise ValueError("priority must be an integer from 0 to 100")
        if not isinstance(self.status_visible, bool) or not isinstance(self.explicit_request_allowed, bool):
            raise ValueError("exposure flags must be booleans")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode.value,
            "priority": self.priority,
            "status_visible": self.status_visible,
            "explicit_request_allowed": self.explicit_request_allowed,
        }


@dataclass(frozen=True, slots=True)
class QualityMetadata:
    schema_precision: int
    description_clarity: int
    effect_accuracy: int
    bounded_output: int
    reversibility: int
    reliability: int
    workflow_integration: int
    context_cost: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("quality metadata schema_version must be 1")
        for name in (
            "schema_precision",
            "description_clarity",
            "effect_accuracy",
            "bounded_output",
            "reversibility",
            "reliability",
            "workflow_integration",
            "context_cost",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or not 0 <= value <= 100:
                raise ValueError(f"{name} must be an integer from 0 to 100")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "schema_precision": self.schema_precision,
            "description_clarity": self.description_clarity,
            "effect_accuracy": self.effect_accuracy,
            "bounded_output": self.bounded_output,
            "reversibility": self.reversibility,
            "reliability": self.reliability,
            "workflow_integration": self.workflow_integration,
            "context_cost": self.context_cost,
        }


@dataclass(frozen=True, slots=True)
class ReadinessSnapshot:
    contribution_id: str
    state: ReadinessState
    summary: str
    details: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("readiness snapshot schema_version must be 1")
        object.__setattr__(self, "contribution_id", _identifier(self.contribution_id, "contribution_id"))
        if not isinstance(self.state, ReadinessState):
            raise ValueError("state must be a ReadinessState value")
        object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        object.__setattr__(self, "details", _freeze_mapping(self.details, "details"))

    @property
    def operational(self) -> bool:
        return self.state in {ReadinessState.READY, ReadinessState.DEGRADED}

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contribution_id": self.contribution_id,
            "state": self.state.value,
            "summary": self.summary,
            "details": _json_value(self.details),
        }


@dataclass(frozen=True, slots=True)
class OperationDescriptor:
    operation_id: str
    name: str
    description: str
    capabilities: tuple[str, ...]
    effects: tuple[OperationEffect, ...]
    dependencies: tuple[CapabilityRequirement, ...]
    exposure: ExposurePolicy
    quality: QualityMetadata
    credentials: tuple[str, ...] = ()
    approval_required: bool = False
    authentication_preflight: bool = False
    enabled: bool = True
    friction: int = 0
    tags: tuple[str, ...] = ()
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("operation descriptor schema_version must be 1")
        object.__setattr__(self, "operation_id", _identifier(self.operation_id, "operation_id"))
        object.__setattr__(self, "name", _required_text(self.name, "operation name"))
        object.__setattr__(self, "description", _required_text(self.description, "operation description"))
        object.__setattr__(self, "capabilities", _unique_text(self.capabilities, "capability"))
        if not self.capabilities:
            raise ValueError("capabilities must not be empty")
        if any(not isinstance(item, OperationEffect) for item in self.effects) or not self.effects:
            raise ValueError("effects must contain OperationEffect values")
        object.__setattr__(self, "effects", tuple(sorted(set(self.effects), key=lambda item: item.value)))
        if any(not isinstance(item, CapabilityRequirement) for item in self.dependencies):
            raise ValueError("dependencies must contain CapabilityRequirement values")
        object.__setattr__(self, "dependencies", tuple(sorted(self.dependencies, key=lambda item: item.capability_id)))
        if not isinstance(self.exposure, ExposurePolicy) or not isinstance(self.quality, QualityMetadata):
            raise ValueError("exposure and quality metadata are required")
        object.__setattr__(self, "credentials", _unique_text(self.credentials, "credential"))
        object.__setattr__(self, "tags", _unique_text(self.tags, "tag"))
        if not isinstance(self.approval_required, bool) or not isinstance(self.authentication_preflight, bool) or not isinstance(self.enabled, bool):
            raise ValueError("operation flags must be booleans")
        if not isinstance(self.friction, int) or not 0 <= self.friction <= 100:
            raise ValueError("friction must be an integer from 0 to 100")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation_id": self.operation_id,
            "name": self.name,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "effects": [item.value for item in self.effects],
            "dependencies": [item.to_json_dict() for item in self.dependencies],
            "exposure": self.exposure.to_json_dict(),
            "quality": self.quality.to_json_dict(),
            "credentials": list(self.credentials),
            "approval_required": self.approval_required,
            "authentication_preflight": self.authentication_preflight,
            "enabled": self.enabled,
            "friction": self.friction,
            "tags": list(self.tags),
        }


ReadinessProbe: TypeAlias = Callable[[], ReadinessSnapshot]


@dataclass(frozen=True, slots=True)
class CapabilityContribution:
    contribution_id: str
    domain: CapabilityDomain
    category: str
    capabilities: tuple[str, ...]
    operations: tuple[OperationDescriptor, ...]
    dependencies: tuple[CapabilityRequirement, ...]
    effects: tuple[OperationEffect, ...]
    readiness_probe: ReadinessProbe
    exposure: ExposurePolicy
    quality: QualityMetadata
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("capability contribution schema_version must be 1")
        object.__setattr__(self, "contribution_id", _identifier(self.contribution_id, "contribution_id"))
        if not isinstance(self.domain, CapabilityDomain):
            raise ValueError("domain must be a CapabilityDomain value")
        category = _identifier(self.category, "category")
        if category == "uncategorized":
            raise ValueError("category must not be uncategorized")
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "capabilities", _unique_text(self.capabilities, "capability"))
        if not self.capabilities:
            raise ValueError("capabilities must not be empty")
        if any(not isinstance(item, OperationDescriptor) for item in self.operations):
            raise ValueError("operations must contain OperationDescriptor values")
        operation_ids = [item.operation_id for item in self.operations]
        operation_names = [item.name for item in self.operations]
        if len(set(operation_ids)) != len(operation_ids) or len(set(operation_names)) != len(operation_names):
            raise ValueError("operations must have unique IDs and names")
        object.__setattr__(self, "operations", tuple(sorted(self.operations, key=lambda item: item.operation_id)))
        if any(not isinstance(item, CapabilityRequirement) for item in self.dependencies):
            raise ValueError("dependencies must contain CapabilityRequirement values")
        object.__setattr__(self, "dependencies", tuple(sorted(self.dependencies, key=lambda item: item.capability_id)))
        if any(not isinstance(item, OperationEffect) for item in self.effects) or not self.effects:
            raise ValueError("effects must contain OperationEffect values")
        object.__setattr__(self, "effects", tuple(sorted(set(self.effects), key=lambda item: item.value)))
        if not callable(self.readiness_probe):
            raise ValueError("readiness_probe must be callable")
        if not isinstance(self.exposure, ExposurePolicy) or not isinstance(self.quality, QualityMetadata):
            raise ValueError("exposure and quality metadata are required")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contribution_id": self.contribution_id,
            "domain": self.domain.value,
            "category": self.category,
            "capabilities": list(self.capabilities),
            "operations": [item.to_json_dict() for item in self.operations],
            "dependencies": [item.to_json_dict() for item in self.dependencies],
            "effects": [item.value for item in self.effects],
            "exposure": self.exposure.to_json_dict(),
            "quality": self.quality.to_json_dict(),
        }


@dataclass(frozen=True, slots=True)
class WorkflowDescriptor:
    workflow_id: str
    title: str
    description: str
    capabilities: tuple[str, ...]
    required_steps: tuple[str, ...]
    completion_criteria: tuple[str, ...]
    activation_terms: tuple[str, ...]
    effects: tuple[OperationEffect, ...]
    exposure: ExposurePolicy
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("workflow descriptor schema_version must be 1")
        object.__setattr__(self, "workflow_id", _identifier(self.workflow_id, "workflow_id"))
        object.__setattr__(self, "title", _required_text(self.title, "workflow title"))
        object.__setattr__(self, "description", _required_text(self.description, "workflow description"))
        object.__setattr__(self, "capabilities", _unique_text(self.capabilities, "capability"))
        object.__setattr__(self, "required_steps", _unique_text(self.required_steps, "required_step"))
        object.__setattr__(self, "completion_criteria", tuple(sorted(_required_text(item, "completion criterion") for item in self.completion_criteria)))
        object.__setattr__(self, "activation_terms", tuple(sorted(_required_text(item, "activation term").casefold() for item in self.activation_terms)))
        if not self.capabilities or not self.required_steps or not self.completion_criteria or not self.activation_terms:
            raise ValueError("workflow metadata must be complete")
        if any(not isinstance(item, OperationEffect) for item in self.effects) or not self.effects:
            raise ValueError("effects must contain OperationEffect values")
        object.__setattr__(self, "effects", tuple(sorted(set(self.effects), key=lambda item: item.value)))
        if not isinstance(self.exposure, ExposurePolicy):
            raise ValueError("exposure must be an ExposurePolicy")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "workflow_id": self.workflow_id,
            "title": self.title,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "required_steps": list(self.required_steps),
            "completion_criteria": list(self.completion_criteria),
            "activation_terms": list(self.activation_terms),
            "effects": [item.value for item in self.effects],
            "exposure": self.exposure.to_json_dict(),
        }


__all__ = [
    "SCHEMA_VERSION",
    "CapabilityContribution",
    "CapabilityDomain",
    "CapabilityRequirement",
    "ExposureMode",
    "ExposurePolicy",
    "OperationDescriptor",
    "OperationEffect",
    "QualityMetadata",
    "ReadinessProbe",
    "ReadinessSnapshot",
    "ReadinessState",
    "WorkflowDescriptor",
]
