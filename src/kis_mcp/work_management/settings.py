from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from kis_mcp.projects import ProjectRegistry, load_project_registry_settings
from kis_mcp.projects.contracts import normalize_github_repository, normalize_windows_root

from .backend import ProjectOwnerType
from .contracts import ManagedProject, PUBLIC_SCHEMA_VERSION

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_SETTING_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "enabled",
        "portfolio_id",
        "managed_projects",
        "backend_bindings",
        "features",
        "automation",
        "gates",
        "evidence",
    }
)
_PROJECT_KEYS = frozenset(
    {
        "project_id",
        "local_root",
        "repository",
        "backend_binding",
        "display_name",
    }
)
_BINDING_KEYS = frozenset(
    {"binding_id", "provider", "owner", "owner_type", "project_number"}
)
_EVIDENCE_KEYS = frozenset({"max_file_bytes", "max_total_bytes"})


class FeatureMode(StrEnum):
    DISABLED = "disabled"
    READ_ONLY = "read_only"
    ENABLED = "enabled"


class GateMode(StrEnum):
    OFF = "off"
    ADVISORY = "advisory"
    REQUIRED = "required"


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _identifier(value: Any, label: str) -> str:
    normalized = _required_text(value, label)
    if _IDENTIFIER.fullmatch(normalized) is None:
        raise ValueError(f"{label} must use lower-case kebab-case")
    return normalized


def _setting_name(value: Any, label: str) -> str:
    normalized = _required_text(value, label)
    if _SETTING_NAME.fullmatch(normalized) is None:
        raise ValueError(f"{label} must use lower-case snake_case")
    return normalized


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _exact_keys(value: dict[str, Any], expected: frozenset[str], label: str) -> None:
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise ValueError(f"unknown {label} keys: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"missing {label} keys: {', '.join(missing)}")


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class BackendBindingSettings:
    binding_id: str
    provider: str
    owner: str
    owner_type: ProjectOwnerType
    project_number: int | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("backend binding schema_version must be 1")
        object.__setattr__(self, "binding_id", _identifier(self.binding_id, "binding_id"))
        object.__setattr__(self, "provider", _identifier(self.provider, "provider"))
        object.__setattr__(self, "owner", _required_text(self.owner, "owner"))
        if not isinstance(self.owner_type, ProjectOwnerType):
            raise ValueError("owner_type must be a ProjectOwnerType value")
        if self.project_number is not None:
            object.__setattr__(
                self,
                "project_number",
                _positive_int(self.project_number, "project_number"),
            )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "binding_id": self.binding_id,
            "provider": self.provider,
            "owner": self.owner,
            "owner_type": self.owner_type.value,
            "project_number": self.project_number,
        }


@dataclass(frozen=True, slots=True)
class EvidenceSettings:
    max_file_bytes: int = 1_048_576
    max_total_bytes: int = 4_194_304

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_file_bytes",
            _positive_int(self.max_file_bytes, "max_file_bytes"),
        )
        object.__setattr__(
            self,
            "max_total_bytes",
            _positive_int(self.max_total_bytes, "max_total_bytes"),
        )
        if self.max_total_bytes < self.max_file_bytes:
            raise ValueError("max_total_bytes must be at least max_file_bytes")


@dataclass(frozen=True, slots=True)
class WorkManagementSettings:
    enabled: bool
    portfolio_id: str
    managed_projects: tuple[ManagedProject, ...]
    backend_bindings: tuple[BackendBindingSettings, ...]
    features: tuple[tuple[str, FeatureMode], ...]
    automation: tuple[tuple[str, bool], ...]
    gates: tuple[tuple[str, GateMode], ...]
    evidence: EvidenceSettings
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("work-management settings schema_version must be 1")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        object.__setattr__(self, "portfolio_id", _identifier(self.portfolio_id, "portfolio_id"))
        if any(not isinstance(item, ManagedProject) for item in self.managed_projects):
            raise ValueError("managed_projects must contain ManagedProject values")
        if any(not isinstance(item, BackendBindingSettings) for item in self.backend_bindings):
            raise ValueError("backend_bindings must contain BackendBindingSettings values")
        project_ids = [item.project_id for item in self.managed_projects]
        binding_ids = [item.binding_id for item in self.backend_bindings]
        if len(set(project_ids)) != len(project_ids):
            raise ValueError("managed project_id values must be unique")
        if len(set(binding_ids)) != len(binding_ids):
            raise ValueError("backend binding_id values must be unique")
        available = set(binding_ids)
        missing = sorted(
            {item.backend_binding for item in self.managed_projects} - available
        )
        if missing:
            raise ValueError(
                "managed project references missing backend binding: "
                + ", ".join(missing)
            )
        object.__setattr__(
            self,
            "managed_projects",
            tuple(sorted(self.managed_projects, key=lambda item: item.project_id)),
        )
        object.__setattr__(
            self,
            "backend_bindings",
            tuple(sorted(self.backend_bindings, key=lambda item: item.binding_id)),
        )
        feature_names = [name for name, _mode in self.features]
        automation_names = [name for name, _enabled in self.automation]
        gate_names = [name for name, _mode in self.gates]
        if len(set(feature_names)) != len(feature_names):
            raise ValueError("feature names must be unique")
        if len(set(automation_names)) != len(automation_names):
            raise ValueError("automation names must be unique")
        if len(set(gate_names)) != len(gate_names):
            raise ValueError("gate names must be unique")
        for name, mode in self.features:
            _setting_name(name, "feature name")
            if not isinstance(mode, FeatureMode):
                raise ValueError("feature mode must be a FeatureMode value")
        for name, enabled in self.automation:
            _setting_name(name, "automation name")
            if not isinstance(enabled, bool):
                raise ValueError("automation values must be booleans")
        for name, mode in self.gates:
            _setting_name(name, "gate name")
            if not isinstance(mode, GateMode):
                raise ValueError("gate mode must be a GateMode value")
        object.__setattr__(self, "features", tuple(sorted(self.features)))
        object.__setattr__(self, "automation", tuple(sorted(self.automation)))
        object.__setattr__(self, "gates", tuple(sorted(self.gates)))
        if not isinstance(self.evidence, EvidenceSettings):
            raise ValueError("evidence must be EvidenceSettings")

    def project(self, project_id: str) -> ManagedProject:
        normalized = _identifier(project_id, "project_id")
        for project in self.managed_projects:
            if project.project_id == normalized:
                return project
        raise KeyError(normalized)

    def binding(self, binding_id: str) -> BackendBindingSettings:
        normalized = _identifier(binding_id, "binding_id")
        for binding in self.backend_bindings:
            if binding.binding_id == normalized:
                return binding
        raise KeyError(normalized)

    def feature_mode(self, name: str) -> FeatureMode:
        normalized = _setting_name(name, "feature name")
        return dict(self.features).get(normalized, FeatureMode.DISABLED)

    def gate_mode(self, name: str) -> GateMode:
        normalized = _setting_name(name, "gate name")
        return dict(self.gates).get(normalized, GateMode.OFF)

    def automation_enabled(self, name: str) -> bool:
        normalized = _setting_name(name, "automation name")
        return dict(self.automation).get(normalized, False)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "portfolio_id": self.portfolio_id,
            "managed_projects": [item.to_json_dict() for item in self.managed_projects],
            "backend_bindings": [item.to_json_dict() for item in self.backend_bindings],
            "features": {name: mode.value for name, mode in self.features},
            "automation": dict(self.automation),
            "gates": {name: mode.value for name, mode in self.gates},
            "evidence": {
                "max_file_bytes": self.evidence.max_file_bytes,
                "max_total_bytes": self.evidence.max_total_bytes,
            },
        }


def _managed_project(value: Any) -> ManagedProject:
    item = _object(value, "managed project")
    _exact_keys(item, _PROJECT_KEYS, "managed project")
    return ManagedProject(
        project_id=item["project_id"],
        local_root=item["local_root"],
        repository=item["repository"],
        backend_binding=item["backend_binding"],
        display_name=item["display_name"],
    )


def _backend_binding(value: Any) -> BackendBindingSettings:
    item = _object(value, "backend binding")
    _exact_keys(item, _BINDING_KEYS, "backend binding")
    try:
        owner_type = ProjectOwnerType(item["owner_type"])
    except (TypeError, ValueError) as exc:
        raise ValueError("owner_type must be a ProjectOwnerType value") from exc
    return BackendBindingSettings(
        binding_id=item["binding_id"],
        provider=item["provider"],
        owner=item["owner"],
        owner_type=owner_type,
        project_number=item["project_number"],
    )


def _enum_mapping(
    value: Any,
    *,
    label: str,
    enum_type: type[StrEnum],
) -> tuple[tuple[str, StrEnum], ...]:
    mapping = _object(value, label)
    result: list[tuple[str, StrEnum]] = []
    for raw_name, raw_mode in mapping.items():
        name = _setting_name(raw_name, f"{label} name")
        try:
            mode = enum_type(raw_mode)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{label} value for {name} must be a {enum_type.__name__} value"
            ) from exc
        result.append((name, mode))
    return tuple(result)


def _registry_project_resource(project: Any) -> Any | None:
    if project.github is None or not project.github.projects:
        return None
    named = [
        resource
        for resource in project.github.projects
        if resource.binding_id == "work-management"
    ]
    if len(named) == 1:
        return named[0]
    if len(project.github.projects) == 1:
        return project.github.projects[0]
    raise ValueError(
        f"project registry has ambiguous work-management binding: {project.project_id}"
    )


def _bridge_project_registry(
    settings: WorkManagementSettings,
    registry: ProjectRegistry,
) -> WorkManagementSettings:
    bridged_projects: list[ManagedProject] = []
    binding_resources: dict[str, Any] = {}

    for managed in settings.managed_projects:
        try:
            registered = registry.project(managed.project_id)
        except KeyError:
            bridged_projects.append(managed)
            continue
        if registered.github is None:
            raise ValueError(
                f"managed project conflicts with project registry: {managed.project_id} has no GitHub binding"
            )
        if normalize_windows_root(managed.local_root).casefold() != registered.local_root.casefold():
            raise ValueError(
                f"managed project local_root conflicts with project registry: {managed.project_id}"
            )
        if normalize_github_repository(managed.repository) != registered.github.repository:
            raise ValueError(
                f"managed project repository conflicts with project registry: {managed.project_id}"
            )
        bridged_projects.append(
            ManagedProject(
                project_id=managed.project_id,
                local_root=registered.local_root,
                repository=registered.github.repository,
                backend_binding=managed.backend_binding,
                display_name=registered.display_name,
            )
        )
        resource = _registry_project_resource(registered)
        if resource is None:
            continue
        previous = binding_resources.get(managed.backend_binding)
        coordinate = (resource.owner.casefold(), resource.owner_type, resource.project_number)
        if previous is not None:
            previous_coordinate = (
                previous.owner.casefold(),
                previous.owner_type,
                previous.project_number,
            )
            if previous_coordinate != coordinate:
                raise ValueError(
                    f"backend binding conflicts across project registry: {managed.backend_binding}"
                )
        binding_resources[managed.backend_binding] = resource

    bridged_bindings = []
    for binding in settings.backend_bindings:
        resource = binding_resources.get(binding.binding_id)
        if resource is None:
            bridged_bindings.append(binding)
            continue
        bridged_bindings.append(
            BackendBindingSettings(
                binding_id=binding.binding_id,
                provider=binding.provider,
                owner=resource.owner,
                owner_type=ProjectOwnerType(resource.owner_type),
                project_number=resource.project_number,
            )
        )

    return WorkManagementSettings(
        enabled=settings.enabled,
        portfolio_id=settings.portfolio_id,
        managed_projects=tuple(bridged_projects),
        backend_bindings=tuple(bridged_bindings),
        features=settings.features,
        automation=settings.automation,
        gates=settings.gates,
        evidence=settings.evidence,
        schema_version=settings.schema_version,
    )


def load_work_management_settings(
    path: Path | None = None,
    *,
    project_registry: ProjectRegistry | None = None,
) -> WorkManagementSettings:
    target = path or (
        Path(__file__).resolve().parents[3]
        / "settings"
        / "work-management"
        / "github-projects.settings.json"
    )
    document = json.loads(target.read_text(encoding="utf-8"))
    root = _object(document, "settings")
    _exact_keys(root, _TOP_LEVEL_KEYS, "settings")
    if root["schema_version"] != PUBLIC_SCHEMA_VERSION:
        raise ValueError("schema_version must be 1")
    managed = root["managed_projects"]
    bindings = root["backend_bindings"]
    if not isinstance(managed, list):
        raise ValueError("managed_projects must be an array")
    if not isinstance(bindings, list):
        raise ValueError("backend_bindings must be an array")
    automation = _object(root["automation"], "automation")
    normalized_automation: list[tuple[str, bool]] = []
    for raw_name, enabled in automation.items():
        name = _setting_name(raw_name, "automation name")
        if not isinstance(enabled, bool):
            raise ValueError(f"automation value for {name} must be a boolean")
        normalized_automation.append((name, enabled))
    evidence = _object(root["evidence"], "evidence")
    _exact_keys(evidence, _EVIDENCE_KEYS, "evidence")
    settings = WorkManagementSettings(
        schema_version=root["schema_version"],
        enabled=root["enabled"],
        portfolio_id=root["portfolio_id"],
        managed_projects=tuple(_managed_project(item) for item in managed),
        backend_bindings=tuple(_backend_binding(item) for item in bindings),
        features=tuple(
            (name, FeatureMode(mode))
            for name, mode in _enum_mapping(
                root["features"], label="features", enum_type=FeatureMode
            )
        ),
        automation=tuple(normalized_automation),
        gates=tuple(
            (name, GateMode(mode))
            for name, mode in _enum_mapping(
                root["gates"], label="gates", enum_type=GateMode
            )
        ),
        evidence=EvidenceSettings(
            max_file_bytes=evidence["max_file_bytes"],
            max_total_bytes=evidence["max_total_bytes"],
        ),
    )
    registry = project_registry
    if registry is None and path is None:
        registry = load_project_registry_settings()
    return settings if registry is None else _bridge_project_registry(settings, registry)


__all__ = [
    "BackendBindingSettings",
    "EvidenceSettings",
    "FeatureMode",
    "GateMode",
    "WorkManagementSettings",
    "load_work_management_settings",
]
