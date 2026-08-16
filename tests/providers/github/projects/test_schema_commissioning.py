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

def _snapshot(
    *,
    priority_type: str = "TEXT",
    include_ready: bool = False,
    include_view: bool = False,
    view_filter: str = "",
    visible_fields: tuple[str, ...] = (),
    group_by: tuple[str, ...] = (),
    vertical_group_by: tuple[str, ...] = (),
):
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
            "databaseId": 1001,
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
                "databaseId": 1002,
                "name": "Priority",
                "dataType": priority_type,
            }
        )
    field_ids = {"Status": "status-id", "Priority": "priority-id"}

    def field_node(name: str) -> dict[str, str]:
        return {"__typename": "ProjectV2Field", "id": field_ids[name], "name": name}

    view = {
        "id": "view-id",
        "name": "01 Inbox",
        "layout": "TABLE_LAYOUT",
        "filter": view_filter,
        "configuration": {
            "visibleFields": {
                "nodes": [field_node(name) for name in visible_fields],
                "pageInfo": {"hasNextPage": False},
            }
        },
        "sortByFields": {"nodes": [], "pageInfo": {"hasNextPage": False}},
        "groupByFields": {
            "nodes": [field_node(name) for name in group_by],
            "pageInfo": {"hasNextPage": False},
        },
        "verticalGroupByFields": {
            "nodes": [field_node(name) for name in vertical_group_by],
            "pageInfo": {"hasNextPage": False},
        },
    }
    return {
        "data": {
            "user": {
                "databaseId": 222640156,
                "projectV2": {
                    "id": "project-id",
                    "fields": {"nodes": fields, "pageInfo": {"hasNextPage": False}},
                    "views": {
                        "nodes": ([view] if include_view else []),
                        "pageInfo": {"hasNextPage": False},
                    },
                },
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
        views=(
            ProjectViewSpec(
                "01 Inbox",
                "Primary intake view",
                filter="status:Ready",
                visible_fields=("Status", "Priority"),
            ),
        ),
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
            Result(stdout=json.dumps(_snapshot(include_ready=False))),
            Result(),
            Result(stdout='{"value":{"id":1}}'),
            Result(
                stdout=json.dumps(
                    _snapshot(
                        include_ready=True,
                        include_view=True,
                        view_filter="status:Ready",
                        visible_fields=("Status", "Priority"),
                    )
                )
            ),
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


def test_read_views_returns_semantic_observations() -> None:
    runner = QueueRunner(
        (
            Result(
                stdout=json.dumps(
                    _snapshot(
                        include_view=True,
                        view_filter="status:Ready",
                        visible_fields=("Status", "Priority"),
                    )
                )
            ),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target)

    assert len(views) == 1
    assert views[0].name == "01 Inbox"
    assert views[0].layout == "table"
    assert views[0].filter == "status:Ready"
    assert views[0].visible_fields == ("Status", "Priority")
    assert views[0].sort_by == ()
    assert views[0].group_by == ()
    assert views[0].vertical_group_by == ()


def test_commission_updates_existing_view_filter_and_visible_fields_in_place() -> None:
    runner = QueueRunner(
        (
            Result(
                stdout=json.dumps(
                    _snapshot(
                        include_ready=True,
                        include_view=True,
                        view_filter="",
                        visible_fields=("Status",),
                    )
                )
            ),
            Result(),
            Result(
                stdout=json.dumps(
                    _snapshot(
                        include_ready=True,
                        include_view=True,
                        view_filter="status:Ready",
                        visible_fields=("Status", "Priority"),
                    )
                )
            ),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    result = _client(runner).commission(target, _manifest())

    assert result["ready"] is True
    assert result["updated_views"] == ["01 Inbox"]
    queries = [call[0][-1].removeprefix("query=") for call in runner.calls]
    update = next(query for query in queries if "updateProjectV2View" in query)
    assert 'viewId: "view-id"' in update
    assert 'filter: "status:Ready"' in update
    assert 'visibleFieldIds: ["status-id", "priority-id"]' in update
    assert "deleteProjectV2View" not in update


def test_commission_creates_missing_view_with_fixed_rest_semantics() -> None:
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(_snapshot(include_ready=True))),
            Result(stdout='{"value":{"id":1}}'),
            Result(
                stdout=json.dumps(
                    _snapshot(
                        include_ready=True,
                        include_view=True,
                        view_filter="status:Ready",
                        visible_fields=("Status", "Priority"),
                    )
                )
            ),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    result = _client(runner).commission(target, _manifest())

    assert result["created_views"] == ["01 Inbox"]
    create = runner.calls[1][0]
    assert create[:5] == ("gh", "api", "--hostname", "github.com", "--method")
    assert "POST" in create
    assert "/users/222640156/projectsV2/1/views" in create
    assert "name=01 Inbox" in create
    assert "layout=table" in create
    assert "filter=status:Ready" in create
    assert "visible_fields[]=1001" in create
    assert "visible_fields[]=1002" in create


def test_commission_preflights_all_view_refusals_before_any_mutation() -> None:
    payload = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="",
        visible_fields=("Status", "Priority"),
    )
    views = payload["data"]["user"]["projectV2"]["views"]["nodes"]
    second = json.loads(json.dumps(views[0]))
    second.update({"id": "view-id-2", "name": "02 Programme Table", "layout": "BOARD_LAYOUT"})
    views.append(second)
    manifest = ProjectSchemaManifest(
        portfolio_id="default",
        fields=_manifest().fields,
        views=(
            _manifest().views[0],
            ProjectViewSpec(
                "02 Programme Table",
                "Active records",
                layout="table",
                visible_fields=("Status", "Priority"),
            ),
        ),
    )
    runner = QueueRunner((Result(stdout=json.dumps(payload)),))
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    with pytest.raises(ValueError, match="view layout mismatch for 02 Programme Table"):
        _client(runner).commission(target, manifest)

    assert len(runner.calls) == 1


def test_missing_view_owner_database_id_refuses_before_mutation() -> None:
    payload = _snapshot(include_ready=True)
    payload["data"]["user"]["databaseId"] = None
    runner = QueueRunner((Result(stdout=json.dumps(payload)),))
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    with pytest.raises(ValueError, match="registered user database ID"):
        _client(runner).commission(target, _manifest())

    assert len(runner.calls) == 1
