from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import pytest

from kis_mcp.providers.github.project_management import (
    GitHubProjectCapabilities,
    GitHubProjectManagementAdapter,
    GitHubProjectManagementError,
    detect_github_project_capabilities,
)
from kis_mcp.work_management import (
    ProjectBinding,
    ProjectFieldKind,
    ProjectOwnerType,
    ReconciliationAction,
    ReconciliationDecision,
)


class Caller:
    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any:
        self.calls.append((name, dict(arguments)))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def binding() -> ProjectBinding:
    return ProjectBinding(
        binding_id="github-default",
        managed_project_id="alpha-project",
        provider_id="github-mcp",
        owner="ExampleOwner",
        owner_type=ProjectOwnerType.USER,
        project_number=12,
        repository="ExampleOwner/alpha",
    )


def decision(
    action: ReconciliationAction,
    *,
    changed_fields: tuple[str, ...] = ("Status",),
    desired_fields: tuple[tuple[str, object], ...] = (("Status", "Active"),),
    external_id: str | None = "I_1",
    observed_revision: str | None = "2026-08-07T00:00:00Z",
) -> ReconciliationDecision:
    return ReconciliationDecision(
        project_id="alpha-project",
        record_id="TASK-1",
        action=action,
        changed_fields=changed_fields,
        desired_fields=desired_fields,
        external_id=external_id,
        source_repository="ExampleOwner/alpha",
        source_number=7,
        source_kind="issue",
        observed_revision=observed_revision,
        reason="test decision",
    )


def test_capability_detection_is_exact_and_excludes_delete() -> None:
    capabilities = detect_github_project_capabilities(
        ("projects_get", "projects_list", "projects_write", "delete_project")
    )

    assert capabilities == GitHubProjectCapabilities(
        read_inventory=True,
        add_item=True,
        update_item=True,
        built_in_workflows=False,
        available_tools=("projects_get", "projects_list", "projects_write"),
    )
    assert "delete" not in " ".join(capabilities.available_tools)


def test_missing_read_or_write_tools_disable_only_affected_operations() -> None:
    read_only = detect_github_project_capabilities(("projects_get", "projects_list"))
    write_only = detect_github_project_capabilities(("projects_write",))

    assert read_only.read_inventory is True
    assert read_only.add_item is False
    assert read_only.update_item is False
    assert write_only.read_inventory is False
    assert write_only.add_item is False
    assert write_only.update_item is False


def test_update_preflights_revision_then_updates_changed_fields() -> None:
    caller = Caller(
        {
            "item": {
                "id": "I_1",
                "updatedAt": "2026-08-07T00:00:00Z",
                "title": "Task one",
            }
        },
        {"item": {"id": "I_1", "updatedAt": "2026-08-07T00:01:00Z"}},
    )
    adapter = GitHubProjectManagementAdapter(
        caller,
        {"alpha-project": binding()},
        available_tools=("projects_get", "projects_list", "projects_write"),
    )

    result = asyncio.run(
        adapter.apply_reconciliation(
            decision(ReconciliationAction.UPDATE),
            idempotency_key="reconcile-1:TASK-1",
        )
    )

    assert result.success is True
    assert result.applied is True
    assert result.provider_revision == "2026-08-07T00:01:00Z"
    assert caller.calls == [
        (
            "projects_get",
            {
                "method": "get_project_item",
                "owner": "ExampleOwner",
                "owner_type": "user",
                "project_number": 12,
                "item_id": "I_1",
                "field_names": ["Status"],
            },
        ),
        (
            "projects_write",
            {
                "method": "update_project_item",
                "owner": "ExampleOwner",
                "owner_type": "user",
                "project_number": 12,
                "item_id": "I_1",
                "updated_field": {"name": "Status", "value": "Active"},
            },
        ),
    ]


def test_revision_conflict_prevents_write() -> None:
    caller = Caller(
        {
            "item": {
                "id": "I_1",
                "updatedAt": "2026-08-07T00:02:00Z",
                "title": "Task one",
            }
        }
    )
    adapter = GitHubProjectManagementAdapter(
        caller,
        {"alpha-project": binding()},
        available_tools=("projects_get", "projects_list", "projects_write"),
    )

    result = asyncio.run(
        adapter.apply_reconciliation(
            decision(ReconciliationAction.UPDATE),
            idempotency_key="reconcile-2:TASK-1",
        )
    )

    assert result.success is False
    assert result.applied is False
    assert result.action is ReconciliationAction.CONFLICT
    assert result.provider_revision == "2026-08-07T00:02:00Z"
    assert len(caller.calls) == 1


def test_create_adds_existing_issue_then_updates_fields() -> None:
    caller = Caller(
        {"items": [], "pageInfo": {"hasNextPage": False, "nextCursor": None}},
        {"item": {"id": "I_9", "updatedAt": "2026-08-07T00:03:00Z"}},
        {"item": {"id": "I_9", "updatedAt": "2026-08-07T00:04:00Z"}},
    )
    adapter = GitHubProjectManagementAdapter(
        caller,
        {"alpha-project": binding()},
        available_tools=("projects_get", "projects_list", "projects_write"),
    )

    result = asyncio.run(
        adapter.apply_reconciliation(
            decision(
                ReconciliationAction.CREATE,
                external_id=None,
                observed_revision=None,
            ),
            idempotency_key="reconcile-3:TASK-1",
        )
    )

    assert result.success is True
    assert result.provider_revision == "2026-08-07T00:04:00Z"
    assert caller.calls[0] == (
        "projects_list",
        {
            "method": "list_project_items",
            "owner": "ExampleOwner",
            "owner_type": "user",
            "project_number": 12,
            "per_page": 50,
            "field_names": ["Status"],
        },
    )
    assert caller.calls[1] == (
        "projects_write",
        {
            "method": "add_project_item",
            "owner": "ExampleOwner",
            "owner_type": "user",
            "project_number": 12,
            "item_owner": "ExampleOwner",
            "item_repo": "alpha",
            "item_type": "issue",
            "issue_number": 7,
        },
    )
    assert caller.calls[2][1]["item_id"] == "I_9"


def test_create_deduplicates_existing_source_after_restart() -> None:
    caller = Caller(
        {
            "items": [
                {
                    "id": "I_EXISTING",
                    "type": "ISSUE",
                    "content": {
                        "title": "Existing issue",
                        "number": 7,
                        "repository": {"nameWithOwner": "ExampleOwner/alpha"},
                    },
                    "fieldValues": {"Status": "Inbox"},
                }
            ],
            "pageInfo": {"hasNextPage": False, "nextCursor": None},
        },
        {
            "item": {
                "id": "I_EXISTING",
                "updatedAt": "2026-08-07T00:00:00Z",
            }
        },
        {
            "item": {
                "id": "I_EXISTING",
                "updatedAt": "2026-08-07T00:01:00Z",
            }
        },
    )
    adapter = GitHubProjectManagementAdapter(
        caller,
        {"alpha-project": binding()},
        available_tools=("projects_get", "projects_list", "projects_write"),
    )

    result = asyncio.run(
        adapter.apply_reconciliation(
            decision(
                ReconciliationAction.CREATE,
                external_id=None,
                observed_revision=None,
            ),
            idempotency_key="restart-safe-key",
        )
    )

    assert result.success is True
    assert [name for name, _arguments in caller.calls] == [
        "projects_list",
        "projects_get",
        "projects_write",
    ]
    assert all(
        arguments.get("method") != "add_project_item"
        for _name, arguments in caller.calls
    )
    assert caller.calls[-1][1]["item_id"] == "I_EXISTING"


def test_idempotency_replay_returns_same_outcome_without_new_calls() -> None:
    caller = Caller(
        {"item": {"id": "I_1", "updatedAt": "2026-08-07T00:00:00Z"}},
        {"item": {"id": "I_1", "updatedAt": "2026-08-07T00:01:00Z"}},
    )
    adapter = GitHubProjectManagementAdapter(
        caller,
        {"alpha-project": binding()},
        available_tools=("projects_get", "projects_list", "projects_write"),
    )
    command = decision(ReconciliationAction.UPDATE)

    first = asyncio.run(
        adapter.apply_reconciliation(command, idempotency_key="same-key")
    )
    repeated = asyncio.run(
        adapter.apply_reconciliation(command, idempotency_key="same-key")
    )

    assert repeated == first
    assert len(caller.calls) == 2


def test_reused_idempotency_key_with_different_command_conflicts() -> None:
    caller = Caller(
        {"item": {"id": "I_1", "updatedAt": "2026-08-07T00:00:00Z"}},
        {"item": {"id": "I_1", "updatedAt": "2026-08-07T00:01:00Z"}},
    )
    adapter = GitHubProjectManagementAdapter(
        caller,
        {"alpha-project": binding()},
        available_tools=("projects_get", "projects_list", "projects_write"),
    )
    asyncio.run(
        adapter.apply_reconciliation(
            decision(ReconciliationAction.UPDATE),
            idempotency_key="shared-key",
        )
    )

    conflicting = asyncio.run(
        adapter.apply_reconciliation(
            decision(
                ReconciliationAction.UPDATE,
                desired_fields=(("Status", "Done"),),
            ),
            idempotency_key="shared-key",
        )
    )

    assert conflicting.success is False
    assert conflicting.action is ReconciliationAction.CONFLICT
    assert "idempotency" in (conflicting.message or "")
    assert len(caller.calls) == 2


def test_missing_capability_is_bounded_and_no_raw_provider_error_leaks() -> None:
    adapter = GitHubProjectManagementAdapter(
        Caller(),
        {"alpha-project": binding()},
        available_tools=("projects_get", "projects_list"),
    )
    unsupported = asyncio.run(
        adapter.apply_reconciliation(
            decision(ReconciliationAction.UPDATE),
            idempotency_key="unsupported-key",
        )
    )
    assert unsupported.success is False
    assert unsupported.action is ReconciliationAction.UNSUPPORTED

    failing = GitHubProjectManagementAdapter(
        Caller(RuntimeError("secret-token")),
        {"alpha-project": binding()},
        available_tools=("projects_get", "projects_list", "projects_write"),
    )
    with pytest.raises(GitHubProjectManagementError) as captured:
        asyncio.run(
            failing.apply_reconciliation(
                decision(ReconciliationAction.UPDATE),
                idempotency_key="failure-key",
            )
        )
    assert "RuntimeError" in str(captured.value)
    assert "secret-token" not in str(captured.value)


def test_adapter_exposes_no_delete_operation() -> None:
    assert not hasattr(GitHubProjectManagementAdapter, "delete")
    assert not hasattr(GitHubProjectManagementAdapter, "delete_project_item")


def test_read_schema_fields_uses_bounded_project_field_inventory() -> None:
    caller = Caller(
        {
            "fields": [
                {
                    "id": 101,
                    "node_id": "FIELD_STATUS",
                    "name": "Status",
                    "data_type": "single_select",
                    "options": [
                        {"id": "todo", "name": {"raw": "Todo"}},
                        {"id": "done", "name": {"raw": "Done"}},
                    ],
                },
                {
                    "id": 102,
                    "node_id": "FIELD_CHANGE",
                    "name": "Change ID",
                    "data_type": "text",
                },
            ],
            "pageInfo": {"hasNextPage": False},
        }
    )
    adapter = GitHubProjectManagementAdapter(
        caller,
        {"alpha-project": binding()},
        available_tools=("projects_get", "projects_list", "projects_write"),
    )

    fields = asyncio.run(adapter.read_schema_fields(binding()))

    assert [item.name for item in fields] == ["Change ID", "Status"]
    assert fields[0].kind is ProjectFieldKind.TEXT
    assert fields[1].kind is ProjectFieldKind.SINGLE_SELECT
    assert [option.name for option in fields[1].options] == ["Done", "Todo"]
    assert caller.calls == [
        (
            "projects_list",
            {
                "method": "list_project_fields",
                "owner": "ExampleOwner",
                "owner_type": "user",
                "project_number": 12,
                "per_page": 50,
            },
        )
    ]
