from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastmcp import FastMCP

from kis_mcp.workflows.project_management import register_project_management_tools


class Service:
    async def read_inventory(self, project_id: str, *, field_names=(), item_limit=100):
        return SimpleNamespace(
            to_json_dict=lambda: {
                "project_id": project_id,
                "field_names": list(field_names),
                "item_limit": item_limit,
            }
        )

    async def next_work(self, project_id: str, *, item_limit=100):
        return SimpleNamespace(
            to_json_dict=lambda: {
                "project_id": project_id,
                "item_limit": item_limit,
                "selected": {"number": 7},
                "complete": True,
            }
        )

    async def take_next_work(self, project_id, execution_owner, **kwargs):
        return {
            "mode": "apply" if kwargs.get("apply") else "preview",
            "project_id": project_id,
            "execution_owner": execution_owner,
        }

    async def claim_work(
        self, project_id, repository, issue_number, execution_owner, **kwargs
    ):
        return {
            "mode": "apply" if kwargs.get("apply") else "preview",
            "project_id": project_id,
            "repository": repository,
            "issue_number": issue_number,
            "execution_owner": execution_owner,
        }

    async def release_work(
        self, project_id, repository, issue_number, expected_owner, **kwargs
    ):
        return {
            "mode": "apply" if kwargs.get("apply") else "preview",
            "released": expected_owner,
        }

    async def transition_work(
        self, project_id, repository, issue_number, target, **kwargs
    ):
        return {
            "mode": "apply" if kwargs.get("apply") else "preview",
            "target": target.value,
        }

    async def sync_change_classification(
        self, project_id, repository, issue_number, change_id, **kwargs
    ):
        return {
            "mode": "apply" if kwargs.get("apply") else "preview",
            "change_id": change_id,
        }

    async def complete_work(
        self, project_id, repository, issue_number, record, **kwargs
    ):
        return {
            "mode": "apply" if kwargs.get("apply") else "preview",
            "record_id": record.record_id,
        }

    async def schema_plan(self, project_id: str):
        return SimpleNamespace(
            to_json_dict=lambda: {
                "project_id": project_id,
                "portfolio_id": "default",
                "ready": False,
                "automatic_ready": False,
                "actions": [{"kind": "create_field", "target": "Effort"}],
            }
        )

    async def schema_status(self, project_id: str):
        return SimpleNamespace(
            to_json_dict=lambda: {
                "project_id": project_id,
                "ready": False,
                "fields_ready": False,
                "views_ready": None,
                "missing_fields": ["Record Type"],
            }
        )

    async def reconcile(
        self,
        project_id,
        desired,
        observed,
        *,
        supported_fields,
        apply=False,
        idempotency_key=None,
    ):
        return (
            SimpleNamespace(
                to_json_dict=lambda: {
                    "project_id": project_id,
                    "record_id": desired[0].record_id,
                    "action": "update",
                    "applied": apply,
                    "success": True,
                    "idempotency_key": idempotency_key,
                    "supported_fields": list(supported_fields),
                    "observed_count": len(observed),
                }
            ),
        )

    def portfolio_status(self, records, **kwargs):
        return SimpleNamespace(
            to_json_dict=lambda: {
                "total_records": len(records),
                "traceability_gaps": kwargs.get("traceability_gaps", {}),
                "records": [item.to_json_dict() for item in records],
            }
        )

    def persist_review_artifact(self, project_id, manifest, kind, content, **kwargs):
        return SimpleNamespace(
            to_json_dict=lambda: {
                "project_id": project_id,
                "review_id": manifest.review_id,
                "kind": kind.value,
                "content_length": len(content),
                "expected_sha256": kwargs.get("expected_sha256"),
            }
        )


def test_registers_only_bounded_task_level_tools() -> None:
    server = FastMCP("root")
    register_project_management_tools(server, Service())

    names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert names == {
        "project_management_inventory",
        "project_management_reconcile",
        "project_management_next_work",
        "project_management_take_next_work",
        "project_management_claim_work",
        "project_management_release_work",
        "project_management_transition_work",
        "project_management_hold_work",
        "project_management_defer_work",
        "project_management_sync_change_classification",
        "project_management_complete_work",
        "project_management_schema_plan",
        "project_management_schema_status",
        "project_management_merge_readiness",
        "project_management_documentation_reconcile",
        "project_management_portfolio_status",
        "project_management_persist_review",
        "project_management_verify_traceability",
        "project_management_current_work",
        "project_management_board_data",
        "project_management_contract",
    }
    assert all("delete" not in name and "graphql" not in name for name in names)


def test_tool_annotations_distinguish_effect_scope_and_mutation() -> None:
    server = FastMCP("root")
    register_project_management_tools(server, Service())
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}

    inventory = tools["project_management_inventory"].annotations
    assert inventory is not None
    assert inventory.read_only_hint is True
    assert inventory.destructive_hint is False
    assert inventory.idempotent_hint is True
    assert inventory.open_world_hint is True

    merge_readiness = tools["project_management_merge_readiness"].annotations
    assert merge_readiness is not None
    assert merge_readiness.read_only_hint is True
    assert merge_readiness.destructive_hint is False
    assert merge_readiness.idempotent_hint is True
    assert merge_readiness.open_world_hint is False

    claim = tools["project_management_claim_work"].annotations
    assert claim is not None
    assert claim.read_only_hint is False
    assert claim.destructive_hint is False
    assert claim.idempotent_hint is True
    assert claim.open_world_hint is True

    evidence = tools["project_management_persist_review"].annotations
    assert evidence is not None
    assert evidence.read_only_hint is False
    assert evidence.destructive_hint is False
    assert evidence.idempotent_hint is True
    assert evidence.open_world_hint is False


def test_reconcile_defaults_to_preview_and_requires_idempotency_for_apply() -> None:
    server = FastMCP("root")
    register_project_management_tools(server, Service())
    arguments = {
        "project_id": "alpha-project",
        "desired": [
            {
                "record_id": "TASK-1",
                "fields": {"Status": "Active"},
                "expected_revision": "rev-1",
                "source_repository": "ExampleOwner/alpha",
                "source_number": 7,
                "source_kind": "issue",
            }
        ],
        "observed": [
            {
                "record_id": "TASK-1",
                "fields": {"Status": "Inbox"},
                "revision": "rev-1",
                "accessible": True,
                "external_id": "I_1",
            }
        ],
        "supported_fields": ["Status"],
    }

    preview = asyncio.run(
        server.call_tool("project_management_reconcile", arguments)
    ).structured_content
    assert preview is not None
    assert preview["outcomes"][0]["applied"] is False

    applied = asyncio.run(
        server.call_tool(
            "project_management_reconcile",
            {**arguments, "apply": True, "idempotency_key": "apply-1"},
        )
    ).structured_content
    assert applied is not None
    assert applied["outcomes"][0]["applied"] is True
    assert applied["outcomes"][0]["idempotency_key"] == "apply-1"


def test_portfolio_status_preserves_change_classification() -> None:
    server = FastMCP("root")
    register_project_management_tools(server, Service())

    result = asyncio.run(
        server.call_tool(
            "project_management_portfolio_status",
            {
                "records": [
                    {
                        "record_id": "SPEC-117",
                        "project_id": "kis-mcp",
                        "title": "Two-axis governance",
                        "record_type": "specification_slice",
                        "complexity": "medium",
                        "risk_triggers": ["public_contract", "external_action"],
                    }
                ]
            },
        )
    ).structured_content

    assert result is not None
    assert result["records"][0]["complexity"] == "medium"
    assert result["records"][0]["risk_triggers"] == [
        "external_action",
        "public_contract",
    ]


class ActivationService(Service):
    async def take_next_work(self, project_id, execution_owner, **kwargs):
        active = kwargs.get("apply") is True
        return {
            "mode": "apply" if active else "preview",
            "selection": {"selected": {"repository": "owner/alpha", "number": 7}},
            "claim": {"phase": "active", "outcomes": [{"success": True}]} if active else None,
        }

    async def claim_work(self, project_id, repository, issue_number, execution_owner, **kwargs):
        active = kwargs.get("apply") is True
        return {
            "mode": "apply" if active else "preview",
            "phase": "active" if active else "ready",
            "outcomes": [{"success": True}] if active else [],
            "repository": repository,
            "issue_number": issue_number,
        }


def test_apply_claim_and_take_materialize_task_handoff_automatically() -> None:
    server = FastMCP("root")
    calls: list[tuple[str, str, int]] = []

    async def materialize(project_id: str, repository: str, issue_number: int):
        calls.append((project_id, repository, issue_number))
        return {"work_id": f"WORK-{issue_number}", "repository": repository}

    register_project_management_tools(
        server, ActivationService(), activation_materializer=materialize
    )
    claim = asyncio.run(server.call_tool(
        "project_management_claim_work",
        {
            "project_id": "alpha-project", "repository": "owner/alpha",
            "issue_number": 7, "execution_owner": "codex", "apply": True,
            "idempotency_key": "claim-7",
        },
    )).structured_content
    take = asyncio.run(server.call_tool(
        "project_management_take_next_work",
        {
            "project_id": "alpha-project", "execution_owner": "codex",
            "apply": True, "idempotency_key": "take-7",
        },
    )).structured_content

    assert claim is not None and claim["task_handoff"]["work_id"] == "WORK-7"
    assert take is not None and take["task_handoff"]["work_id"] == "WORK-7"
    assert calls == [
        ("alpha-project", "owner/alpha", 7),
        ("alpha-project", "owner/alpha", 7),
    ]


class FailedActivationService(ActivationService):
    async def claim_work(self, project_id, repository, issue_number, execution_owner, **kwargs):
        return {"mode": "apply", "phase": "active", "outcomes": [{"success": False}]}


def test_failed_active_transition_does_not_materialize_task_handoff() -> None:
    server = FastMCP("root")
    calls: list[tuple[str, str, int]] = []

    async def materialize(project_id: str, repository: str, issue_number: int):
        calls.append((project_id, repository, issue_number))
        return {"work_id": f"WORK-{issue_number}"}

    register_project_management_tools(
        server, FailedActivationService(), activation_materializer=materialize
    )
    result = asyncio.run(server.call_tool(
        "project_management_claim_work",
        {"project_id": "alpha-project", "repository": "owner/alpha", "issue_number": 7,
         "execution_owner": "codex", "apply": True, "idempotency_key": "claim-fail"},
    )).structured_content
    assert result is not None and "task_handoff" not in result
    assert calls == []
