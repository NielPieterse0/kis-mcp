from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from kis_mcp.work_management.backend import (
    ProjectBinding,
    ProjectField,
    ProjectFieldKind,
    ProjectFieldOption,
)
from kis_mcp.work_management.schema import (
    ProjectSchemaManifest,
    ProjectViewObservation,
    compare_project_schema,
)

CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], Any]
_KIND_BY_GITHUB = {
    "TEXT": ProjectFieldKind.TEXT,
    "NUMBER": ProjectFieldKind.NUMBER,
    "DATE": ProjectFieldKind.DATE,
    "SINGLE_SELECT": ProjectFieldKind.SINGLE_SELECT,
    "ITERATION": ProjectFieldKind.ITERATION,
    "REPOSITORY": ProjectFieldKind.REPOSITORY,
}
_CUSTOM_KIND = {
    ProjectFieldKind.TEXT: "TEXT",
    ProjectFieldKind.NUMBER: "NUMBER",
    ProjectFieldKind.DATE: "DATE",
    ProjectFieldKind.SINGLE_SELECT: "SINGLE_SELECT",
    ProjectFieldKind.ITERATION: "ITERATION",
}
_VIEW_LAYOUT = {"table": "TABLE_LAYOUT", "board": "BOARD_LAYOUT", "roadmap": "ROADMAP_LAYOUT"}
_VIEW_ITEMS_PER_PAGE = 100
_MAX_VIEW_ITEM_PAGES = 10


@dataclass(frozen=True, slots=True)
class ProjectSchemaTarget:
    owner: str
    owner_type: str
    project_number: int

    def __post_init__(self) -> None:
        if not isinstance(self.owner, str) or not self.owner.strip():
            raise ValueError("project owner must be a non-empty string")
        owner_type = self.owner_type.casefold() if isinstance(self.owner_type, str) else ""
        if owner_type not in {"user", "org"}:
            raise ValueError("project owner_type must be user or org")
        if isinstance(self.project_number, bool) or not isinstance(self.project_number, int) or self.project_number <= 0:
            raise ValueError("project_number must be a positive integer")
        object.__setattr__(self, "owner", self.owner.strip())
        object.__setattr__(self, "owner_type", owner_type)

    @classmethod
    def from_binding(cls, binding: ProjectBinding) -> "ProjectSchemaTarget":
        return cls(
            owner=binding.owner,
            owner_type=binding.owner_type.value,
            project_number=binding.project_number,
        )


@dataclass(frozen=True, slots=True)
class _Option:
    option_id: str
    name: str
    color: str
    description: str


@dataclass(frozen=True, slots=True)
class _Field:
    field_id: str
    database_id: int | None
    name: str
    kind: ProjectFieldKind
    options: tuple[_Option, ...] = ()


@dataclass(frozen=True, slots=True)
class _View:
    view_id: str
    view_number: int
    name: str
    layout: str
    filter: str = ""
    visible_fields: tuple[str, ...] = ()
    sort_by: tuple[tuple[str, str], ...] = ()
    group_by: tuple[str, ...] = ()
    vertical_group_by: tuple[str, ...] = ()

    def observation(
        self,
        *,
        behavior_verified: bool | None = None,
        behavior_mismatches: tuple[str, ...] = (),
    ) -> ProjectViewObservation:
        return ProjectViewObservation(
            name=self.name,
            layout=self.layout.removesuffix("_LAYOUT").casefold(),
            filter=self.filter,
            visible_fields=(
                () if self.layout == "ROADMAP_LAYOUT" else self.visible_fields
            ),
            sort_by=self.sort_by,
            group_by=self.group_by,
            vertical_group_by=self.vertical_group_by,
            behavior_verified=behavior_verified,
            behavior_mismatches=behavior_mismatches,
        )


@dataclass(frozen=True, slots=True)
class _Snapshot:
    project_id: str
    owner_database_id: int | None
    fields: tuple[_Field, ...]
    views: tuple[_View, ...]

    def work_fields(self) -> tuple[ProjectField, ...]:
        return tuple(
            ProjectField(
                field_id=field.field_id,
                name=field.name,
                kind=field.kind,
                options=tuple(
                    ProjectFieldOption(option_id=option.option_id, name=option.name)
                    for option in field.options
                ),
            )
            for field in self.fields
        )


def _default_runner(args: Sequence[str], cwd: Path, env: Mapping[str, str]):
    return subprocess.run(
        list(args), cwd=cwd, env=dict(env), text=True, capture_output=True, timeout=60, check=False
    )


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _required(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} was missing")
    return value.strip()


def _connection_nodes(value: Any, label: str) -> list[Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: {label} was missing")
    page_info = value.get("pageInfo")
    if not isinstance(page_info, dict):
        raise RuntimeError(f"GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: {label} pageInfo was missing")
    if page_info.get("hasNextPage"):
        raise RuntimeError(f"GITHUB_PROJECT_SCHEMA_INCOMPLETE: {label} exceeded 100 entries")
    nodes = value.get("nodes")
    if not isinstance(nodes, list):
        raise RuntimeError(f"GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: {label} nodes were missing")
    return nodes


def _field_names(value: Any, label: str) -> tuple[str, ...]:
    names: list[str] = []
    for item in _connection_nodes(value, label):
        if not isinstance(item, dict):
            raise RuntimeError(f"GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: {label} field was invalid")
        names.append(_required(item.get("name"), f"{label} field name"))
    return tuple(names)


class GitHubProjectSchemaClient:
    def __init__(
        self,
        *,
        gh_config_dir: Path,
        cwd: Path,
        runner: CommandRunner = _default_runner,
    ) -> None:
        self._gh_config_dir = Path(gh_config_dir)
        self._cwd = Path(cwd)
        self._runner = runner

    def _environment(self) -> dict[str, str]:
        env = dict(os.environ)
        for name in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
            env.pop(name, None)
        env["GH_CONFIG_DIR"] = str(self._gh_config_dir)
        env["GIT_TERMINAL_PROMPT"] = "0"
        return env

    def _graphql(self, query: str) -> dict[str, Any]:
        result = self._runner(
            ("gh", "api", "graphql", "--hostname", "github.com", "-f", f"query={query}"),
            self._cwd,
            self._environment(),
        )
        if getattr(result, "returncode", 1) != 0:
            stderr = str(getattr(result, "stderr", "")).strip()
            raise RuntimeError(f"GITHUB_PROJECT_SCHEMA_API_FAILED: {stderr or 'gh api graphql failed'}")
        try:
            document = json.loads(str(getattr(result, "stdout", "")) or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: response was not JSON") from exc
        if not isinstance(document, dict):
            raise RuntimeError("GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: response was not an object")
        if document.get("errors"):
            raise RuntimeError("GITHUB_PROJECT_SCHEMA_API_FAILED: GraphQL returned errors")
        return document

    @staticmethod
    def _snapshot_query(target: ProjectSchemaTarget) -> str:
        owner_field = "user" if target.owner_type == "user" else "organization"
        return f'''query {{
  {owner_field}(login: {_quoted(target.owner)}) {{
    databaseId
    projectV2(number: {target.project_number}) {{
      id
      fields(first: 100) {{
        nodes {{
          __typename
          ... on ProjectV2FieldCommon {{ id databaseId name dataType }}
          ... on ProjectV2SingleSelectField {{
            options {{ id name color description }}
          }}
        }}
        pageInfo {{ hasNextPage }}
      }}
      views(first: 100) {{
        nodes {{
          id
          number
          name
          layout
          filter
          configuration {{
            visibleFields(first: 100) {{
              nodes {{
                __typename
                ... on ProjectV2FieldCommon {{ id name }}
              }}
              pageInfo {{ hasNextPage }}
            }}
          }}
          sortByFields(first: 100) {{
            nodes {{
              direction
              field {{
                __typename
                ... on ProjectV2FieldCommon {{ id name }}
              }}
            }}
            pageInfo {{ hasNextPage }}
          }}
          groupByFields(first: 100) {{
            nodes {{
              __typename
              ... on ProjectV2FieldCommon {{ id name }}
            }}
            pageInfo {{ hasNextPage }}
          }}
          verticalGroupByFields(first: 100) {{
            nodes {{
              __typename
              ... on ProjectV2FieldCommon {{ id name }}
            }}
            pageInfo {{ hasNextPage }}
          }}
        }}
        pageInfo {{ hasNextPage }}
      }}
    }}
  }}
}}'''

    def read_snapshot(self, target: ProjectSchemaTarget) -> _Snapshot:
        document = self._graphql(self._snapshot_query(target))
        owner_key = "user" if target.owner_type == "user" else "organization"
        data = document.get("data")
        owner = data.get(owner_key) if isinstance(data, dict) else None
        project = owner.get("projectV2") if isinstance(owner, dict) else None
        if not isinstance(project, dict):
            raise RuntimeError("GITHUB_PROJECT_SCHEMA_NOT_FOUND: registered Project was not found")
        raw_fields = _connection_nodes(project.get("fields"), "Project fields")
        raw_views = _connection_nodes(project.get("views"), "Project views")

        fields: list[_Field] = []
        for item in raw_fields:
            if not isinstance(item, dict):
                raise RuntimeError("GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: field was not an object")
            kind = _KIND_BY_GITHUB.get(str(item.get("dataType", "")).upper(), ProjectFieldKind.UNKNOWN)
            options: list[_Option] = []
            if kind is ProjectFieldKind.SINGLE_SELECT:
                raw_options = item.get("options", [])
                if not isinstance(raw_options, list):
                    raise RuntimeError("GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: field options were invalid")
                for option in raw_options:
                    if not isinstance(option, dict):
                        raise RuntimeError("GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: field option was invalid")
                    options.append(
                        _Option(
                            option_id=_required(option.get("id"), "option id"),
                            name=_required(option.get("name"), "option name"),
                            color=_required(option.get("color"), "option color"),
                            description=str(option.get("description", "")),
                        )
                    )
            database_id = item.get("databaseId")
            if isinstance(database_id, bool) or not isinstance(database_id, int):
                database_id = None
            fields.append(
                _Field(
                    field_id=_required(item.get("id"), "field id"),
                    database_id=database_id,
                    name=_required(item.get("name"), "field name"),
                    kind=kind,
                    options=tuple(options),
                )
            )
        views: list[_View] = []
        for item in raw_views:
            if not isinstance(item, dict):
                raise RuntimeError("GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: view was not an object")
            configuration = item.get("configuration")
            if not isinstance(configuration, dict):
                raise RuntimeError(
                    "GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: view configuration was missing"
                )
            sort_by: list[tuple[str, str]] = []
            for sort_item in _connection_nodes(item.get("sortByFields"), "view sort config"):
                if not isinstance(sort_item, dict) or not isinstance(sort_item.get("field"), dict):
                    raise RuntimeError(
                        "GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: view sort entry was invalid"
                    )
                sort_by.append(
                    (
                        _required(sort_item["field"].get("name"), "view sort field name"),
                        _required(sort_item.get("direction"), "view sort direction").casefold(),
                    )
                )
            view_number = item.get("number")
            if isinstance(view_number, bool) or not isinstance(view_number, int) or view_number <= 0:
                raise RuntimeError(
                    "GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: view number was invalid"
                )
            views.append(
                _View(
                    view_id=_required(item.get("id"), "view id"),
                    view_number=view_number,
                    name=_required(item.get("name"), "view name"),
                    layout=_required(item.get("layout"), "view layout"),
                    filter=str(item.get("filter") or "").strip(),
                    visible_fields=_field_names(
                        configuration.get("visibleFields"), "view visible fields"
                    ),
                    sort_by=tuple(sort_by),
                    group_by=_field_names(item.get("groupByFields"), "view group config"),
                    vertical_group_by=_field_names(
                        item.get("verticalGroupByFields"), "view vertical group config"
                    ),
                )
            )
        owner_database_id = owner.get("databaseId") if isinstance(owner, dict) else None
        if isinstance(owner_database_id, bool) or not isinstance(owner_database_id, int):
            owner_database_id = None
        return _Snapshot(
            project_id=_required(project.get("id"), "project id"),
            owner_database_id=owner_database_id,
            fields=tuple(fields),
            views=tuple(views),
        )

    @staticmethod
    def _field_slug(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")

    @classmethod
    def _filter_requirements(
        cls,
        snapshot: _Snapshot,
        filter_text: str,
    ) -> tuple[tuple[_Field, tuple[str, ...]], ...] | None:
        if not filter_text:
            return ()
        by_slug = {cls._field_slug(field.name): field for field in snapshot.fields}
        requirements: list[tuple[_Field, tuple[str, ...]]] = []
        try:
            tokens = shlex.split(filter_text, posix=True)
        except ValueError:
            return None
        for token in tokens:
            qualifier, separator, raw_values = token.partition(":")
            if not separator or not qualifier or not raw_values:
                return None
            field = by_slug.get(qualifier.casefold())
            if field is None:
                return None
            values = tuple(
                value.strip().casefold()
                for value in raw_values.split(",")
                if value.strip()
            )
            if not values:
                return None
            requirements.append((field, values))
        return tuple(requirements)

    @staticmethod
    def _included_saved_view_page(
        stdout: str,
    ) -> tuple[tuple[dict[str, Any], ...] | None, str | None, str | None]:
        if not isinstance(stdout, str) or not stdout.strip():
            return None, None, "empty_response"
        parts = re.split(r"\r?\n\r?\n", stdout, maxsplit=1)
        body_only = len(parts) != 2 or not parts[0].lstrip().startswith("HTTP/")
        if body_only:
            if not stdout.lstrip().startswith("["):
                return None, None, "malformed_http"
            headers = ""
            body = stdout
        else:
            headers, body = parts
        next_cursor: str | None = None
        for line in headers.splitlines():
            if not line.casefold().startswith("link:"):
                continue
            for link in line.partition(":")[2].split(","):
                if 'rel="next"' not in link.casefold():
                    continue
                match = re.search(r"<([^>]+)>", link)
                if match is None:
                    return None, None, "pagination_link"
                cursors = parse_qs(urlparse(match.group(1)).query).get("after", [])
                if len(cursors) != 1 or not cursors[0].strip():
                    return None, None, "pagination_cursor"
                if next_cursor is not None:
                    return None, None, "pagination_link"
                next_cursor = cursors[0].strip()
        if not body.strip():
            return None, None, "empty_body"
        try:
            document = json.loads(body)
        except json.JSONDecodeError:
            return None, None, "malformed_json"
        if not isinstance(document, list):
            return None, None, "response_shape"
        items: list[dict[str, Any]] = []
        for item in document:
            if not isinstance(item, dict):
                return None, None, "item_shape"
            items.append(item)
        if body_only and len(items) >= _VIEW_ITEMS_PER_PAGE:
            return None, None, "pagination_evidence"
        return tuple(items), next_cursor, None

    def _verify_saved_view_behavior(
        self,
        target: ProjectSchemaTarget,
        snapshot: _Snapshot,
        view: _View,
        *,
        expected_filter: str,
    ) -> tuple[bool | None, tuple[str, ...]]:
        requirements = self._filter_requirements(snapshot, expected_filter)
        if requirements is None:
            return None, ("unverified:filter_grammar",)
        if not requirements:
            return True, ()
        if any(field.database_id is None for field, _ in requirements):
            return None, ("unverified:field_database_id",)
        if target.owner_type == "user":
            endpoint = (
                f"/users/{target.owner}/projectsV2/{target.project_number}/"
                f"views/{view.view_number}/items"
            )
        else:
            endpoint = (
                f"/orgs/{target.owner}/projectsV2/{target.project_number}/"
                f"views/{view.view_number}/items"
            )
        database_ids = tuple(int(field.database_id) for field, _ in requirements)
        base_args = (
            "gh",
            "api",
            "--hostname",
            "github.com",
            "--method",
            "GET",
            "-H",
            "X-GitHub-Api-Version: 2026-03-10",
            "-H",
            "Accept: application/vnd.github+json",
            "--include",
            endpoint,
            "-f",
            f"per_page={_VIEW_ITEMS_PER_PAGE}",
            "-f",
            "fields=" + ",".join(str(value) for value in database_ids),
        )
        items: list[dict[str, Any]] = []
        seen_cursors: set[str] = set()
        after: str | None = None
        for page_number in range(_MAX_VIEW_ITEM_PAGES):
            args = base_args if after is None else (*base_args, "-f", f"after={after}")
            result = self._runner(args, self._cwd, self._environment())
            if getattr(result, "returncode", 1) != 0:
                return None, ("unverified:api_error",)
            page_items, next_cursor, reason = self._included_saved_view_page(
                str(getattr(result, "stdout", ""))
            )
            if reason is not None or page_items is None:
                return None, (f"unverified:{reason or 'response'}",)
            items.extend(page_items)
            if next_cursor is None:
                break
            if next_cursor in seen_cursors:
                return None, ("unverified:pagination_cycle",)
            if page_number + 1 >= _MAX_VIEW_ITEM_PAGES:
                return None, ("unverified:pagination_limit",)
            seen_cursors.add(next_cursor)
            after = next_cursor
        required_by_name = {field.name.casefold(): field for field, _ in requirements}
        mismatches: list[str] = []
        for item in items:
            raw_fields = item.get("fields")
            if not isinstance(raw_fields, list):
                return None, ("unverified:item_fields",)
            values_by_name: dict[str, str] = {}
            seen_field_names: set[str] = set()
            for raw_field in raw_fields:
                if not isinstance(raw_field, dict):
                    return None, ("unverified:field_entry",)
                field_name = raw_field.get("name")
                if not isinstance(field_name, str) or not field_name.strip():
                    return None, ("unverified:field_name",)
                field_key = field_name.casefold()
                field = required_by_name.get(field_key)
                if field is None:
                    continue
                if field_key in seen_field_names:
                    return None, ("unverified:duplicate_required_field",)
                seen_field_names.add(field_key)
                value = raw_field.get("value")
                if value is None:
                    continue
                if field.kind is ProjectFieldKind.SINGLE_SELECT:
                    if not isinstance(value, dict):
                        return None, ("unverified:single_select_value",)
                    option_name = value.get("name")
                    if isinstance(option_name, dict):
                        option_name = option_name.get("raw")
                    if not isinstance(option_name, str) or not option_name.strip():
                        return None, ("unverified:single_select_name",)
                    values_by_name[field_key] = option_name.strip()
                    continue
                if field.kind in {ProjectFieldKind.TEXT, ProjectFieldKind.DATE}:
                    if not isinstance(value, str):
                        return None, ("unverified:scalar_value",)
                    values_by_name[field_key] = value.strip()
                    continue
                return None, ("unverified:unsupported_field_kind",)
            for field, allowed in requirements:
                observed_value = values_by_name.get(field.name.casefold())
                if observed_value is None or observed_value.casefold() not in allowed:
                    detail = "<missing>" if observed_value is None else observed_value
                    mismatch = f"{field.name}:{detail}"
                    if mismatch not in mismatches:
                        mismatches.append(mismatch)
        return not mismatches, tuple(mismatches)

    def _observations_for_snapshot(
        self,
        target: ProjectSchemaTarget,
        snapshot: _Snapshot,
        manifest: ProjectSchemaManifest,
    ) -> tuple[ProjectViewObservation, ...]:
        actual_by_name = {view.name.casefold(): view for view in snapshot.views}
        observations: list[ProjectViewObservation] = []
        for expected in manifest.views:
            view = actual_by_name.get(expected.name.casefold())
            if view is None:
                continue
            verified, mismatches = self._verify_saved_view_behavior(
                target,
                snapshot,
                view,
                expected_filter=expected.filter,
            )
            observations.append(
                view.observation(
                    behavior_verified=verified,
                    behavior_mismatches=mismatches,
                )
            )
        return tuple(observations)

    def read_views(
        self,
        target: ProjectSchemaTarget,
        manifest: ProjectSchemaManifest,
    ) -> tuple[ProjectViewObservation, ...]:
        if not isinstance(manifest, ProjectSchemaManifest):
            raise ValueError("manifest must be a ProjectSchemaManifest")
        snapshot = self.read_snapshot(target)
        return self._observations_for_snapshot(target, snapshot, manifest)

    @staticmethod
    def _option_input(option: _Option | None, name: str) -> str:
        option_id = "" if option is None else f"id: {_quoted(option.option_id)}, "
        color = "GRAY" if option is None else option.color
        description = "" if option is None else option.description
        return (
            "{" + option_id + f"name: {_quoted(name)}, color: {color}, "
            f"description: {_quoted(description)}" + "}"
        )

    def _update_select_options(self, field: _Field, expected_options: tuple[str, ...]) -> None:
        by_name = {option.name.casefold(): option for option in field.options}
        all_names = [option.name for option in field.options]
        all_names.extend(name for name in expected_options if name.casefold() not in by_name)
        values = ", ".join(
            self._option_input(by_name.get(name.casefold()), name) for name in all_names
        )
        query = f'''mutation {{
  updateProjectV2Field(input: {{
    fieldId: {_quoted(field.field_id)},
    singleSelectOptions: [{values}]
  }}) {{ clientMutationId }}
}}'''
        self._graphql(query)

    def _create_field(self, project_id: str, field_spec) -> None:
        if field_spec.kind is ProjectFieldKind.REPOSITORY:
            raise ValueError("built-in repository field cannot be created by schema commissioning")
        try:
            data_type = _CUSTOM_KIND[field_spec.kind]
        except KeyError as exc:
            raise ValueError(f"unsupported project field type: {field_spec.kind.value}") from exc
        parts = [
            f"projectId: {_quoted(project_id)}",
            f"name: {_quoted(field_spec.name)}",
            f"dataType: {data_type}",
        ]
        if field_spec.kind is ProjectFieldKind.SINGLE_SELECT:
            if not field_spec.options:
                raise ValueError(f"single-select field requires options: {field_spec.name}")
            options = ", ".join(self._option_input(None, name) for name in field_spec.options)
            parts.append(f"singleSelectOptions: [{options}]")
        if field_spec.kind is ProjectFieldKind.ITERATION:
            today = datetime.now(timezone.utc).date()
            monday = today - timedelta(days=today.weekday())
            parts.append(
                "iterationConfiguration: {duration: 14, "
                f"startDate: {_quoted(monday.isoformat())}, iterations: []}}"
            )
        self._graphql(
            "mutation { createProjectV2Field(input: {"
            + ", ".join(parts)
            + "}) { clientMutationId } }"
        )

    @staticmethod
    def _view_field_ids(snapshot: _Snapshot, names: tuple[str, ...]) -> tuple[str, ...]:
        by_name = {field.name.casefold(): field.field_id for field in snapshot.fields}
        missing = tuple(name for name in names if name.casefold() not in by_name)
        if missing:
            raise ValueError(
                "view configuration references unavailable Project fields: "
                + ", ".join(missing)
            )
        return tuple(by_name[name.casefold()] for name in names)

    @staticmethod
    def _view_database_ids(snapshot: _Snapshot, names: tuple[str, ...]) -> tuple[int, ...]:
        by_name = {field.name.casefold(): field.database_id for field in snapshot.fields}
        missing = tuple(
            name
            for name in names
            if name.casefold() not in by_name or by_name[name.casefold()] is None
        )
        if missing:
            raise ValueError(
                "view configuration requires Project database field IDs: "
                + ", ".join(missing)
            )
        return tuple(int(by_name[name.casefold()]) for name in names)

    def _update_view(
        self,
        snapshot: _Snapshot,
        actual: _View,
        expected,
        *,
        force_filter: bool = False,
    ) -> None:
        observed = actual.observation()
        parts = [f"viewId: {_quoted(actual.view_id)}"]
        expected_layout = _VIEW_LAYOUT[expected.layout]
        if actual.layout != expected_layout:
            parts.append(f"layout: {expected_layout}")
        if force_filter or observed.filter != expected.filter:
            parts.append(f"filter: {_quoted(expected.filter)}")
        if observed.visible_fields != expected.visible_fields:
            field_ids = self._view_field_ids(snapshot, expected.visible_fields)
            values = ", ".join(_quoted(value) for value in field_ids)
            parts.append(f"configuration: {{visibleFieldIds: [{values}]}}")
        if len(parts) == 1:
            return
        self._graphql(
            "mutation { updateProjectV2View(input: {"
            + ", ".join(parts)
            + "}) { clientMutationId } }"
        )

    def _create_view(
        self,
        target: ProjectSchemaTarget,
        snapshot: _Snapshot,
        view_spec,
    ) -> None:
        if target.owner_type == "user":
            if snapshot.owner_database_id is None:
                raise RuntimeError(
                    "GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: user database ID was unavailable"
                )
            endpoint = (
                f"/users/{snapshot.owner_database_id}/projectsV2/"
                f"{target.project_number}/views"
            )
        else:
            endpoint = f"/orgs/{target.owner}/projectsV2/{target.project_number}/views"
        args: list[str] = [
            "gh",
            "api",
            "--hostname",
            "github.com",
            "--method",
            "POST",
            "-H",
            "X-GitHub-Api-Version: 2026-03-10",
            "-H",
            "Accept: application/vnd.github+json",
            endpoint,
            "-f",
            f"name={view_spec.name}",
            "-f",
            f"layout={view_spec.layout}",
            "-f",
            f"filter={view_spec.filter}",
        ]
        for database_id in self._view_database_ids(snapshot, view_spec.visible_fields):
            args.extend(("-F", f"visible_fields[]={database_id}"))
        for field_name, direction in view_spec.sort_by:
            database_id = self._view_database_ids(snapshot, (field_name,))[0]
            args.extend(("-F", f"sort_by[][0]={database_id}"))
            args.extend(("-f", f"sort_by[][1]={direction}"))
        for database_id in self._view_database_ids(snapshot, view_spec.group_by):
            args.extend(("-F", f"group_by[]={database_id}"))
        for database_id in self._view_database_ids(snapshot, view_spec.vertical_group_by):
            args.extend(("-F", f"vertical_group_by[]={database_id}"))
        result = self._runner(tuple(args), self._cwd, self._environment())
        if getattr(result, "returncode", 1) != 0:
            stderr = str(getattr(result, "stderr", "")).strip()
            raise RuntimeError(
                f"GITHUB_PROJECT_SCHEMA_API_FAILED: {stderr or 'gh api view create failed'}"
            )

    def commission(
        self,
        target: ProjectSchemaTarget,
        manifest: ProjectSchemaManifest,
    ) -> dict[str, Any]:
        snapshot = self.read_snapshot(target)
        actual_by_name = {field.name.casefold(): field for field in snapshot.fields}
        for expected in manifest.fields:
            actual = actual_by_name.get(expected.name.casefold())
            if actual is not None and actual.kind is not expected.kind:
                raise ValueError(
                    f"field type mismatch for {expected.name}: "
                    f"{actual.kind.value}->{expected.kind.value}"
                )

        available_view_fields = set(actual_by_name)
        available_view_fields.update(field.name.casefold() for field in manifest.fields)
        initial_views_by_name = {view.name.casefold(): view for view in snapshot.views}
        for expected in manifest.views:
            referenced_fields = (
                *expected.visible_fields,
                *(field_name for field_name, _ in expected.sort_by),
                *expected.group_by,
                *expected.vertical_group_by,
            )
            unavailable = tuple(
                field_name
                for field_name in referenced_fields
                if field_name.casefold() not in available_view_fields
            )
            if unavailable:
                raise ValueError(
                    f"view configuration references unavailable Project fields for {expected.name}: "
                    + ", ".join(unavailable)
                )
            actual = initial_views_by_name.get(expected.name.casefold())
            if actual is None:
                if target.owner_type == "user" and snapshot.owner_database_id is None:
                    raise ValueError(
                        f"missing view {expected.name} requires the registered user database ID"
                    )
                existing_fields = {
                    field.name.casefold(): field for field in snapshot.fields
                }
                missing_database_ids = tuple(
                    field_name
                    for field_name in referenced_fields
                    if (
                        (field := existing_fields.get(field_name.casefold())) is not None
                        and field.database_id is None
                    )
                )
                if missing_database_ids:
                    raise ValueError(
                        f"missing view {expected.name} requires Project database field IDs: "
                        + ", ".join(missing_database_ids)
                    )
                continue
            observed = actual.observation()
            unsupported = []
            if observed.sort_by != expected.sort_by:
                unsupported.append("sort_by")
            if observed.group_by != expected.group_by:
                unsupported.append("group_by")
            if observed.vertical_group_by != expected.vertical_group_by:
                unsupported.append("vertical_group_by")
            if unsupported:
                raise ValueError(
                    f"view configuration mismatch for {expected.name} is not safely mutable: "
                    + ", ".join(unsupported)
                )

        created_fields: list[str] = []
        for expected in manifest.fields:
            actual = actual_by_name.get(expected.name.casefold())
            if actual is None:
                self._create_field(snapshot.project_id, expected)
                created_fields.append(expected.name)

        if created_fields:
            snapshot = self.read_snapshot(target)
            actual_by_name = {field.name.casefold(): field for field in snapshot.fields}
            for expected in manifest.fields:
                actual = actual_by_name.get(expected.name.casefold())
                if actual is None or actual.kind is not expected.kind:
                    raise RuntimeError(
                        f"GITHUB_PROJECT_SCHEMA_VERIFY_FAILED: field not ready after creation: {expected.name}"
                    )

        views_by_name = {view.name.casefold(): view for view in snapshot.views}
        for expected in manifest.views:
            if expected.name.casefold() in views_by_name:
                continue
            referenced_fields = (
                *expected.visible_fields,
                *(field_name for field_name, _ in expected.sort_by),
                *expected.group_by,
                *expected.vertical_group_by,
            )
            self._view_database_ids(snapshot, referenced_fields)

        updated_fields: list[str] = []
        for expected in manifest.fields:
            actual = actual_by_name.get(expected.name.casefold())
            if actual is None:
                raise RuntimeError(
                    f"GITHUB_PROJECT_SCHEMA_VERIFY_FAILED: field unavailable before option update: {expected.name}"
                )
            if expected.kind is ProjectFieldKind.SINGLE_SELECT:
                available = {option.name.casefold() for option in actual.options}
                if any(option.casefold() not in available for option in expected.options):
                    self._update_select_options(actual, expected.options)
                    updated_fields.append(expected.name)
        created_views: list[str] = []
        updated_views: list[str] = []
        for expected in manifest.views:
            actual = views_by_name.get(expected.name.casefold())
            if actual is None:
                self._create_view(target, snapshot, expected)
                created_views.append(expected.name)
                continue
            observed = actual.observation()
            unsupported = []
            if observed.sort_by != expected.sort_by:
                unsupported.append("sort_by")
            if observed.group_by != expected.group_by:
                unsupported.append("group_by")
            if observed.vertical_group_by != expected.vertical_group_by:
                unsupported.append("vertical_group_by")
            if unsupported:
                raise ValueError(
                    f"view configuration mismatch for {expected.name} is not safely mutable: "
                    + ", ".join(unsupported)
                )
            expected_layout = _VIEW_LAYOUT[expected.layout]
            if (
                actual.layout != expected_layout
                or observed.filter != expected.filter
                or observed.visible_fields != expected.visible_fields
            ):
                self._update_view(snapshot, actual, expected)
                updated_views.append(expected.name)
        final = self.read_snapshot(target)
        final_views = {view.name.casefold(): view for view in final.views}
        for expected in manifest.views:
            actual = final_views.get(expected.name.casefold())
            if actual is None or actual.layout != _VIEW_LAYOUT[expected.layout]:
                raise RuntimeError(
                    f"GITHUB_PROJECT_SCHEMA_VERIFY_FAILED: view not ready: {expected.name}"
                )
        observations = self._observations_for_snapshot(target, final, manifest)
        status = compare_project_schema(
            manifest,
            final.work_fields(),
            project_id="registered-project",
            views_observed=observations,
        )
        behavior_repairs = {
            mismatch.partition(":")[0]
            for mismatch in status.view_mismatches
            if mismatch.endswith(":behavior")
        }
        if behavior_repairs:
            expected_by_name = {view.name.casefold(): view for view in manifest.views}
            for name in sorted(behavior_repairs, key=str.casefold):
                actual = final_views.get(name.casefold())
                expected = expected_by_name.get(name.casefold())
                if actual is None or expected is None:
                    raise RuntimeError(
                        f"GITHUB_PROJECT_SCHEMA_VERIFY_FAILED: behavior repair target missing: {name}"
                    )
                self._update_view(final, actual, expected, force_filter=True)
                if expected.name not in updated_views:
                    updated_views.append(expected.name)
            final = self.read_snapshot(target)
            final_views = {view.name.casefold(): view for view in final.views}
            observations = self._observations_for_snapshot(target, final, manifest)
            status = compare_project_schema(
                manifest,
                final.work_fields(),
                project_id="registered-project",
                views_observed=observations,
            )
        if not status.ready:
            observations_by_name = {
                observation.name.casefold(): observation for observation in observations
            }
            details: list[str] = []
            for name in status.unverified_views:
                observation = observations_by_name.get(name.casefold())
                reasons = () if observation is None else observation.behavior_mismatches
                details.append(
                    name if not reasons else f"{name}[{';'.join(reasons)}]"
                )
            details.extend(status.view_mismatches)
            suffix = f": {', '.join(details)}" if details else ""
            raise RuntimeError(
                "GITHUB_PROJECT_SCHEMA_VERIFY_FAILED: canonical schema remained incomplete"
                + suffix
            )
        return {
            "ready": True,
            "project_node_id": final.project_id,
            "created_fields": created_fields,
            "updated_fields": updated_fields,
            "created_views": created_views,
            "updated_views": updated_views,
            "field_count": len(final.fields),
            "view_count": len(final.views),
            "view_behavior": [
                {
                    "name": observation.name,
                    "verified": observation.behavior_verified,
                    "mismatches": list(observation.behavior_mismatches),
                }
                for observation in observations
            ],
        }


class GitHubProjectSchemaAwareBackend:
    def __init__(
        self,
        delegate,
        bindings: Mapping[str, ProjectBinding],
        *,
        manifest: ProjectSchemaManifest,
        gh_config_dir: Path,
        cwd: Path,
        runner: CommandRunner = _default_runner,
    ) -> None:
        self._delegate = delegate
        self._bindings = dict(bindings)
        if not self._bindings or any(
            project_id != binding.managed_project_id
            for project_id, binding in self._bindings.items()
        ):
            raise ValueError("schema-aware backend requires exact configured project bindings")
        if not isinstance(manifest, ProjectSchemaManifest):
            raise ValueError("manifest must be a ProjectSchemaManifest")
        self._manifest = manifest
        self._client = GitHubProjectSchemaClient(
            gh_config_dir=gh_config_dir,
            cwd=cwd,
            runner=runner,
        )
        self.capabilities = getattr(delegate, "capabilities", None)

    async def read_inventory(self, project_binding, *, field_names=(), item_limit=100):
        return await self._delegate.read_inventory(
            project_binding, field_names=field_names, item_limit=item_limit
        )

    async def read_schema_fields(self, project_binding):
        return await self._delegate.read_schema_fields(project_binding)

    async def read_schema_views(
        self, project_binding
    ) -> tuple[ProjectViewObservation, ...]:
        if not isinstance(project_binding, ProjectBinding):
            raise ValueError("project_binding must be a ProjectBinding")
        configured = self._bindings.get(project_binding.managed_project_id)
        if configured != project_binding:
            raise ValueError("project_binding does not match configured GitHub binding")
        target = ProjectSchemaTarget.from_binding(project_binding)
        return await asyncio.to_thread(self._client.read_views, target, self._manifest)

    async def apply_reconciliation(self, decision, *, idempotency_key: str):
        return await self._delegate.apply_reconciliation(
            decision, idempotency_key=idempotency_key
        )


__all__ = [
    "GitHubProjectSchemaAwareBackend",
    "GitHubProjectSchemaClient",
    "ProjectSchemaTarget",
]
