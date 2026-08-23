from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from kis_mcp.providers.github.projects import schema_commissioning
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


def test_default_runner_decodes_captured_bytes_as_utf8(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return schema_commissioning.subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout='{"title":"café"}'.encode(), stderr=b""
        )

    monkeypatch.setattr(schema_commissioning.subprocess, "run", fake_run)

    result = schema_commissioning._default_runner(("gh", "api"), tmp_path, {})

    assert captured["text"] is False
    assert result.stdout == '{"title":"café"}'


def test_default_runner_fails_closed_on_invalid_utf8(tmp_path: Path) -> None:
    with pytest.raises(UnicodeDecodeError):
        schema_commissioning._default_runner(
            (
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(bytes([0xff]))",
            ),
            tmp_path,
            dict(os.environ),
        )


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
        "number": 1,
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


def _view_items(*, status: str) -> list[dict[str, object]]:
    return [
        {
            "id": 17,
            "fields": [
                {
                    "id": 1001,
                    "name": "Status",
                    "data_type": "single_select",
                    "value": {"name": status},
                }
            ],
        }
    ]


def _included_view_items(
    items: list[dict[str, object]] | None = None,
    *,
    has_next: bool = False,
) -> str:
    headers = ["HTTP/2 200 OK", "content-type: application/json"]
    if has_next:
        headers.append(
            'link: <https://api.github.com/example?after=cursor>; rel="next"'
        )
    return "\r\n".join(headers) + "\r\n\r\n" + json.dumps(items or [])


def test_read_views_rejects_false_green_saved_filter_behavior() -> None:
    runner = QueueRunner(
        (
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
            Result(stdout=_included_view_items(_view_items(status="Todo"))),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is False
    assert views[0].behavior_mismatches == ("Status:Todo",)
    assert "/users/NielPieterse0/projectsV2/1/views/1/items" in runner.calls[1][0]
    assert "fields=1001" in runner.calls[1][0]


@pytest.mark.parametrize(
    "items",
    [
        [],
        _view_items(status="Ready"),
        [
            *_view_items(status="Ready"),
            {"id": 18, "fields": _view_items(status="Ready")[0]["fields"]},
        ],
    ],
)
def test_read_views_accepts_complete_body_only_saved_view_response(
    items: list[dict[str, object]],
) -> None:
    runner = QueueRunner(
        (
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
            Result(stdout=json.dumps(items)),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is True
    assert views[0].behavior_mismatches == ()


def test_read_views_rejects_body_only_page_without_pagination_completeness() -> None:
    items = [
        {"id": item_id, "fields": _view_items(status="Ready")[0]["fields"]}
        for item_id in range(100)
    ]
    runner = QueueRunner(
        (
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
            Result(stdout=json.dumps(items)),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is None
    assert views[0].behavior_mismatches == ("unverified:pagination_evidence",)


@pytest.mark.parametrize(
    ("stdout", "reason"),
    [
        ("", "unverified:empty_response"),
        ("{}", "unverified:malformed_http"),
        ("[", "unverified:malformed_json"),
        ("HTTP/2 200 OK\r\n\r\n", "unverified:empty_body"),
    ],
)
def test_read_views_marks_incomplete_saved_view_response_unverified(
    stdout: str,
    reason: str,
) -> None:
    runner = QueueRunner(
        (
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
            Result(stdout=stdout),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is None
    assert views[0].behavior_mismatches == (reason,)


@pytest.mark.parametrize(
    ("raw_field", "reason"),
    [
        (
            {"id": 1001, "name": "", "value": {"name": "Ready"}},
            "unverified:field_name",
        ),
        (
            {"id": 1001, "name": "Status", "value": {"name": 42}},
            "unverified:single_select_name",
        ),
        (
            {"id": 1001, "name": "Status", "value": {"name": {"raw": 42}}},
            "unverified:single_select_name",
        ),
        (
            {"id": 1001, "name": "Status", "value": {"name": {"html": "Ready"}}},
            "unverified:single_select_name",
        ),
        (
            {"id": 1001, "name": "Status", "value": ["Ready"]},
            "unverified:single_select_value",
        ),
    ],
)
def test_read_views_marks_malformed_saved_view_field_unverified(
    raw_field: dict[str, object],
    reason: str,
) -> None:
    ready_view = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=_included_view_items([{"id": 17, "fields": [raw_field]}])),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is None
    assert views[0].behavior_mismatches == (reason,)


def test_read_views_ignores_well_formed_unrelated_saved_view_fields() -> None:
    ready_view = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    fields = [
        {"id": 2001, "name": "Unrelated", "value": "extra"},
        {"id": 1001, "name": "Status", "value": {"name": "Ready"}},
    ]
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=_included_view_items([{"id": 17, "fields": fields}])),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is True
    assert views[0].behavior_mismatches == ()


def test_read_views_accepts_rest_single_select_raw_name_shape() -> None:
    ready_view = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    fields = [
        {
            "id": 1001,
            "name": "Status",
            "value": {"name": {"html": "Ready", "raw": "Ready"}},
        }
    ]
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=_included_view_items([{"id": 17, "fields": fields}])),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is True
    assert views[0].behavior_mismatches == ()


@pytest.mark.parametrize(
    "fields",
    [
        [
            {"id": 1001, "name": "Status", "value": None},
            {"id": 1001, "name": "Status", "value": {"name": "Ready"}},
        ],
        [
            {"id": 1001, "name": "Status", "value": {"name": "Ready"}},
            {"id": 1001, "name": "Status", "value": None},
        ],
    ],
)
def test_read_views_marks_duplicate_saved_view_fields_unverified(
    fields: list[dict[str, object]],
) -> None:
    ready_view = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=_included_view_items([{"id": 17, "fields": fields}])),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is None
    assert views[0].behavior_mismatches == ("unverified:duplicate_required_field",)


def test_commission_does_not_repair_unverified_saved_view_field_evidence() -> None:
    ready_view = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    malformed_items = _included_view_items(
        [
            {
                "id": 17,
                "fields": [
                    {"id": 1001, "name": "Status", "value": {"name": 42}}
                ],
            }
        ]
    )
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=malformed_items),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    with pytest.raises(
        RuntimeError,
        match=r"canonical schema remained incomplete: 01 Inbox\[unverified:single_select_name\]",
    ):
        _client(runner).commission(target, _manifest())

    assert not any(
        call[0][-1].startswith("query=") and "updateProjectV2View" in call[0][-1]
        for call in runner.calls
    )


def test_read_views_marks_saved_view_api_failure_unverified() -> None:
    runner = QueueRunner(
        (
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
            Result(returncode=1, stderr="temporary provider failure"),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is None
    assert views[0].behavior_mismatches == ("unverified:api_error",)


def test_read_views_ignores_noncanonical_filtered_views() -> None:
    payload = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    views = payload["data"]["user"]["projectV2"]["views"]["nodes"]
    extra = json.loads(json.dumps(views[0]))
    extra.update(
        {
            "id": "extra-view-id",
            "number": 2,
            "name": "Operator Scratch",
            "filter": "status:Todo",
        }
    )
    views.append(extra)
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(payload)),
            Result(stdout=_included_view_items()),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    observed = _client(runner).read_views(target, _manifest())

    assert [view.name for view in observed] == ["01 Inbox"]
    assert len(runner.calls) == 2
    assert "/views/1/items" in str(runner.calls[1][0])
    assert "/views/2/items" not in str(runner.calls)


def test_read_views_follows_bounded_saved_view_pagination() -> None:
    runner = QueueRunner(
        (
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
            Result(stdout=_included_view_items(_view_items(status="Ready"), has_next=True)),
            Result(stdout=_included_view_items(_view_items(status="Ready"))),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is True
    assert views[0].behavior_mismatches == ()
    assert "--paginate" not in runner.calls[1][0]
    assert "--include" in runner.calls[1][0]
    assert "after=cursor" in runner.calls[2][0]


def test_read_views_marks_cyclic_saved_view_pagination_unverified() -> None:
    runner = QueueRunner(
        (
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
            Result(stdout=_included_view_items(_view_items(status="Ready"), has_next=True)),
            Result(stdout=_included_view_items(_view_items(status="Ready"), has_next=True)),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert views[0].behavior_verified is None
    assert views[0].behavior_mismatches == ("unverified:pagination_cycle",)


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
            Result(stdout=_included_view_items()),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    result = _client(runner).commission(target, _manifest())

    assert result["scope"] == "full"
    assert result["ready"] is True
    assert result["fields_ready"] is True
    assert result["views_ready"] is True
    assert result["created_fields"] == ["Priority"]
    assert result["updated_fields"] == ["Status"]
    assert result["created_views"] == ["01 Inbox"]
    assert result["view_behavior"] == [
        {"name": "01 Inbox", "verified": True, "mismatches": []}
    ]
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
            Result(stdout=_included_view_items()),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    views = _client(runner).read_views(target, _manifest())

    assert len(views) == 1
    assert views[0].name == "01 Inbox"
    assert views[0].layout == "table"
    assert views[0].filter == "status:Ready"
    assert views[0].visible_fields == ("Status", "Priority")
    assert views[0].sort_by == ()
    assert views[0].group_by == ()
    assert views[0].vertical_group_by == ()
    assert views[0].behavior_verified is True
    assert views[0].behavior_mismatches == ()


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
            Result(stdout=_included_view_items()),
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


def test_commission_updates_existing_view_layout_in_place() -> None:
    drifted = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    drifted["data"]["user"]["projectV2"]["views"]["nodes"][0]["layout"] = "BOARD_LAYOUT"
    corrected = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(drifted)),
            Result(),
            Result(stdout=json.dumps(corrected)),
            Result(stdout=_included_view_items()),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    result = _client(runner).commission(target, _manifest())

    assert result["ready"] is True
    queries = [call[0][-1].removeprefix("query=") for call in runner.calls]
    update = next(query for query in queries if "updateProjectV2View" in query)
    assert "layout: TABLE_LAYOUT" in update


def test_commission_reapplies_matching_filter_when_saved_view_behavior_is_wrong() -> None:
    ready_view = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=_included_view_items(_view_items(status="Todo"))),
            Result(),
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=_included_view_items()),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    result = _client(runner).commission(target, _manifest())

    assert result["ready"] is True
    assert result["updated_views"] == ["01 Inbox"]
    queries = [
        call[0][-1].removeprefix("query=")
        for call in runner.calls
        if call[0][-1].startswith("query=")
    ]
    repair = next(query for query in queries if "updateProjectV2View" in query)
    assert 'filter: "status:Ready"' in repair


def test_commission_fails_when_saved_view_behavior_remains_wrong_after_repair() -> None:
    ready_view = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="status:Ready",
        visible_fields=("Status", "Priority"),
    )
    wrong_items = _included_view_items(_view_items(status="Todo"))
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=wrong_items),
            Result(),
            Result(stdout=json.dumps(ready_view)),
            Result(stdout=wrong_items),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    with pytest.raises(RuntimeError, match="01 Inbox:behavior"):
        _client(runner).commission(target, _manifest())

    repairs = [
        call
        for call in runner.calls
        if call[0][-1].startswith("query=")
        and "updateProjectV2View" in call[0][-1]
    ]
    assert len(repairs) == 1


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
            Result(stdout=_included_view_items()),
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


def test_fields_scope_commissions_manifest_fields_despite_unrelated_view_drift() -> None:
    before = _snapshot(
        priority_type="",
        include_ready=True,
        include_view=True,
        view_filter="",
        visible_fields=("Status",),
    )
    before_view = before["data"]["user"]["projectV2"]["views"]["nodes"][0]
    before_view["sortByFields"] = {
        "nodes": [
            {
                "direction": "ASC",
                "field": {"__typename": "ProjectV2Field", "id": "status-id", "name": "Status"},
            }
        ],
        "pageInfo": {"hasNextPage": False},
    }
    after = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="",
        visible_fields=("Status",),
    )
    after_view = after["data"]["user"]["projectV2"]["views"]["nodes"][0]
    after_view["sortByFields"] = before_view["sortByFields"]
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(before)),
            Result(stdout="{}"),
            Result(stdout=json.dumps(after)),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    result = _client(runner).commission(target, _manifest(), scope="fields")

    assert result["scope"] == "fields"
    assert result["ready"] is True
    assert result["fields_ready"] is True
    assert result["views_ready"] is None
    assert result["created_fields"] == ["Priority"]
    assert result["updated_fields"] == []
    queries = [call[0][-1].removeprefix("query=") for call in runner.calls]
    assert any("createProjectV2Field" in query for query in queries)
    assert not any("updateProjectV2View" in query for query in queries)
    assert not any("/views/" in part for call in runner.calls for part in call[0])


def test_fields_scope_fails_closed_when_created_field_is_not_observed() -> None:
    before = _snapshot(priority_type="", include_ready=True)
    still_missing = _snapshot(priority_type="", include_ready=True)
    runner = QueueRunner(
        (
            Result(stdout=json.dumps(before)),
            Result(stdout="{}"),
            Result(stdout=json.dumps(still_missing)),
        )
    )
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    with pytest.raises(RuntimeError, match="field not ready after creation: Priority"):
        _client(runner).commission(target, _manifest(), scope="fields")

    assert len(runner.calls) == 3
    queries = [call[0][-1].removeprefix("query=") for call in runner.calls]
    assert sum("createProjectV2Field" in query for query in queries) == 1
    assert not any("updateProjectV2Field" in query for query in queries)
    assert not any("updateProjectV2View" in query for query in queries)


def test_fields_scope_preflights_all_field_refusals_before_any_mutation() -> None:
    payload = _snapshot(priority_type="", include_ready=True)
    manifest = ProjectSchemaManifest(
        portfolio_id="default",
        fields=(
            ProjectFieldSpec("Status", ProjectFieldKind.SINGLE_SELECT, ("Todo", "Ready")),
            ProjectFieldSpec("Priority", ProjectFieldKind.TEXT),
            ProjectFieldSpec("Repository", ProjectFieldKind.REPOSITORY),
        ),
        views=(),
    )
    runner = QueueRunner((Result(stdout=json.dumps(payload)),))
    target = ProjectSchemaTarget(owner="NielPieterse0", owner_type="user", project_number=1)

    with pytest.raises(ValueError, match="built-in repository field cannot be created"):
        _client(runner).commission(target, manifest, scope="fields")

    assert len(runner.calls) == 1


def test_commission_preflights_all_view_refusals_before_any_mutation() -> None:
    payload = _snapshot(
        include_ready=True,
        include_view=True,
        view_filter="",
        visible_fields=("Status", "Priority"),
    )
    views = payload["data"]["user"]["projectV2"]["views"]["nodes"]
    second = json.loads(json.dumps(views[0]))
    second.update({"id": "view-id-2", "number": 2, "name": "02 Programme Table"})
    second["filter"] = ""
    second["groupByFields"] = {
        "nodes": [{"__typename": "ProjectV2Field", "id": "status-id", "name": "Status"}],
        "pageInfo": {"hasNextPage": False},
    }
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

    with pytest.raises(ValueError, match="not safely mutable: group_by"):
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
