from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import pytest

from kis_mcp.providers.github.projects import (
    GitHubProjectInventoryAdapter,
    GitHubProjectInventoryError,
)
from kis_mcp.work_management import (
    ProjectBinding,
    ProjectFieldKind,
    ProjectItemKind,
    ProjectOwnerType,
)


class FakeCaller:
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


def page_info(has_next: bool, cursor: str | None = None) -> dict[str, Any]:
    return {"hasNextPage": has_next, "nextCursor": cursor}


def test_inventory_uses_fixed_read_calls_and_normalizes_results() -> None:
    caller = FakeCaller(
        {
            "result": {
                "project": {
                    "id": "PVT_1",
                    "title": "KIS Portfolio",
                    "closed": False,
                }
            }
        },
        {
            "fields": [
                {
                    "id": "F_STATUS",
                    "name": "Status",
                    "dataType": "SINGLE_SELECT",
                    "options": [
                        {"id": "O_ACTIVE", "name": "Active"},
                        {"id": "O_DONE", "name": "Done"},
                    ],
                }
            ],
            "pageInfo": page_info(False),
        },
        {
            "items": [
                {
                    "id": "I_1",
                    "type": "ISSUE",
                    "updatedAt": "2026-08-14T00:42:00Z",
                    "content": {
                        "title": "First issue",
                        "number": 7,
                        "state": "OPEN",
                        "url": "https://github.com/ExampleOwner/alpha/issues/7",
                        "repository": {"nameWithOwner": "ExampleOwner/alpha"},
                    },
                    "fieldValues": {"Status": "Active"},
                }
            ],
            "pageInfo": page_info(False),
        },
    )

    inventory = asyncio.run(
        GitHubProjectInventoryAdapter(caller).read_inventory(
            binding(), field_names=("Status",), item_limit=25
        )
    )

    assert inventory.title == "KIS Portfolio"
    assert inventory.project_node_id == "PVT_1"
    assert inventory.fields[0].kind is ProjectFieldKind.SINGLE_SELECT
    assert [option.name for option in inventory.fields[0].options] == ["Active", "Done"]
    assert inventory.items[0].kind is ProjectItemKind.ISSUE
    assert inventory.items[0].repository == "ExampleOwner/alpha"
    assert inventory.items[0].revision == "2026-08-14T00:42:00Z"
    assert inventory.items[0].field_values[0].value == "Active"

    assert caller.calls == [
        (
            "projects_get",
            {
                "method": "get_project",
                "owner": "ExampleOwner",
                "owner_type": "user",
                "project_number": 12,
            },
        ),
        (
            "projects_list",
            {
                "method": "list_project_fields",
                "owner": "ExampleOwner",
                "owner_type": "user",
                "project_number": 12,
                "per_page": 50,
            },
        ),
        (
            "projects_list",
            {
                "method": "list_project_items",
                "owner": "ExampleOwner",
                "owner_type": "user",
                "project_number": 12,
                "per_page": 25,
                "field_names": ["Status"],
            },
        ),
    ]


def test_inventory_normalizes_live_github_project_rest_shapes() -> None:
    caller = FakeCaller(
        {
            "id": 25071419,
            "node_id": "PVT_kwHODUU4HM4Bfo87",
            "title": "KIS Work Management",
            "public": False,
        },
        {
            "fields": [
                {
                    "id": 377123158,
                    "node_id": "PVTSSF_lAHODUU4HM4Bfo87zhZ6cVY",
                    "name": "Status",
                    "data_type": "single_select",
                    "options": [
                        {
                            "id": "f75ad846",
                            "name": {"html": "Todo", "raw": "Todo"},
                        },
                        {
                            "id": "47fc9ee4",
                            "name": {
                                "html": "In Progress",
                                "raw": "In Progress",
                            },
                        },
                        {
                            "id": "98236657",
                            "name": {"html": "Done", "raw": "Done"},
                        },
                    ],
                }
            ],
            "pageInfo": page_info(False),
        },
        {"items": [], "pageInfo": page_info(False)},
    )

    inventory = asyncio.run(
        GitHubProjectInventoryAdapter(caller).read_inventory(
            binding(), field_names=("Status",), item_limit=50
        )
    )

    assert inventory.project_node_id == "PVT_kwHODUU4HM4Bfo87"
    assert inventory.fields[0].field_id == "PVTSSF_lAHODUU4HM4Bfo87zhZ6cVY"
    assert [option.name for option in inventory.fields[0].options] == [
        "Done",
        "In Progress",
        "Todo",
    ]
    assert inventory.items == ()


def test_inventory_paginates_and_reports_truncation() -> None:
    caller = FakeCaller(
        {"project": {"id": "PVT_1", "title": "Programme", "closed": False}},
        {"fields": [], "pageInfo": page_info(False)},
        {
            "items": [
                {"id": "I_1", "type": "DRAFT", "title": "One"},
                {"id": "I_2", "type": "DRAFT", "title": "Two"},
            ],
            "pageInfo": page_info(True, "CURSOR_2"),
        },
        {
            "items": [
                {"id": "I_3", "type": "DRAFT", "title": "Three"},
                {"id": "I_4", "type": "DRAFT", "title": "Four"},
            ],
            "pageInfo": page_info(True, "CURSOR_3"),
        },
    )

    inventory = asyncio.run(
        GitHubProjectInventoryAdapter(caller, page_size=2).read_inventory(
            binding(), item_limit=3
        )
    )

    assert [item.item_id for item in inventory.items] == ["I_1", "I_2", "I_3"]
    assert inventory.truncated is True
    assert inventory.next_cursor == "CURSOR_3"

    assert caller.calls[-1] == (
        "projects_list",
        {
            "method": "list_project_items",
            "owner": "ExampleOwner",
            "owner_type": "user",
            "project_number": 12,
            "per_page": 1,
            "after": "CURSOR_2",
        },
    )


def test_inventory_accepts_list_field_values_and_result_objects() -> None:
    class Result:
        def __init__(self, data: dict[str, Any]) -> None:
            self.data = data

    caller = FakeCaller(
        Result({"project": {"id": "PVT_1", "title": "Programme"}}),
        Result({"fields": [], "pageInfo": page_info(False)}),
        Result(
            {
                "items": [
                    {
                        "id": "I_1",
                        "type": "PULL_REQUEST",
                        "content": {
                            "title": "PR one",
                            "number": 8,
                            "repository": "ExampleOwner/alpha",
                        },
                        "field_values": [
                            {"field_name": "Priority", "value": "High"},
                            {"field": {"name": "Estimate", "id": "F_EST"}, "number": 5},
                        ],
                    }
                ],
                "pageInfo": page_info(False),
            }
        ),
    )

    inventory = asyncio.run(
        GitHubProjectInventoryAdapter(caller).read_inventory(binding())
    )

    item = inventory.items[0]
    assert item.kind is ProjectItemKind.PULL_REQUEST
    assert [(value.field_name, value.value) for value in item.field_values] == [
        ("Estimate", 5),
        ("Priority", "High"),
    ]


def test_invalid_response_is_bounded_and_redacted() -> None:
    caller = FakeCaller({"project": {"id": "PVT_1"}})

    with pytest.raises(
        GitHubProjectInventoryError,
        match="GITHUB_PROJECT_INVENTORY_INVALID_RESPONSE: get_project",
    ) as captured:
        asyncio.run(GitHubProjectInventoryAdapter(caller).read_inventory(binding()))

    assert "secret-value" not in str(captured.value)


def test_tool_failure_reports_type_without_raw_message() -> None:
    caller = FakeCaller(RuntimeError("secret-value"))

    with pytest.raises(
        GitHubProjectInventoryError,
        match="GITHUB_PROJECT_INVENTORY_FAILED: get_project: RuntimeError",
    ) as captured:
        asyncio.run(GitHubProjectInventoryAdapter(caller).read_inventory(binding()))

    assert "secret-value" not in str(captured.value)


def test_adapter_rejects_wrong_provider_and_invalid_limits() -> None:
    wrong = ProjectBinding(
        binding_id="future-default",
        managed_project_id="alpha-project",
        provider_id="future-provider",
        owner="owner",
        owner_type=ProjectOwnerType.ORG,
        project_number=1,
    )

    with pytest.raises(ValueError, match="github-mcp"):
        asyncio.run(GitHubProjectInventoryAdapter(FakeCaller()).read_inventory(wrong))

    with pytest.raises(ValueError, match="item_limit"):
        asyncio.run(
            GitHubProjectInventoryAdapter(FakeCaller()).read_inventory(
                binding(), item_limit=0
            )
        )
