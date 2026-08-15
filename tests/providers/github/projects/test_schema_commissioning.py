from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from kis_mcp.providers.github.projects.schema_commissioning import (
    GitHubProjectSchemaClient,
    ProjectSchemaTarget,
)
from kis_mcp.work_management.backend import ProjectFieldKind
from kis_mcp.work_management.schema import (
    ProjectFieldSpec,
    ProjectSchemaManifest,
    ProjectViewSpec,
)


@dataclass
class Result:
    stdout: str = "{}"
    stderr: str = ""
    returncode: int = 0


class QueueRunner:
    def __init__(self, results: tuple[Result, ...]) -> None:
        self.results = list(results)
        self.calls: list[tuple[tuple[str, ...], Path, dict[str, str]]] = []

    def __call__(self, args, cwd, env):
        self.calls.append((tuple(args), cwd, dict(env)))
        if not self.results:
            raise AssertionError(f"unexpected command: {args}")
        return self.results.pop(0)

def _snapshot(*, priority_type: str = "TEXT", include_ready: bool = False, include_view: bool = False):
    options = [
        {"id": "todo-id", "name": "Todo", "color": "GRAY", "description": "existing"}
    ]
    if include_ready:
        options.append(
            {"id": "ready-id", "name": "Ready", "color": "GREEN", "description": ""}
        )
    fields = [
        {
            "__typename": "ProjectV2SingleSelectField",
            "id": "status-id",
            "name": "Status",
            "dataType": "SINGLE_SELECT",
            "options": options,
        }
    ]
    if priority_type:
        fields.append(
            {
                "__typename": "ProjectV2Field",
                "id": "priority-id",
                "name": "Priority",
                "dataType": priority_type,
            }
        )
    return {
        "data": {
            "user": {
                "projectV2": {
                    "id": "project-id",
                    "fields": {"nodes": fields, "pageInfo": {"hasNextPage": False}},
                    "views": {
                        "nodes": ([{"id": "view-id", "name": "01 Inbox", "layout": "TABLE_LAYOUT"}] if include_view else []),
                        "pageInfo": {"hasNextPage": False},
                    },
                }
            }
        }
    }


def _manifest() -> ProjectSchemaManifest:
    return ProjectSchemaManifest(
        portfolio_id="default",
        fields=(
            ProjectFieldSpec("Status", ProjectFieldKind.SINGLE_SELECT, ("Todo", "Ready")),
            ProjectFieldSpec("Priority", ProjectFieldKind.TEXT),
        ),
        views=(ProjectViewSpec("01 Inbox", "Primary intake view"),),
    )


def _client(runner: QueueRunner) -> GitHubProjectSchemaClient:
    return GitHubProjectSchemaClient(
        gh_config_dir=Path(r"C:\Projects\.kis-mcp\github-cli"),
        cwd=Path(r"C:\Projects\kis-mcp"),
        runner=runner,
    )

def test_commission_preserves_existing_option_ids_and_verifies_final_state() -> None:
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(_snapshot(priority_type="", include_ready=False))),
            Result(),
            Result(),
            Result(),
            Result(stdout=json.dumps(_snapshot(include_ready=True, include_view=True))),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    result = _client(runner).commission(target, _manifest())

    assert result["ready"] is True
    assert result["created_fields"] == ["Priority"]
    assert result["updated_fields"] == ["Status"]
    assert result["created_views"] == ["01 Inbox"]
    queries = [call[0][-1].removeprefix("query=") for call in runner.calls]
    update = next(query for query in queries if "updateProjectV2Field" in query)
    assert 'id: "todo-id"' in update
    assert 'name: "Todo"' in update
    assert 'name: "Ready"' in update
    assert all("GH_TOKEN" not in call[2] for call in runner.calls)


def test_commission_refuses_incompatible_field_type_before_mutation() -> None:
    runner = QueueRunner((Result(stdout=json.dumps(_snapshot(priority_type="SINGLE_SELECT"))),))
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    with pytest.raises(ValueError, match="field type mismatch"):
        _client(runner).commission(target, _manifest())

    assert len(runner.calls) == 1
