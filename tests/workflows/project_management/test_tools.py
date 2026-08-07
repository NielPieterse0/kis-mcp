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
        "project_management_portfolio_status",
        "project_management_persist_review",
        "project_management_verify_traceability",
    }
    assert all("delete" not in name and "graphql" not in name for name in names)


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
