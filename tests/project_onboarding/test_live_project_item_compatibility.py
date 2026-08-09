from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from kis_mcp.providers.github.project_management import GitHubProjectManagementAdapter
from kis_mcp.providers.github.projects import GitHubProjectInventoryAdapter
from kis_mcp.work_management import (
    ProjectBinding,
    ProjectItemKind,
    ProjectOwnerType,
    ReconciliationAction,
    ReconciliationDecision,
)


class FakeCaller:
    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any:
        self.calls.append((name, dict(arguments)))
        return self.responses.pop(0)


def binding() -> ProjectBinding:
    return ProjectBinding(
        binding_id="github-default",
        managed_project_id="kis-mcp",
        provider_id="github-mcp",
        owner="NielPieterse0",
        owner_type=ProjectOwnerType.USER,
        project_number=1,
        repository="NielPieterse0/kis-mcp",
    )


def test_inventory_normalizes_live_rest_project_item_shape() -> None:
    caller = FakeCaller(
        {"id": 25071419, "node_id": "PVT_1", "title": "KIS Work Management", "public": False},
        {
            "fields": [
                {
                    "id": 377123158,
                    "node_id": "PVTSSF_1",
                    "name": "Status",
                    "data_type": "single_select",
                    "options": [
                        {"id": "f75ad846", "name": {"raw": "Todo"}},
                        {"id": "47fc9ee4", "name": {"raw": "In Progress"}},
                        {"id": "98236657", "name": {"raw": "Done"}},
                    ],
                }
            ],
            "pageInfo": {"hasNextPage": False},
        },
        {
            "items": [
                {
                    "id": 225838119,
                    "node_id": "PVTI_1",
                    "content_type": "Issue",
                    "content": {
                        "number": 102,
                        "title": "085: Commission GitHub Projects writes",
                        "state": "open",
                        "html_url": "https://github.com/NielPieterse0/kis-mcp/issues/102",
                        "repository": "NielPieterse0/kis-mcp",
                    },
                    "fields": [
                        {
                            "id": 377123158,
                            "name": "Status",
                            "data_type": "single_select",
                            "value": {"id": "47fc9ee4", "name": "In Progress"},
                        }
                    ],
                }
            ],
            "pageInfo": {"hasNextPage": False},
        },
    )

    inventory = asyncio.run(
        GitHubProjectInventoryAdapter(caller).read_inventory(
            binding(), field_names=("Status",), item_limit=50
        )
    )

    item = inventory.items[0]
    assert item.item_id == "225838119"
    assert item.kind is ProjectItemKind.ISSUE
    assert item.repository == "NielPieterse0/kis-mcp"
    assert item.number == 102
    assert item.url == "https://github.com/NielPieterse0/kis-mcp/issues/102"
    assert [(value.field_name, value.value) for value in item.field_values] == [
        ("Status", "In Progress")
    ]


def test_reconciliation_prefers_numeric_item_id_from_live_add_response() -> None:
    caller = FakeCaller(
        {"items": [], "pageInfo": {"hasNextPage": False}},
        {
            "id": "PVTI_lAHODUU4HM4Bfo87zg12BCc",
            "item_id": 225838119,
            "updated_at": "2026-08-09T12:02:10Z",
        },
        {
            "id": 225838119,
            "node_id": "PVTI_lAHODUU4HM4Bfo87zg12BCc",
            "updated_at": "2026-08-09T12:03:24Z",
        },
    )
    adapter = GitHubProjectManagementAdapter(
        caller,
        {"kis-mcp": binding()},
        available_tools=("projects_get", "projects_list", "projects_write"),
    )
    decision = ReconciliationDecision(
        project_id="kis-mcp",
        record_id="GH-ISSUE-102",
        action=ReconciliationAction.CREATE,
        changed_fields=("Status",),
        desired_fields=(("Status", "In Progress"),),
        source_repository="NielPieterse0/kis-mcp",
        source_number=102,
        source_kind="issue",
        reason="commission first Project item",
    )

    outcome = asyncio.run(
        adapter.apply_reconciliation(decision, idempotency_key="commission-issue-102")
    )

    assert outcome.applied is True
    assert outcome.success is True
    assert caller.calls[1][0] == "projects_write"
    assert caller.calls[1][1]["method"] == "add_project_item"
    assert caller.calls[2][0] == "projects_write"
    assert caller.calls[2][1]["method"] == "update_project_item"
    assert caller.calls[2][1]["item_id"] == "225838119"
