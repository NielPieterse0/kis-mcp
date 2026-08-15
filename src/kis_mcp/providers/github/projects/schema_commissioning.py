from __future__ import annotations

import asyncio
import json
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from kis_mcp.work_management.backend import (
    ProjectBinding,
    ProjectField,
    ProjectFieldKind,
    ProjectFieldOption,
)
from kis_mcp.work_management.schema import (
    ProjectSchemaManifest,
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
    name: str
    kind: ProjectFieldKind
    options: tuple[_Option, ...] = ()


@dataclass(frozen=True, slots=True)
class _View:
    view_id: str
    name: str
    layout: str


@dataclass(frozen=True, slots=True)
class _Snapshot:
    project_id: str
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
    projectV2(number: {target.project_number}) {{
      id
      fields(first: 100) {{
        nodes {{
          __typename
          ... on ProjectV2FieldCommon {{ id name dataType }}
          ... on ProjectV2SingleSelectField {{
            options {{ id name color description }}
          }}
        }}
        pageInfo {{ hasNextPage }}
      }}
      views(first: 100) {{
        nodes {{ id name layout }}
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
        fields_source = project.get("fields")
        views_source = project.get("views")
        if not isinstance(fields_source, dict) or not isinstance(views_source, dict):
            raise RuntimeError("GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: field/view inventory was missing")
        if fields_source.get("pageInfo", {}).get("hasNextPage") or views_source.get("pageInfo", {}).get("hasNextPage"):
            raise RuntimeError("GITHUB_PROJECT_SCHEMA_INCOMPLETE: bounded inventory exceeded 100 entries")
        raw_fields = fields_source.get("nodes")
        raw_views = views_source.get("nodes")
        if not isinstance(raw_fields, list) or not isinstance(raw_views, list):
            raise RuntimeError("GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: field/view nodes were missing")

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
            fields.append(
                _Field(
                    field_id=_required(item.get("id"), "field id"),
                    name=_required(item.get("name"), "field name"),
                    kind=kind,
                    options=tuple(options),
                )
            )
        views: list[_View] = []
        for item in raw_views:
            if not isinstance(item, dict):
                raise RuntimeError("GITHUB_PROJECT_SCHEMA_INVALID_RESPONSE: view was not an object")
            views.append(
                _View(
                    view_id=_required(item.get("id"), "view id"),
                    name=_required(item.get("name"), "view name"),
                    layout=_required(item.get("layout"), "view layout"),
                )
            )
        return _Snapshot(
            project_id=_required(project.get("id"), "project id"),
            fields=tuple(fields),
            views=tuple(views),
        )

    def read_views(self, target: ProjectSchemaTarget) -> tuple[str, ...]:
        return tuple(
            sorted((view.name for view in self.read_snapshot(target).views), key=str.casefold)
        )

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

    def _create_view(self, project_id: str, view_spec) -> None:
        layout = _VIEW_LAYOUT[view_spec.layout]
        self._graphql(
            "mutation { createProjectV2View(input: {"
            f"projectId: {_quoted(project_id)}, name: {_quoted(view_spec.name)}, layout: {layout}"
            "}) { clientMutationId } }"
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

        created_fields: list[str] = []
        updated_fields: list[str] = []
        for expected in manifest.fields:
            actual = actual_by_name.get(expected.name.casefold())
            if actual is None:
                self._create_field(snapshot.project_id, expected)
                created_fields.append(expected.name)
                continue
            if expected.kind is ProjectFieldKind.SINGLE_SELECT:
                available = {option.name.casefold() for option in actual.options}
                if any(option.casefold() not in available for option in expected.options):
                    self._update_select_options(actual, expected.options)
                    updated_fields.append(expected.name)

        views_by_name = {view.name.casefold(): view for view in snapshot.views}
        created_views: list[str] = []
        for expected in manifest.views:
            actual = views_by_name.get(expected.name.casefold())
            if actual is None:
                self._create_view(snapshot.project_id, expected)
                created_views.append(expected.name)
                continue
            expected_layout = _VIEW_LAYOUT[expected.layout]
            if actual.layout != expected_layout:
                raise ValueError(
                    f"view layout mismatch for {expected.name}: {actual.layout}->{expected_layout}"
                )

        final = self.read_snapshot(target)
        final_views = {view.name.casefold(): view for view in final.views}
        for expected in manifest.views:
            actual = final_views.get(expected.name.casefold())
            if actual is None or actual.layout != _VIEW_LAYOUT[expected.layout]:
                raise RuntimeError(
                    f"GITHUB_PROJECT_SCHEMA_VERIFY_FAILED: view not ready: {expected.name}"
                )
        status = compare_project_schema(
            manifest,
            final.work_fields(),
            project_id="registered-project",
            views_observed=tuple(view.name for view in final.views),
        )
        if not status.ready:
            raise RuntimeError(
                "GITHUB_PROJECT_SCHEMA_VERIFY_FAILED: canonical schema remained incomplete"
            )
        return {
            "ready": True,
            "project_node_id": final.project_id,
            "created_fields": created_fields,
            "updated_fields": updated_fields,
            "created_views": created_views,
            "field_count": len(final.fields),
            "view_count": len(final.views),
        }


class GitHubProjectSchemaAwareBackend:
    def __init__(
        self,
        delegate,
        bindings: Mapping[str, ProjectBinding],
        *,
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

    async def read_schema_views(self, project_binding) -> tuple[str, ...]:
        if not isinstance(project_binding, ProjectBinding):
            raise ValueError("project_binding must be a ProjectBinding")
        configured = self._bindings.get(project_binding.managed_project_id)
        if configured != project_binding:
            raise ValueError("project_binding does not match configured GitHub binding")
        target = ProjectSchemaTarget.from_binding(project_binding)
        return await asyncio.to_thread(self._client.read_views, target)

    async def apply_reconciliation(self, decision, *, idempotency_key: str):
        return await self._delegate.apply_reconciliation(
            decision, idempotency_key=idempotency_key
        )


__all__ = [
    "GitHubProjectSchemaAwareBackend",
    "GitHubProjectSchemaClient",
    "ProjectSchemaTarget",
]
