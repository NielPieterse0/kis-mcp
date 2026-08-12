from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backend import ProjectField, ProjectFieldKind
from .contracts import PUBLIC_SCHEMA_VERSION

_MANIFEST_KEYS = frozenset({"schema_version", "project_id", "fields", "views"})
_FIELD_KEYS = frozenset({"name", "type", "options"})
_VIEW_KEYS = frozenset({"name", "purpose"})


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _exact_keys(value: dict[str, Any], expected: frozenset[str], label: str) -> None:
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown or missing:
        raise ValueError(f"{label} keys must be exactly {', '.join(sorted(expected))}")

@dataclass(frozen=True, slots=True)
class ProjectFieldSpec:
    name: str
    kind: ProjectFieldKind
    options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "field name"))
        if not isinstance(self.kind, ProjectFieldKind):
            raise ValueError("field kind must be a ProjectFieldKind value")
        normalized = tuple(_text(value, "field option") for value in self.options)
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError("field options must be unique")
        if self.kind is not ProjectFieldKind.SINGLE_SELECT and normalized:
            raise ValueError("options are allowed only for single_select fields")
        object.__setattr__(self, "options", normalized)

    def to_json_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.kind.value, "options": list(self.options)}


@dataclass(frozen=True, slots=True)
class ProjectViewSpec:
    name: str
    purpose: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "view name"))
        object.__setattr__(self, "purpose", _text(self.purpose, "view purpose"))

    def to_json_dict(self) -> dict[str, str]:
        return {"name": self.name, "purpose": self.purpose}


@dataclass(frozen=True, slots=True)
class ProjectSchemaManifest:
    project_id: str
    fields: tuple[ProjectFieldSpec, ...]
    views: tuple[ProjectViewSpec, ...]
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("project schema manifest schema_version must be 1")
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        field_names = [item.name.casefold() for item in self.fields]
        view_names = [item.name.casefold() for item in self.views]
        if len(set(field_names)) != len(field_names):
            raise ValueError("project schema fields must be unique")
        if len(set(view_names)) != len(view_names):
            raise ValueError("project schema views must be unique")

    def field(self, name: str) -> ProjectFieldSpec:
        normalized = _text(name, "field name").casefold()
        for item in self.fields:
            if item.name.casefold() == normalized:
                return item
        raise KeyError(name)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "fields": [item.to_json_dict() for item in self.fields],
            "views": [item.to_json_dict() for item in self.views],
        }

@dataclass(frozen=True, slots=True)
class ProjectSchemaStatus:
    project_id: str
    fields_ready: bool
    views_ready: bool | None
    missing_fields: tuple[str, ...] = ()
    type_mismatches: tuple[str, ...] = ()
    missing_options: tuple[str, ...] = ()
    unverified_views: tuple[str, ...] = ()
    schema_version: int = PUBLIC_SCHEMA_VERSION

    @property
    def ready(self) -> bool:
        return self.fields_ready and self.views_ready is True

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "ready": self.ready,
            "fields_ready": self.fields_ready,
            "views_ready": self.views_ready,
            "missing_fields": list(self.missing_fields),
            "type_mismatches": list(self.type_mismatches),
            "missing_options": list(self.missing_options),
            "unverified_views": list(self.unverified_views),
        }


def _field_spec(value: Any) -> ProjectFieldSpec:
    item = _object(value, "project field spec")
    _exact_keys(item, _FIELD_KEYS, "project field spec")
    options = item["options"]
    if not isinstance(options, list):
        raise ValueError("project field options must be an array")
    return ProjectFieldSpec(
        name=item["name"],
        kind=ProjectFieldKind(item["type"]),
        options=tuple(options),
    )

def _view_spec(value: Any) -> ProjectViewSpec:
    item = _object(value, "project view spec")
    _exact_keys(item, _VIEW_KEYS, "project view spec")
    return ProjectViewSpec(name=item["name"], purpose=item["purpose"])


def load_project_schema_manifest(path: Path | None = None) -> ProjectSchemaManifest:
    target = path or (
        Path(__file__).resolve().parents[3]
        / "settings"
        / "work-management"
        / "github-project-schema.json"
    )
    document = json.loads(target.read_text(encoding="utf-8"))
    root = _object(document, "project schema manifest")
    _exact_keys(root, _MANIFEST_KEYS, "project schema manifest")
    if root["schema_version"] != PUBLIC_SCHEMA_VERSION:
        raise ValueError("project schema manifest schema_version must be 1")
    fields = root["fields"]
    views = root["views"]
    if not isinstance(fields, list) or not isinstance(views, list):
        raise ValueError("project schema fields and views must be arrays")
    return ProjectSchemaManifest(
        schema_version=root["schema_version"],
        project_id=root["project_id"],
        fields=tuple(_field_spec(item) for item in fields),
        views=tuple(_view_spec(item) for item in views),
    )

def compare_project_schema(
    manifest: ProjectSchemaManifest,
    observed_fields: tuple[ProjectField, ...],
    *,
    views_observed: tuple[str, ...] | None,
) -> ProjectSchemaStatus:
    if not isinstance(manifest, ProjectSchemaManifest):
        raise ValueError("manifest must be a ProjectSchemaManifest")
    if any(not isinstance(item, ProjectField) for item in observed_fields):
        raise ValueError("observed_fields must contain ProjectField values")
    observed = {item.name.casefold(): item for item in observed_fields}
    missing_fields: list[str] = []
    mismatches: list[str] = []
    missing_options: list[str] = []
    for expected in manifest.fields:
        actual = observed.get(expected.name.casefold())
        if actual is None:
            missing_fields.append(expected.name)
            continue
        if actual.kind is not expected.kind:
            mismatches.append(f"{expected.name}:{actual.kind.value}->{expected.kind.value}")
            continue
        available_options = {item.name.casefold() for item in actual.options}
        for option in expected.options:
            if option.casefold() not in available_options:
                missing_options.append(f"{expected.name}:{option}")

    if views_observed is None:
        views_ready: bool | None = None
        unverified_views = tuple(item.name for item in manifest.views)
    else:
        observed_views = {value.casefold() for value in views_observed}
        unverified_views = tuple(
            item.name for item in manifest.views if item.name.casefold() not in observed_views
        )
        views_ready = not unverified_views

    fields_ready = not (missing_fields or mismatches or missing_options)
    return ProjectSchemaStatus(
        project_id=manifest.project_id,
        fields_ready=fields_ready,
        views_ready=views_ready,
        missing_fields=tuple(sorted(missing_fields, key=str.casefold)),
        type_mismatches=tuple(sorted(mismatches, key=str.casefold)),
        missing_options=tuple(sorted(missing_options, key=str.casefold)),
        unverified_views=tuple(unverified_views),
    )


__all__ = [
    "ProjectFieldSpec",
    "ProjectSchemaManifest",
    "ProjectSchemaStatus",
    "ProjectViewSpec",
    "compare_project_schema",
    "load_project_schema_manifest",
]
