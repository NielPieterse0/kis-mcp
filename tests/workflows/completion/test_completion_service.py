from __future__ import annotations

import asyncio
from typing import Any

import pytest

from kis_mcp.workflows.completion.service import CompletionCoordinator, CompletionInvocationError

COMMIT = "a" * 40
DEFAULT = "b" * 40
SOURCE_BASE = "e" * 40
PUBLISHED = "d" * 40


class Invoker:
    def __init__(
        self,
        execution_status: str = "passed",
        base_relation: str = "diverged",
    ) -> None:
        self.execution_status = execution_status
        self.base_relation = base_relation
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        if tool_name == "execute_change_workflow":
            return {
                "contract": "change-execution-result-v2",
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
                "base_relation": self.base_relation,
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
    assert execution["complexity"] == "medium"
    assert execution["risk_triggers"] == []
    assert "max_verifications" not in execution
    assert "review_types" not in execution
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
    arguments = create["arguments"]
    assert arguments["project_id"] == "college"
    assert arguments["branch"] == "feature/example"
    assert arguments["expected_head"] == PUBLISHED
    assert arguments["expected_remote_default"] == DEFAULT
    assert arguments["title"] == "Review exact change"
    assert arguments["approved"] is True
    body = arguments["body"]
    assert "## Outcome\nReview exact change" in body
    assert "Ready for review." in body
    assert f"Source commit: `{COMMIT}`" in body
    assert f"Published head: `{PUBLISHED}`" in body
    assert "Complexity: `medium`" in body
    assert "Risk triggers: `none`" in body
    assert "Documentation impact: `not_assessed`" in body
    assert "Reconciliation base: `diverged`" in body
    assert "Residual state: none declared" in body


@pytest.mark.parametrize("status", ["failed", "incomplete"])
def test_completion_suppresses_all_external_mutation_unless_execution_passes(status: str) -> None:
    invoker = Invoker(execution_status=status)
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")

    with pytest.raises(CompletionInvocationError, match="change execution must pass") as raised:
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

    assert raised.value.code == "COMPLETION_VERIFICATION_NOT_PASSED"
    assert raised.value.stage == "verification"
    assert raised.value.retryable is False
    assert [name for name, _ in invoker.calls] == ["execute_change_workflow"]


class RecoveringInvoker(Invoker):
    def __init__(self, fail_stage: str) -> None:
        super().__init__()
        self.fail_stage = fail_stage
        self.failed = False
        self.publication_exists = False
        self.pull_request_exists = False

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        if tool_name == "execute_change_workflow":
            return {
                "contract": "change-execution-result-v2",
                "status": "passed",
                "source_fingerprint": "c" * 64,
            }
        operation = arguments["operation"]
        if operation == "kis_github_reconcile_registered_commit":
            recovered = self.publication_exists
            self.publication_exists = True
            if self.fail_stage == "publication" and not self.failed:
                self.failed = True
                raise TimeoutError("publication response lost")
            result = {
                "state": "published",
                "branch": arguments["arguments"]["branch"],
                "source_commit_sha": COMMIT,
                "commit_sha": PUBLISHED,
                "base_relation": "tree_equivalent",
            }
            if recovered:
                result["recovery"] = "existing_exact"
            return result
        if operation == "kis_github_create_registered_pull_request":
            recovered = self.pull_request_exists
            self.pull_request_exists = True
            if self.fail_stage == "pull_request" and not self.failed:
                self.failed = True
                raise TimeoutError("pull request response lost")
            result = {
                "state": "open",
                "pull_number": 9,
                "branch": arguments["arguments"]["branch"],
                "head_sha": PUBLISHED,
                "base_branch": "main",
                "url": "https://github.com/example/repo/pull/9",
            }
            if recovered:
                result["recovery"] = "existing_exact"
            return result
        raise AssertionError(operation)


def _prepare(service: CompletionCoordinator) -> Any:
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


@pytest.mark.parametrize(
    ("fail_stage", "expected_completed"),
    [
        ("publication", ("verification",)),
        ("pull_request", ("verification", "publication")),
    ],
)
def test_completion_retry_converges_after_external_response_loss(
    fail_stage: str,
    expected_completed: tuple[str, ...],
) -> None:
    invoker = RecoveringInvoker(fail_stage)
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")

    with pytest.raises(CompletionInvocationError) as raised:
        _prepare(service)

    error = raised.value
    assert error.retryable is True
    assert error.stage == fail_stage
    assert error.completed_steps == expected_completed
    result = _prepare(service)
    assert result.status == "reviewable"
    assert result.publication.get("recovery") == "existing_exact"
    if fail_stage == "pull_request":
        assert result.pull_request.get("recovery") == "existing_exact"


class ConflictInvoker(Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "execute_change_workflow":
            return await super().__call__(tool_name, arguments)
        self.calls.append((tool_name, arguments))
        raise RuntimeError(
            f"REMOTE_DEFAULT_MISMATCH: expected {DEFAULT}, observed {'f' * 40}"
        )


def test_completion_marks_stale_remote_authority_conflict_non_retryable() -> None:
    invoker = ConflictInvoker()
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")

    with pytest.raises(CompletionInvocationError) as raised:
        _prepare(service)

    error = raised.value
    assert error.retryable is False
    assert error.stage == "publication"
    assert error.completed_steps == ("verification",)
    assert "REMOTE_DEFAULT_MISMATCH" in error.reason


class InvalidContractInvoker(Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        assert tool_name == "execute_change_workflow"
        return {"contract": "change-execution-result-v1", "status": "passed"}


def test_completion_execution_contract_mismatch_is_non_retryable() -> None:
    invoker = InvalidContractInvoker()
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")

    with pytest.raises(CompletionInvocationError) as raised:
        _prepare(service)

    error = raised.value
    assert error.code == "COMPLETION_EXECUTION_INVALID"
    assert error.stage == "verification"
    assert error.retryable is False
    assert error.completed_steps == ()


class UnknownFailureInvoker(Invoker):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "execute_change_workflow":
            return await super().__call__(tool_name, arguments)
        self.calls.append((tool_name, arguments))
        raise RuntimeError("opaque provider failure")


def test_completion_unknown_external_failure_is_conservatively_non_retryable() -> None:
    invoker = UnknownFailureInvoker()
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")

    with pytest.raises(CompletionInvocationError) as raised:
        _prepare(service)

    error = raised.value
    assert error.code == "COMPLETION_PUBLICATION_FAILED"
    assert error.stage == "publication"
    assert error.retryable is False
    assert error.completed_steps == ("verification",)


def test_completion_success_exposes_stable_operation_identity_and_stage_timings() -> None:
    first = _run(Invoker())
    service = CompletionCoordinator(Invoker(), lambda project_id: r"C:\Projects\college")
    second = asyncio.run(service.prepare(
        project_id="college",
        commit=COMMIT,
        source_base=SOURCE_BASE,
        branch="feature/example",
        expected_remote_branch=None,
        expected_remote_default=DEFAULT,
        title="Review exact change",
        body="Ready for review.",
        approved=True,
        deadline_ms=60_000,
    ))

    assert first.operation_state == "applied"
    assert str(first.operation_id).startswith("prp-")
    assert first.operation_id == second.operation_id
    assert first.elapsed_ms >= 0
    assert set(first.stage_timings_ms) == {"verification", "publication", "pull_request"}


class ReconcileInvoker:
    def __init__(self, *, publication_state: str, pull_request_state: str = "not_started") -> None:
        self.publication_state = publication_state
        self.pull_request_state = pull_request_state
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        if tool_name == "execute_change_workflow":
            return {
                "contract": "change-execution-result-v2",
                "status": "passed",
                "source_fingerprint": "c" * 64,
            }
        operation = arguments["operation"]
        inner = arguments["arguments"]
        assert inner["status_only"] is True
        if operation == "kis_github_reconcile_registered_commit":
            if self.publication_state == "applied":
                return {
                    "state": "published",
                    "operation_state": "applied",
                    "operation_id": "rgm-publication",
                    "branch": inner["branch"],
                    "source_commit_sha": COMMIT,
                    "commit_sha": PUBLISHED,
                    "base_relation": "tree_equivalent",
                }
            return {
                "state": self.publication_state,
                "operation_state": self.publication_state,
                "operation_id": "rgm-publication",
                "branch": inner["branch"],
                "source_commit_sha": COMMIT,
            }
        if operation == "kis_github_create_registered_pull_request":
            if self.pull_request_state == "applied":
                return {
                    "state": "open",
                    "operation_state": "applied",
                    "operation_id": "rgm-pr",
                    "pull_number": 9,
                    "branch": inner["branch"],
                    "head_sha": PUBLISHED,
                    "base_branch": "main",
                    "url": "https://github.com/example/repo/pull/9",
                }
            return {
                "state": self.pull_request_state,
                "operation_state": self.pull_request_state,
                "operation_id": "rgm-pr",
                "branch": inner["branch"],
                "head_sha": PUBLISHED,
            }
        raise AssertionError(operation)


def test_completion_reconcile_only_reports_not_started_without_rerunning_verification() -> None:
    invoker = ReconcileInvoker(publication_state="not_started")
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")

    receipt = asyncio.run(service.prepare(
        project_id="college",
        commit=COMMIT,
        source_base=SOURCE_BASE,
        branch="feature/example",
        expected_remote_branch=None,
        expected_remote_default=DEFAULT,
        title="Review exact change",
        body="Ready for review.",
        approved=True,
        reconcile_only=True,
        deadline_ms=60_000,
    ))

    assert receipt.operation_state == "not_started"
    assert receipt.stage == "publication"
    assert receipt.completed_steps == ()
    assert [name for name, _ in invoker.calls] == ["execute_external_action"]


def test_completion_reconcile_only_reports_partial_publication_as_in_progress() -> None:
    invoker = ReconcileInvoker(publication_state="applied", pull_request_state="not_started")
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")

    receipt = asyncio.run(service.prepare(
        project_id="college",
        commit=COMMIT,
        source_base=SOURCE_BASE,
        branch="feature/example",
        expected_remote_branch=None,
        expected_remote_default=DEFAULT,
        title="Review exact change",
        body="Ready for review.",
        approved=True,
        reconcile_only=True,
        deadline_ms=60_000,
    ))

    assert receipt.operation_state == "in_progress"
    assert receipt.completed_steps == ("publication",)
    assert [name for name, _ in invoker.calls] == [
        "execute_external_action",
        "execute_change_workflow",
        "execute_external_action",
    ]


class SlowVerificationInvoker:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(tool_name)
        if tool_name == "execute_change_workflow":
            await asyncio.sleep(0.05)
            return {"contract": "change-execution-result-v2", "status": "passed"}
        raise AssertionError("external mutation must not start after verification deadline")


def test_completion_total_deadline_expires_before_mutation_with_conclusive_not_started_state() -> None:
    invoker = SlowVerificationInvoker()
    service = CompletionCoordinator(invoker, lambda project_id: r"C:\Projects\college")

    with pytest.raises(CompletionInvocationError) as raised:
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
            deadline_ms=10,
        ))

    error = raised.value
    assert error.operation_state == "not_started"
    assert str(error.operation_id).startswith("prp-")
    assert error.stage == "verification"
    assert error.elapsed_ms >= 0
    assert "verification" in error.stage_timings_ms
    assert invoker.calls == ["execute_change_workflow"]
