from __future__ import annotations

import asyncio
from typing import Any

import pytest

from kis_mcp.workflows.completion.service import CompletionCoordinator

COMMIT = "a" * 40
DEFAULT = "b" * 40
SOURCE_BASE = "e" * 40
PUBLISHED = "d" * 40


class Invoker:
    def __init__(self, execution_status: str = "passed") -> None:
        self.execution_status = execution_status
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        if tool_name == "execute_change_workflow":
            return {
                "contract": "change-execution-result-v1",
                "status": self.execution_status,
                "source_fingerprint": "c" * 64,
            }
        operation = arguments["operation"]
        if operation == "kis_github_reconcile_registered_commit":
            return {
                "state": "published",
                "branch": arguments["arguments"]["branch"],
                "source_commit_sha": COMMIT,
                "commit_sha": PUBLISHED,
            }
        if operation == "kis_github_create_registered_pull_request":
            return {
                "state": "open",
                "pull_number": 9,
                "branch": arguments["arguments"]["branch"],
                "head_sha": PUBLISHED,
                "base_branch": "main",
                "url": "https://github.com/example/repo/pull/9",
            }
        raise AssertionError(operation)


def _run(invoker: Invoker) -> Any:
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")
    return asyncio.run(service.prepare(
        project_id="college",
        commit=COMMIT,
        source_base=SOURCE_BASE,
        branch="feature/example",
        expected_remote_branch=None,
        expected_remote_default=DEFAULT,
        title="Review exact change",
        body="Ready for review.",
        approved=True,
    ))


def test_completion_coordinates_verification_publish_and_pr_in_fixed_order() -> None:
    invoker = Invoker()
    result = _run(invoker)

    assert result.status == "reviewable"
    assert result.source_commit_sha == COMMIT
    assert result.published_head_sha == PUBLISHED
    assert result.pull_request["pull_number"] == 9
    assert [name for name, _ in invoker.calls] == [
        "execute_change_workflow",
        "execute_external_action",
        "execute_external_action",
    ]
    execution = invoker.calls[0][1]
    assert execution["project"] == r"C:\Projects\college"
    assert execution["source"] == "commit"
    assert execution["commit_ref"] == COMMIT
    publish = invoker.calls[1][1]
    assert publish["operation"] == "kis_github_reconcile_registered_commit"
    assert publish["arguments"]["source_base"] == SOURCE_BASE
    assert publish["arguments"]["expected_remote_branch"] is None
    assert publish["arguments"]["expected_remote_default"] == DEFAULT
    assert publish["arguments"]["approved"] is True


def test_completion_creates_pr_only_for_published_exact_head() -> None:
    invoker = Invoker()
    _run(invoker)

    create = invoker.calls[2][1]
    assert create["operation"] == "kis_github_create_registered_pull_request"
    assert create["arguments"] == {
        "project_id": "college",
        "branch": "feature/example",
        "expected_head": PUBLISHED,
        "expected_remote_default": DEFAULT,
        "title": "Review exact change",
        "body": "Ready for review.",
        "approved": True,
    }


@pytest.mark.parametrize("status", ["failed", "incomplete"])
def test_completion_suppresses_all_external_mutation_unless_execution_passes(status: str) -> None:
    invoker = Invoker(execution_status=status)
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")

    with pytest.raises(ValueError, match="change execution must pass"):
        asyncio.run(service.prepare(
            project_id="college",
            commit=COMMIT,
            source_base=SOURCE_BASE,
            branch="feature/example",
            expected_remote_branch=None,
            expected_remote_default=DEFAULT,
            title="Review exact change",
            body="Ready for review.",
            approved=True,
        ))

    assert [name for name, _ in invoker.calls] == ["execute_change_workflow"]
