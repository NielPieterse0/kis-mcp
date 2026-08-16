from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backend import ProjectField, ProjectFieldKind
from .contracts import PUBLIC_SCHEMA_VERSION

_MANIFEST_KEYS = frozenset({"schema_version", "portfolio_id", "fields", "views"})
_FIELD_KEYS = frozenset({"name", "type", "options"})
_VIEW_KEYS = frozenset(
    {
        "name",
        "purpose",
        "layout",
        "filter",
        "visible_fields",
        "sort_by",
        "group_by",
        "vertical_group_by",
    }
)


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
        return {
            "name": self.name,
            "type": self.kind.value,
            "options": list(self.options),
        }


@dataclass(frozen=True, slots=True)
class ProjectViewSpec:
    name: str
    purpose: str
    layout: str = "table"
    filter: str = ""
    visible_fields: tuple[str, ...] = ()
    sort_by: tuple[tuple[str, str], ...] = ()
    group_by: tuple[str, ...] = ()
    vertical_group_by: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "view name"))
        object.__setattr__(self, "purpose", _text(self.purpose, "view purpose"))
        layout = _text(self.layout, "view layout").casefold()
        if layout not in {"table", "board", "roadmap"}:
            raise ValueError("view layout must be table, board, or roadmap")
        object.__setattr__(self, "layout", layout)
        normalized_filter = self.filter.strip() if isinstance(self.filter, str) else None
        if normalized_filter is None:
            raise ValueError("view filter must be a string")
        object.__setattr__(self, "filter", normalized_filter)
        visible = tuple(_text(value, "visible field") for value in self.visible_fields)
        groups = tuple(_text(value, "group field") for value in self.group_by)
        vertical = tuple(_text(value, "vertical group field") for value in self.vertical_group_by)
        if len({value.casefold() for value in visible}) != len(visible):
            raise ValueError("visible fields must be unique")
        if len(groups) > 1 or len(vertical) > 1:
            raise ValueError("view grouping supports at most one field per axis")
        if vertical and layout != "board":
            raise ValueError("vertical grouping is allowed only for board views")
        if visible and layout == "roadmap":
            raise ValueError("visible_fields are not supported for roadmap views")
        normalized_sort: list[tuple[str, str]] = []
        for field_name, direction in self.sort_by:
            field = _text(field_name, "sort field")
            order = _text(direction, "sort direction").casefold()
            if order not in {"asc", "desc"}:
                raise ValueError("sort direction must be asc or desc")
            normalized_sort.append((field, order))
        object.__setattr__(self, "visible_fields", visible)
        object.__setattr__(self, "sort_by", tuple(normalized_sort))
        object.__setattr__(self, "group_by", groups)
        object.__setattr__(self, "vertical_group_by", vertical)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "layout": self.layout,
            "filter": self.filter,
            "visible_fields": list(self.visible_fields),
            "sort_by": [list(item) for item in self.sort_by],
            "group_by": list(self.group_by),
            "vertical_group_by": list(self.vertical_group_by),
        }


@dataclass(frozen=True, slots=True)
class ProjectViewObservation:
    name: str
    layout: str
    filter: str = ""
    visible_fields: tuple[str, ...] = ()
    sort_by: tuple[tuple[str, str], ...] = ()
    group_by: tuple[str, ...] = ()
    vertical_group_by: tuple[str, ...] = ()
    behavior_verified: bool | None = None
    behavior_mismatches: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        probe = ProjectViewSpec(
            self.name,
            "observed Project view",
            self.layout,
            self.filter,
            self.visible_fields,
            self.sort_by,
            self.group_by,
            self.vertical_group_by,
        )
        object.__setattr__(self, "name", probe.name)
        object.__setattr__(self, "layout", probe.layout)
        object.__setattr__(self, "filter", probe.filter)
        object.__setattr__(self, "visible_fields", probe.visible_fields)
        object.__setattr__(self, "sort_by", probe.sort_by)
        object.__setattr__(self, "group_by", probe.group_by)
        object.__setattr__(self, "vertical_group_by", probe.vertical_group_by)
        if (
            self.behavior_verified is not True
            and self.behavior_verified is not False
            and self.behavior_verified is not None
        ):
            raise ValueError("behavior_verified must be true, false, or null")
        behavior_mismatches = tuple(
            _text(value, "view behavior mismatch") for value in self.behavior_mismatches
        )
        if self.behavior_verified is True and behavior_mismatches:
            raise ValueError("verified view behavior cannot contain mismatches")
        object.__setattr__(self, "behavior_mismatches", behavior_mismatches)


@dataclass(frozen=True, slots=True)
class ProjectSchemaManifest:
    portfolio_id: str
    fields: tuple[ProjectFieldSpec, ...]
    views: tuple[ProjectViewSpec, ...]
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("project schema manifest schema_version must be 1")
        object.__setattr__(
            self, "portfolio_id", _text(self.portfolio_id, "portfolio_id")
        )
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
            "portfolio_id": self.portfolio_id,
            "fields": [item.to_json_dict() for item in self.fields],
            "views": [item.to_json_dict() for item in self.views],
        }


@dataclass(frozen=True, slots=True)
class ProjectSchemaRepairAction:
    kind: str
    target: str
    disposition: str
    reason: str

    def __post_init__(self) -> None:
        if self.kind not in {
            "create_field",
            "change_field_type",
            "add_option",
            "create_view",
            "update_view",
        }:
            raise ValueError("unsupported schema repair action kind")
        if self.disposition not in {"automatic", "provider_gap", "manual"}:
            raise ValueError("unsupported schema repair disposition")
        object.__setattr__(self, "target", _text(self.target, "repair target"))
        object.__setattr__(self, "reason", _text(self.reason, "repair reason"))

    def to_json_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "target": self.target,
            "disposition": self.disposition,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ProjectSchemaPlan:
    project_id: str
    portfolio_id: str
    ready: bool
    automatic_ready: bool
    actions: tuple[ProjectSchemaRepairAction, ...]
    unverified_views: tuple[str, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "portfolio_id": self.portfolio_id,
            "ready": self.ready,
            "automatic_ready": self.automatic_ready,
            "actions": [action.to_json_dict() for action in self.actions],
            "unverified_views": list(self.unverified_views),
        }


@dataclass(frozen=True, slots=True)
class ProjectSchemaStatus:
    project_id: str
    portfolio_id: str
    fields_ready: bool
    views_ready: bool | None
    missing_fields: tuple[str, ...] = ()
    type_mismatches: tuple[str, ...] = ()
    missing_options: tuple[str, ...] = ()
    missing_views: tuple[str, ...] = ()
    unverified_views: tuple[str, ...] = ()
    view_mismatches: tuple[str, ...] = ()
    schema_version: int = PUBLIC_SCHEMA_VERSION

    @property
    def ready(self) -> bool:
        return self.fields_ready and self.views_ready is True

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "portfolio_id": self.portfolio_id,
            "ready": self.ready,
            "fields_ready": self.fields_ready,
            "views_ready": self.views_ready,
            "missing_fields": list(self.missing_fields),
            "type_mismatches": list(self.type_mismatches),
            "missing_options": list(self.missing_options),
            "missing_views": list(self.missing_views),
            "unverified_views": list(self.unverified_views),
            "view_mismatches": list(self.view_mismatches),
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
    for key in ("visible_fields", "sort_by", "group_by", "vertical_group_by"):
        if not isinstance(item[key], list):
            raise ValueError(f"project view {key} must be an array")
    sort_by: list[tuple[str, str]] = []
    for entry in item["sort_by"]:
        if not isinstance(entry, list) or len(entry) != 2:
            raise ValueError("project view sort_by entries must be [field, direction]")
        sort_by.append((entry[0], entry[1]))
    return ProjectViewSpec(
        name=item["name"],
        purpose=item["purpose"],
        layout=item["layout"],
        filter=item["filter"],
        visible_fields=tuple(item["visible_fields"]),
        sort_by=tuple(sort_by),
        group_by=tuple(item["group_by"]),
        vertical_group_by=tuple(item["vertical_group_by"]),
    )


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
        portfolio_id=root["portfolio_id"],
        fields=tuple(_field_spec(item) for item in fields),
        views=tuple(_view_spec(item) for item in views),
    )


def compare_project_schema(
    manifest: ProjectSchemaManifest,
    observed_fields: tuple[ProjectField, ...],
    *,
    project_id: str,
    views_observed: tuple[ProjectViewObservation | str, ...] | None,
) -> ProjectSchemaStatus:
    if not isinstance(manifest, ProjectSchemaManifest):
        raise ValueError("manifest must be a ProjectSchemaManifest")
    if any(not isinstance(item, ProjectField) for item in observed_fields):
        raise ValueError("observed_fields must contain ProjectField values")
    normalized_project_id = _text(project_id, "project_id")
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
            mismatches.append(
                f"{expected.name}:{actual.kind.value}->{expected.kind.value}"
            )
            continue
        available_options = {item.name.casefold() for item in actual.options}
        for option in expected.options:
            if option.casefold() not in available_options:
                missing_options.append(f"{expected.name}:{option}")

    view_mismatches: list[str] = []
    missing_views: tuple[str, ...] = ()
    if views_observed is None:
        views_ready: bool | None = None
        unverified_views = tuple(item.name for item in manifest.views)
    else:
        semantic_views = {
            item.name.casefold(): item
            for item in views_observed
            if isinstance(item, ProjectViewObservation)
        }
        name_only_views = {
            item.casefold() for item in views_observed if isinstance(item, str)
        }
        if len(semantic_views) + len(name_only_views) != len(views_observed):
            raise ValueError(
                "views_observed must contain ProjectViewObservation or string values"
            )
        unverified: list[str] = []
        missing: list[str] = []
        for expected in manifest.views:
            key = expected.name.casefold()
            actual = semantic_views.get(key)
            if actual is None:
                unverified.append(expected.name)
                if key not in name_only_views:
                    missing.append(expected.name)
                continue
            dimensions = (
                ("layout", actual.layout, expected.layout),
                ("filter", actual.filter.casefold(), expected.filter.casefold()),
                (
                    "visible_fields",
                    tuple(value.casefold() for value in actual.visible_fields),
                    tuple(value.casefold() for value in expected.visible_fields),
                ),
                (
                    "sort_by",
                    tuple((field.casefold(), direction) for field, direction in actual.sort_by),
                    tuple((field.casefold(), direction) for field, direction in expected.sort_by),
                ),
                (
                    "group_by",
                    tuple(value.casefold() for value in actual.group_by),
                    tuple(value.casefold() for value in expected.group_by),
                ),
                (
                    "vertical_group_by",
                    tuple(value.casefold() for value in actual.vertical_group_by),
                    tuple(value.casefold() for value in expected.vertical_group_by),
                ),
            )
            stored_semantics_match = True
            for dimension, observed_value, expected_value in dimensions:
                if observed_value != expected_value:
                    stored_semantics_match = False
                    view_mismatches.append(f"{expected.name}:{dimension}")
            if stored_semantics_match and expected.filter:
                if actual.behavior_verified is False:
                    view_mismatches.append(f"{expected.name}:behavior")
                elif actual.behavior_verified is None:
                    unverified.append(expected.name)
        missing_views = tuple(missing)
        unverified_views = tuple(unverified)
        views_ready = not (unverified_views or view_mismatches)

    fields_ready = not (missing_fields or mismatches or missing_options)
    return ProjectSchemaStatus(
        project_id=normalized_project_id,
        portfolio_id=manifest.portfolio_id,
        fields_ready=fields_ready,
        views_ready=views_ready,
        missing_fields=tuple(sorted(missing_fields, key=str.casefold)),
        type_mismatches=tuple(sorted(mismatches, key=str.casefold)),
        missing_options=tuple(sorted(missing_options, key=str.casefold)),
        missing_views=tuple(sorted(missing_views, key=str.casefold)),
        unverified_views=tuple(unverified_views),
        view_mismatches=tuple(sorted(view_mismatches, key=str.casefold)),
    )


def plan_project_schema_repair(
    status: ProjectSchemaStatus,
    manifest: ProjectSchemaManifest,
) -> ProjectSchemaPlan:
    if not isinstance(status, ProjectSchemaStatus):
        raise ValueError("status must be a ProjectSchemaStatus")
    if not isinstance(manifest, ProjectSchemaManifest):
        raise ValueError("manifest must be a ProjectSchemaManifest")
    if status.portfolio_id != manifest.portfolio_id:
        raise ValueError("schema status and manifest portfolio_id must match")

    actions: list[ProjectSchemaRepairAction] = []
    for field_name in status.missing_fields:
        actions.append(
            ProjectSchemaRepairAction(
                kind="create_field",
                target=field_name,
                disposition="provider_gap",
                reason=(
                    "the bounded GitHub Projects provider can update item fields "
                    "but does not expose general custom-field creation"
                ),
            )
        )
    for mismatch in status.type_mismatches:
        actions.append(
            ProjectSchemaRepairAction(
                kind="change_field_type",
                target=mismatch,
                disposition="provider_gap",
                reason=(
                    "the bounded GitHub Projects provider does not expose field-type migration"
                ),
            )
        )
    for option in status.missing_options:
        actions.append(
            ProjectSchemaRepairAction(
                kind="add_option",
                target=option,
                disposition="provider_gap",
                reason=(
                    "the bounded GitHub Projects provider does not expose single-select option provisioning"
                ),
            )
        )
    if status.views_ready is False:
        for view_name in status.missing_views:
            actions.append(
                ProjectSchemaRepairAction(
                    kind="create_view",
                    target=view_name,
                    disposition="provider_gap",
                    reason=(
                        "the normal Project provider does not create saved views; "
                        "run the bounded registered-Project commissioner"
                    ),
                )
            )
        for mismatch in status.view_mismatches:
            _, _, dimension = mismatch.rpartition(":")
            commissioner_supported = dimension in {
                "layout",
                "filter",
                "visible_fields",
                "behavior",
            }
            actions.append(
                ProjectSchemaRepairAction(
                    kind="update_view",
                    target=mismatch,
                    disposition=("provider_gap" if commissioner_supported else "manual"),
                    reason=(
                        "the normal Project provider does not repair saved-view semantics; "
                        "run the bounded registered-Project commissioner"
                        if commissioner_supported
                        else (
                            "the current bounded registered-Project commissioner intentionally "
                            f"does not mutate existing view {dimension} configuration"
                        )
                    ),
                )
            )
    actions.sort(key=lambda action: (action.kind, action.target.casefold()))
    return ProjectSchemaPlan(
        project_id=status.project_id,
        portfolio_id=status.portfolio_id,
        ready=status.ready,
        automatic_ready=status.ready and not actions,
        actions=tuple(actions),
        unverified_views=status.unverified_views,
    )


__all__ = [
    "ProjectFieldSpec",
    "ProjectSchemaManifest",
    "ProjectSchemaPlan",
    "ProjectSchemaRepairAction",
    "ProjectSchemaStatus",
    "ProjectViewObservation",
    "ProjectViewSpec",
    "compare_project_schema",
    "load_project_schema_manifest",
    "plan_project_schema_repair",
]
