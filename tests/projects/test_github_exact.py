from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.projects import (
    GitHubProjectBinding,
    GitHubProjectResource,
    ProjectDefinition,
    ProjectRegistry,
)
from kis_mcp.projects.github_exact import (
    REGISTERED_GITHUB_OPERATION_SCHEMAS,
    RegisteredGitHubOperations,
    execute_registered_github_operation,
)


@dataclass(frozen=True)
class Result:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class QueueRunner:
    def __init__(self, results=()) -> None:
        self.results = list(results)
        self.calls = []

    def __call__(self, args, cwd, env, *, timeout_seconds=None):
        self.calls.append((tuple(args), cwd, dict(env)))
        if not self.results:
            raise AssertionError(f"unexpected command: {args}")
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

def _registry() -> ProjectRegistry:
    return ProjectRegistry(
        default_project_id="kis-mcp",
        projects=(
            ProjectDefinition(
                project_id="kis-mcp",
                display_name="kis-mcp",
                local_root=r"C:\Projects\kis-mcp",
                github=GitHubProjectBinding(
                    repository="NielPieterse0/kis-mcp",
                    projects=(
                        GitHubProjectResource(
                            binding_id="work-management",
                            owner="NielPieterse0",
                            owner_type="user",
                            project_number=1,
                        ),
                    ),
                ),
            ),
        ),
    )


def test_project_schema_commissioning_requires_approval_and_registered_binding() -> None:
    operations = RegisteredGitHubOperations(
        _registry(),
        runner=QueueRunner(()),
        gh_config_dir=Path(r"C:\Projects\.kis-mcp\github-cli"),
    )
    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        operations.commission_project_schema(
            project_id="kis-mcp",
            project_binding_id="work-management",
            approved=False,
        )
    with pytest.raises(ToolError, match="REGISTERED_GITHUB_PROJECT_REQUIRED"):
        operations.commission_project_schema(
            project_id="kis-mcp",
            project_binding_id="unknown",
            approved=True,
        )

def test_project_schema_commissioning_uses_only_registered_manifest(monkeypatch) -> None:
    runner = QueueRunner((Result(),))
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        def commission(self, target, manifest, *, scope="full"):
            captured["target"] = target
            captured["manifest"] = manifest
            captured["scope"] = scope
            return {
                "ready": True,
                "project_node_id": "project-id",
                "created_fields": [],
                "updated_fields": [],
                "created_views": [],
                "field_count": 24,
                "view_count": 12,
            }

    monkeypatch.setattr("kis_mcp.projects.github_exact.GitHubProjectSchemaClient", FakeClient)
    operations = RegisteredGitHubOperations(
        _registry(),
        runner=runner,
        gh_config_dir=Path(r"C:\Projects\.kis-mcp\github-cli"),
    )

    result = operations.commission_project_schema(
        project_id="kis-mcp",
        project_binding_id="work-management",
        approved=True,
    )

    assert result["ready"] is True
    assert captured["target"].project_number == 1
    assert captured["target"].owner == "NielPieterse0"
    assert captured["manifest"].portfolio_id == "default"
    assert captured["scope"] == "full"
    assert runner.calls[0][0][:3] == ("gh", "auth", "status")


def test_project_schema_operation_declares_bounded_commissioning_scope() -> None:
    schema = REGISTERED_GITHUB_OPERATION_SCHEMAS[
        "kis_github_commission_registered_project_schema"
    ]

    assert schema["properties"]["scope"] == {
        "type": "string",
        "enum": ["full", "fields"],
    }
    assert "scope" not in schema["required"]


def test_project_schema_operation_rejects_invalid_scope_before_dispatch() -> None:
    with pytest.raises(ToolError, match="scope must be full or fields"):
        execute_registered_github_operation(
            "kis_github_commission_registered_project_schema",
            {
                "project_id": "kis-mcp",
                "project_binding_id": "work-management",
                "approved": True,
                "scope": "views",
            },
            operations=RegisteredGitHubOperations(_registry()),
        )


def test_project_schema_operation_rejects_arbitrary_api_inputs_before_dispatch() -> None:
    with pytest.raises(ToolError, match="unknown fields: query"):
        execute_registered_github_operation(
            "kis_github_commission_registered_project_schema",
            {
                "project_id": "kis-mcp",
                "project_binding_id": "work-management",
                "approved": True,
                "query": "mutation { arbitrary }",
            },
            operations=RegisteredGitHubOperations(_registry()),
        )


def _ls_remote(ref: str, sha: str | None) -> Result:
    return Result(stdout="" if sha is None else f"{sha}\t{ref}\n")


def _default_remote(default_sha: str) -> tuple[Result, Result]:
    return (
        Result(stdout=f"ref: refs/heads/main\tHEAD\n{default_sha}\tHEAD\n"),
        _ls_remote("refs/heads/main", default_sha),
    )


def _pr_item(*, head: str, title: str, body: str, number: int = 9) -> str:
    return (
        f'{{"number":{number},"html_url":"https://github.com/example/repo/pull/{number}",'
        f'"title":"{title}","body":"{body}","head":{{"sha":"{head}"}},'
        '"base":{"ref":"main"},"state":"open","draft":false}'
    )


def _pr_pages(*, head: str, title: str, body: str) -> str:
    return f"[[{_pr_item(head=head, title=title, body=body)}]]"


class TimeoutOnceRunner(QueueRunner):
    def __init__(self, *, timeout_command: tuple[str, ...], results=()) -> None:
        super().__init__(results)
        self.timeout_command = timeout_command
        self.timed_out = False

    def __call__(self, args, cwd, env, *, timeout_seconds=None):
        call = tuple(args)
        self.calls.append((call, cwd, dict(env)))
        if not self.timed_out and all(part in call for part in self.timeout_command):
            self.timed_out = True
            raise ToolError(f"REGISTERED_GITHUB_COMMAND_TIMEOUT: {call[0]}")
        if not self.results:
            raise AssertionError(f"unexpected command: {args}")
        return self.results.pop(0)


def test_injected_runner_is_bounded_by_operation_deadline() -> None:
    calls: list[tuple[str, ...]] = []

    def slow_runner(args, cwd, env, *, timeout_seconds):
        calls.append(tuple(args))
        time.sleep(timeout_seconds)
        raise ToolError(f"REGISTERED_GITHUB_COMMAND_TIMEOUT: {args[0]}")

    operations = RegisteredGitHubOperations(_registry(), runner=slow_runner)

    with pytest.raises(ToolError, match="REGISTERED_GITHUB_COMMAND_TIMEOUT"):
        operations.publish_commit(
            project_id="kis-mcp",
            commit="a" * 40,
            branch="change/example",
            expected_remote_base=None,
            approved=True,
            deadline_ms=5,
        )

    assert calls == [("git", "check-ref-format", "--branch", "change/example")]


def test_publish_status_only_is_read_only_and_identity_stable() -> None:
    target = "a" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    runner = QueueRunner((
        Result(),
        Result(stdout=f"{target}\n"),
        Result(),
        _ls_remote(ref, None),
    ))
    operations = RegisteredGitHubOperations(_registry(), runner=runner)

    receipt = operations.publish_commit(
        project_id="kis-mcp",
        commit=target,
        branch=branch,
        expected_remote_base=None,
        approved=True,
        status_only=True,
        deadline_ms=20_000,
    )

    assert receipt["operation_state"] == "not_started"
    assert receipt["state"] == "not_started"
    assert str(receipt["operation_id"]).startswith("rgm-")
    assert not any("push" in call for call, _cwd, _env in runner.calls)

    applied_runner = QueueRunner((
        Result(),
        Result(stdout=f"{target}\n"),
        Result(),
        _ls_remote(ref, target),
    ))
    applied = RegisteredGitHubOperations(_registry(), runner=applied_runner).publish_commit(
        project_id="kis-mcp",
        commit=target,
        branch=branch,
        expected_remote_base=None,
        approved=True,
        status_only=True,
        deadline_ms=20_000,
    )
    assert applied["operation_state"] == "applied"
    assert applied["operation_id"] == receipt["operation_id"]


def test_publish_timeout_after_remote_apply_returns_applied_receipt_without_retry_push() -> None:
    target = "a" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    runner = TimeoutOnceRunner(
        timeout_command=("push",),
        results=(
            Result(),
            Result(stdout=f"{target}\n"),
            Result(),
            _ls_remote(ref, None),
            _ls_remote(ref, target),
        ),
    )
    operations = RegisteredGitHubOperations(_registry(), runner=runner)

    result = operations.publish_commit(
        project_id="kis-mcp",
        commit=target,
        branch=branch,
        expected_remote_base=None,
        approved=True,
        deadline_ms=20_000,
    )

    assert result["state"] == "published"
    assert result["operation_state"] == "applied"
    assert result["recovery"] == "acknowledgement_lost"
    assert sum("push" in call for call, _cwd, _env in runner.calls) == 1


def test_injected_native_timeout_after_push_attempt_reconciles_remote_authority() -> None:
    target = "a" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    runner = QueueRunner((
        Result(),
        Result(stdout=f"{target}\n"),
        Result(),
        _ls_remote(ref, None),
        subprocess.TimeoutExpired(cmd="git push", timeout=1.0),
        _ls_remote(ref, target),
    ))

    result = RegisteredGitHubOperations(_registry(), runner=runner).publish_commit(
        project_id="kis-mcp",
        commit=target,
        branch=branch,
        expected_remote_base=None,
        approved=True,
        deadline_ms=20_000,
    )

    assert result["operation_state"] == "applied"
    assert result["state"] == "published"
    assert result["recovery"] == "acknowledgement_lost"
    assert sum("push" in call for call, _cwd, _env in runner.calls) == 1


def test_publish_non_timeout_command_failure_reconciles_remote_authority() -> None:
    target = "a" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    runner = QueueRunner((
        Result(),
        Result(stdout=f"{target}\n"),
        Result(),
        _ls_remote(ref, None),
        ToolError("REGISTERED_GITHUB_COMMAND_FAILED: git push failed after submission"),
        _ls_remote(ref, target),
    ))

    result = RegisteredGitHubOperations(_registry(), runner=runner).publish_commit(
        project_id="kis-mcp",
        commit=target,
        branch=branch,
        expected_remote_base=None,
        approved=True,
        deadline_ms=20_000,
    )

    assert result["operation_state"] == "applied"
    assert result["state"] == "published"
    assert result["recovery"] == "acknowledgement_lost"
    assert sum("push" in call for call, _cwd, _env in runner.calls) == 1


def test_publish_post_push_verification_timeout_reconciles_to_applied_receipt() -> None:
    target = "a" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    runner = QueueRunner((
        Result(),
        Result(stdout=f"{target}\n"),
        Result(),
        _ls_remote(ref, None),
        Result(),
        ToolError("REGISTERED_GITHUB_COMMAND_TIMEOUT: git"),
        _ls_remote(ref, target),
    ))
    operations = RegisteredGitHubOperations(_registry(), runner=runner)

    result = operations.publish_commit(
        project_id="kis-mcp",
        commit=target,
        branch=branch,
        expected_remote_base=None,
        approved=True,
        deadline_ms=20_000,
    )

    assert result["state"] == "published"
    assert result["operation_state"] == "applied"
    assert result["recovery"] == "post_mutation_reconciled"
    assert sum("push" in call for call, _cwd, _env in runner.calls) == 1


def test_publish_timeout_before_remote_apply_returns_not_started_receipt() -> None:
    target = "a" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    runner = TimeoutOnceRunner(
        timeout_command=("push",),
        results=(
            Result(),
            Result(stdout=f"{target}\n"),
            Result(),
            _ls_remote(ref, None),
            _ls_remote(ref, None),
        ),
    )
    operations = RegisteredGitHubOperations(_registry(), runner=runner)

    result = operations.publish_commit(
        project_id="kis-mcp",
        commit=target,
        branch=branch,
        expected_remote_base=None,
        approved=True,
        deadline_ms=20_000,
    )

    assert result["state"] == "not_started"
    assert result["operation_state"] == "not_started"
    assert result["retryable"] is True


def test_create_pull_request_status_only_and_timeout_reconcile_do_not_duplicate() -> None:
    head = "d" * 40
    default = "b" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    title = "Exact change"
    body = "Body"
    empty_status_runner = QueueRunner((
        Result(),
        Result(),
        *_default_remote(default),
        _ls_remote(ref, head),
        Result(stdout="[]"),
    ))
    status = RegisteredGitHubOperations(_registry(), runner=empty_status_runner).create_pull_request(
        project_id="kis-mcp",
        branch=branch,
        expected_head=head,
        expected_remote_default=default,
        title=title,
        body=body,
        approved=True,
        status_only=True,
        deadline_ms=20_000,
    )
    assert status["operation_state"] == "not_started"
    assert not any(call[:3] == ("gh", "pr", "create") for call, _cwd, _env in empty_status_runner.calls)

    exact_pr = _pr_pages(head=head, title=title, body=body)
    timeout_runner = TimeoutOnceRunner(
        timeout_command=("pr", "create"),
        results=(
            Result(),
            Result(),
            *_default_remote(default),
            _ls_remote(ref, head),
            Result(stdout="[]"),
            Result(stdout=exact_pr),
        ),
    )
    result = RegisteredGitHubOperations(_registry(), runner=timeout_runner).create_pull_request(
        project_id="kis-mcp",
        branch=branch,
        expected_head=head,
        expected_remote_default=default,
        title=title,
        body=body,
        approved=True,
        deadline_ms=20_000,
    )
    assert result["state"] == "open"
    assert result["operation_state"] == "applied"
    assert result["recovery"] == "acknowledgement_lost"
    assert result["operation_id"] == status["operation_id"]
    assert sum(call[:3] == ("gh", "pr", "create") for call, _cwd, _env in timeout_runner.calls) == 1


def test_create_pull_request_status_only_rejects_exact_plus_conflicting_history() -> None:
    head = "d" * 40
    default = "b" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    title = "Exact change"
    body = "Body"
    history = (
        f"[[{_pr_item(head=head, title=title, body=body, number=9)}],"
        f"[{_pr_item(head=head, title='Different title', body=body, number=10)}]]"
    )
    runner = QueueRunner((
        Result(),
        Result(),
        *_default_remote(default),
        _ls_remote(ref, head),
        Result(stdout=history),
    ))

    result = RegisteredGitHubOperations(_registry(), runner=runner).create_pull_request(
        project_id="kis-mcp",
        branch=branch,
        expected_head=head,
        expected_remote_default=default,
        title=title,
        body=body,
        approved=True,
        status_only=True,
        deadline_ms=20_000,
    )

    assert result["operation_state"] == "failed"
    assert result["state"] == "failed"
    assert not any(call[:3] == ("gh", "pr", "create") for call, _cwd, _env in runner.calls)


def test_create_pull_request_non_timeout_failure_reconciles_exact_existing_pr() -> None:
    head = "d" * 40
    default = "b" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    title = "Exact change"
    body = "Body"
    exact_pr = _pr_pages(head=head, title=title, body=body)
    runner = QueueRunner((
        Result(),
        Result(),
        *_default_remote(default),
        _ls_remote(ref, head),
        Result(stdout="[]"),
        ToolError("REGISTERED_GITHUB_COMMAND_FAILED: gh pr create failed after submission"),
        Result(stdout=exact_pr),
    ))

    result = RegisteredGitHubOperations(_registry(), runner=runner).create_pull_request(
        project_id="kis-mcp",
        branch=branch,
        expected_head=head,
        expected_remote_default=default,
        title=title,
        body=body,
        approved=True,
        deadline_ms=20_000,
    )

    assert result["operation_state"] == "applied"
    assert result["state"] == "open"
    assert result["recovery"] == "acknowledgement_lost"
    assert sum(call[:3] == ("gh", "pr", "create") for call, _cwd, _env in runner.calls) == 1


def test_create_pull_request_malformed_success_ack_reconciles_exact_existing_pr() -> None:
    head = "d" * 40
    default = "b" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    title = "Exact change"
    body = "Body"
    exact_pr = _pr_pages(head=head, title=title, body=body)
    runner = QueueRunner((
        Result(),
        Result(),
        *_default_remote(default),
        _ls_remote(ref, head),
        Result(stdout="[]"),
        Result(stdout="created-without-url"),
        Result(stdout=exact_pr),
    ))

    result = RegisteredGitHubOperations(_registry(), runner=runner).create_pull_request(
        project_id="kis-mcp",
        branch=branch,
        expected_head=head,
        expected_remote_default=default,
        title=title,
        body=body,
        approved=True,
        deadline_ms=20_000,
    )

    assert result["state"] == "open"
    assert result["operation_state"] == "applied"
    assert result["recovery"] == "post_mutation_reconciled"
    assert sum(call[:3] == ("gh", "pr", "create") for call, _cwd, _env in runner.calls) == 1


def test_create_pull_request_post_create_metadata_drift_is_not_acknowledged_as_applied() -> None:
    head = "d" * 40
    default = "b" * 40
    branch = "change/example"
    ref = f"refs/heads/{branch}"
    title = "Exact change"
    body = "Body"
    changed_title = "Changed elsewhere"
    view_payload = (
        '{"number":9,"url":"https://github.com/example/repo/pull/9",'
        f'"title":"{changed_title}","body":"{body}","headRefOid":"{head}",'
        '"baseRefName":"main","state":"OPEN","isDraft":false}'
    )
    runner = QueueRunner((
        Result(),
        Result(),
        *_default_remote(default),
        _ls_remote(ref, head),
        Result(stdout="[]"),
        Result(stdout="https://github.com/example/repo/pull/9"),
        Result(stdout=view_payload),
        Result(stdout=_pr_pages(head=head, title=changed_title, body=body)),
    ))

    result = RegisteredGitHubOperations(_registry(), runner=runner).create_pull_request(
        project_id="kis-mcp",
        branch=branch,
        expected_head=head,
        expected_remote_default=default,
        title=title,
        body=body,
        approved=True,
        deadline_ms=20_000,
    )

    assert result["operation_state"] == "failed"
    assert result["state"] == "failed"
    assert sum(call[:3] == ("gh", "pr", "create") for call, _cwd, _env in runner.calls) == 1
