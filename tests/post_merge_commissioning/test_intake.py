from __future__ import annotations

import asyncio
from typing import Any

import pytest

from kis_mcp.commissioning.classifier import classify_change
from kis_mcp.commissioning.intake import (
    CommissioningIntakeError,
    CommissioningIntakeService,
    _render_body,
    _render_title,
)
from kis_mcp.commissioning.models import IntakeDisposition, LandedChangeEvidence
from kis_mcp.commissioning.settings import load_post_merge_commissioning_settings

MERGE_SHA = "b" * 40


class FakeInvoker:
    def __init__(self, responses: dict[str, list[Any]]) -> None:
        self.responses = {key: list(value) for key, value in responses.items()}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def external(self, operation: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((operation, dict(arguments)))
        queue = self.responses.get(operation)
        if not queue:
            raise AssertionError(f"unexpected operation: {operation}")
        return queue.pop(0)


def _classification():
    settings = load_post_merge_commissioning_settings()
    evidence = LandedChangeEvidence(
        repository="NielPieterse0/kis-mcp",
        source_issue=419,
        source_pr=452,
        merge_sha=MERGE_SHA,
        change_id="227-post-merge-project-field-commissioning",
        changed_paths=("src/kis_mcp/work_management/service.py",),
        risk_triggers=("external_action",),
    )
    return evidence, classify_change(evidence, settings)


def _issue(number: int, key: str, *, state: str = "open") -> dict[str, Any]:
    return {
        "number": number,
        "title": "Commissioning",
        "body": f"Commissioning Key: `{key}`",
        "state": state,
        "html_url": f"https://github.com/NielPieterse0/kis-mcp/issues/{number}",
    }


def _generated_issue(number: int, evidence, obligation) -> dict[str, Any]:
    return {
        "number": number,
        "title": _render_title(obligation, evidence),
        "body": _render_body(obligation, evidence),
        "state": "open",
        "html_url": f"https://github.com/NielPieterse0/kis-mcp/issues/{number}",
    }


def test_existing_closed_issue_suppresses_creation() -> None:
    evidence, classification = _classification()
    obligation = classification.obligations[0]
    invoker = FakeInvoker(
        {"github_search_issues": [[_issue(500, obligation.commissioning_key, state="closed")]]}
    )
    service = CommissioningIntakeService(invoker)

    outcomes = asyncio.run(service.intake(evidence, classification))

    assert len(outcomes) == 1
    assert outcomes[0].disposition is IntakeDisposition.EXISTING
    assert outcomes[0].issue_number == 500
    assert [call[0] for call in invoker.calls] == ["github_search_issues"]


def test_first_observation_creates_and_verifies_one_issue() -> None:
    evidence, classification = _classification()
    obligation = classification.obligations[0]
    created = _generated_issue(501, evidence, obligation)
    invoker = FakeInvoker(
        {
            "github_search_issues": [[]],
            "github_issue_write": [{"number": 501, "html_url": created["html_url"]}],
            "github_issue_read": [created],
        }
    )
    service = CommissioningIntakeService(invoker)

    outcomes = asyncio.run(service.intake(evidence, classification))

    assert outcomes[0].disposition is IntakeDisposition.CREATED
    assert outcomes[0].issue_number == 501
    create = next(arguments for operation, arguments in invoker.calls if operation == "github_issue_write")
    assert create["method"] == "create"
    assert create["owner"] == "NielPieterse0"
    assert create["repo"] == "kis-mcp"
    assert f"Source Issue: #{evidence.source_issue}" in create["body"]
    assert f"Source PR: #{evidence.source_pr}" in create["body"]
    assert f"Merge SHA: `{MERGE_SHA}`" in create["body"]
    assert f"Commissioning Key: `{obligation.commissioning_key}`" in create["body"]
    assert obligation.verification_procedure in create["body"]
    assert obligation.expected_invariant in create["body"]
    assert obligation.terminal_success_criterion in create["body"]


def test_intake_never_mutates_source_issue_or_project_evidence() -> None:
    evidence, classification = _classification()
    obligation = classification.obligations[0]
    created = _generated_issue(502, evidence, obligation)
    invoker = FakeInvoker(
        {
            "github_search_issues": [[]],
            "github_issue_write": [{"number": 502}],
            "github_issue_read": [created],
        }
    )

    asyncio.run(CommissioningIntakeService(invoker).intake(evidence, classification))

    operations = [operation for operation, _ in invoker.calls]
    assert all(not operation.startswith("project_management_") for operation in operations)
    writes = [args for operation, args in invoker.calls if operation == "github_issue_write"]
    assert len(writes) == 1
    assert writes[0].get("issue_number") is None


def test_multiple_existing_matches_are_reused_without_create() -> None:
    evidence, classification = _classification()
    key = classification.obligations[0].commissioning_key
    invoker = FakeInvoker(
        {"github_search_issues": [[_issue(503, key), _issue(504, key, state="closed")]]}
    )

    outcomes = asyncio.run(CommissioningIntakeService(invoker).intake(evidence, classification))

    assert outcomes[0].disposition is IntakeDisposition.EXISTING
    assert outcomes[0].issue_number == 503
    assert outcomes[0].matching_issue_numbers == (503, 504)
    assert all(operation != "github_issue_write" for operation, _ in invoker.calls)


def test_created_issue_must_retain_exact_key_on_readback() -> None:
    evidence, classification = _classification()
    invoker = FakeInvoker(
        {
            "github_search_issues": [[]],
            "github_issue_write": [{"number": 505}],
            "github_issue_read": [{"number": 505, "body": "wrong body"}],
        }
    )

    with pytest.raises(CommissioningIntakeError, match="created_issue_verification_failed"):
        asyncio.run(CommissioningIntakeService(invoker).intake(evidence, classification))


def test_non_required_classification_performs_no_external_calls() -> None:
    settings = load_post_merge_commissioning_settings()
    evidence = LandedChangeEvidence(
        repository="NielPieterse0/kis-mcp",
        source_issue=1,
        source_pr=2,
        merge_sha=MERGE_SHA,
        change_id="999-docs-only",
        changed_paths=("docs/README.md",),
        risk_triggers=(),
    )
    classification = classify_change(evidence, settings)
    invoker = FakeInvoker({})

    outcomes = asyncio.run(CommissioningIntakeService(invoker).intake(evidence, classification))

    assert outcomes == ()
    assert invoker.calls == []


def test_truncated_remote_key_search_fails_before_creation() -> None:
    evidence, classification = _classification()
    invoker = FakeInvoker(
        {
            "github_search_issues": [
                {
                    "incomplete_results": False,
                    "items": [],
                    "total_count": 1,
                }
            ]
        }
    )

    with pytest.raises(CommissioningIntakeError, match="issue_search_invalid"):
        asyncio.run(CommissioningIntakeService(invoker).intake(evidence, classification))

    assert all(operation != "github_issue_write" for operation, _ in invoker.calls)
