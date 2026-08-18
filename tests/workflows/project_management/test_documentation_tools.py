from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastmcp import FastMCP

from kis_mcp.workflows.project_management import register_project_management_tools


class Service:
    async def schema_status(self, project_id: str):
        return SimpleNamespace(
            to_json_dict=lambda: {
                "project_id": project_id,
                "ready": False,
                "fields_ready": False,
                "views_ready": None,
            }
        )


def record(*, state: str = "verification", impact: str = "pre_merge_complete", event_id=None):
    return {
        "record_id": "SPEC-110",
        "project_id": "kis-mcp",
        "title": "Work management completion",
        "record_type": "specification_slice",
        "state": state,
        "documentation_mode": "required",
        "documentation_impact": impact,
        "traceability_required": True,
        "documentation_milestone": "documentation_reconciliation_due" if event_id else "not_required",
        "documentation_event_id": event_id,
    }

def trace(*, merged: bool, include_due: bool = False):
    head = "a" * 40
    merge_commit = "b" * 40
    event = {
        "event_id": "doc-110-work-management-documentation-completion-pr-140",
        "project_id": "kis-mcp",
        "specification_record_id": "SPEC-110",
        "change_id": "110-work-management-documentation-completion",
        "pull_request_number": 140,
        "merge_commit": merge_commit,
        "documentation_task_id": "TASK-110",
        "required_updates": ["docs/OPERATIONS.md"],
        "state": "documentation_reconciliation_due",
    }
    return {
        "project_id": "kis-mcp",
        "specification_record_id": "SPEC-110",
        "change_id": "110-work-management-documentation-completion",
        "branch": "change/110-work-management-documentation-completion",
        "worktree": ".work/worktrees/110-work-management-documentation-completion",
        "pull_requests": [{
            "repository": "NielPieterse0/kis-mcp",
            "number": 140,
            "head_branch": "change/110-work-management-documentation-completion",
            "head_revision": head,
            "base_branch": "main",
            "state": "merged" if merged else "open",
        }],
        "verifications": [{
            "evidence_id": "verify-110",
            "pull_request_number": 140,
            "revision": head,
            "status": "passed",
            "command": "pwsh -File scripts/verify.ps1",
            "source": "github_actions",
            "reference": "run-110",
        }],
        "merges": ([{"pull_request_number": 140, "merge_commit": merge_commit, "head_revision": head}] if merged else []),
        "documentation_events": ([event] if include_due else []),
    }

def test_schema_status_is_exposed_as_bounded_read_operation() -> None:
    server = FastMCP("root")
    register_project_management_tools(server, Service())

    result = asyncio.run(
        server.call_tool("project_management_schema_status", {"project_id": "kis-mcp"})
    ).structured_content

    assert result is not None
    assert result["project_id"] == "kis-mcp"
    assert result["ready"] is False
    assert result["views_ready"] is None


def test_merge_readiness_enforces_pre_merge_documentation() -> None:
    server = FastMCP("root")
    register_project_management_tools(server, Service())

    ready = asyncio.run(server.call_tool(
        "project_management_merge_readiness",
        {"record": record(), "trace": trace(merged=False), "pull_request_number": 140},
    )).structured_content
    blocked = asyncio.run(server.call_tool(
        "project_management_merge_readiness",
        {"record": record(impact="planned"), "trace": trace(merged=False), "pull_request_number": 140},
    )).structured_content

    assert ready is not None and ready["ready"] is True
    assert blocked is not None and blocked["ready"] is False
    assert blocked["blocking_reasons"] == ["documentation_pre_merge_incomplete"]

def test_documentation_reconciliation_moves_verification_to_documentation_then_completes() -> None:
    server = FastMCP("root")
    register_project_management_tools(server, Service())

    due = asyncio.run(server.call_tool(
        "project_management_documentation_reconcile",
        {
            "record": record(),
            "trace": trace(merged=True),
            "pull_request_number": 140,
            "documentation_task_id": "TASK-110",
            "required_updates": ["docs/OPERATIONS.md"],
        },
    )).structured_content

    assert due is not None
    assert due["phase"] == "documentation_reconciliation_due"
    assert due["record"]["state"] == "documentation"
    assert due["record"]["documentation_milestone"] == "documentation_reconciliation_due"

    completed = asyncio.run(server.call_tool(
        "project_management_documentation_reconcile",
        {
            "record": due["record"],
            "trace": trace(merged=True, include_due=True),
            "pull_request_number": 140,
            "documentation_task_id": "TASK-110",
            "required_updates": ["docs/OPERATIONS.md"],
            "completion_revision": "c" * 40,
        },
    )).structured_content

    assert completed is not None
    assert completed["phase"] == "post_merge_complete"
    assert completed["record"]["state"] == "documentation"
    assert completed["record"]["documentation_impact"] == "post_merge_complete"
    assert completed["record"]["documentation_milestone"] == "post_merge_complete"
