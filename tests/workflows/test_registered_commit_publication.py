from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.projects import GitHubProjectBinding, ProjectDefinition, ProjectRegistry
from kis_mcp.projects.github_exact import (
    REGISTERED_GITHUB_OPERATION_SCHEMAS,
    RegisteredGitHubOperations,
    _contains_issue_closing_reference,
    execute_registered_github_operation,
)

TARGET = "1111111111111111111111111111111111111111"
BASE = "2222222222222222222222222222222222222222"
OTHER = "3333333333333333333333333333333333333333"
REMOTE_DEFAULT = "4444444444444444444444444444444444444444"
SOURCE_TREE = "5555555555555555555555555555555555555555"
BASE_TREE = "6666666666666666666666666666666666666666"
OTHER_TREE = "7777777777777777777777777777777777777777"
RECONCILED = "8888888888888888888888888888888888888888"
MERGED_TREE = "9999999999999999999999999999999999999999"


@dataclass(frozen=True)
class Result:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class QueueRunner:
    def __init__(self, results: Sequence[Result]) -> None:
        self.results = list(results)
        self.calls: list[tuple[tuple[str, ...], Path, Mapping[str, str]]] = []

    def __call__(
        self,
        args: Sequence[str],
        cwd: Path,
        env: Mapping[str, str],
        *,
        timeout_seconds: float | None = None,
    ) -> Result:
        self.calls.append((tuple(args), cwd, dict(env)))
        if not self.results:
            raise AssertionError(f"unexpected command: {args}")
        return self.results.pop(0)


def registry(*, github: bool = True) -> ProjectRegistry:
    return ProjectRegistry(
        default_project_id="college",
        projects=(
            ProjectDefinition(
                project_id="college",
                display_name="College",
                local_root="C:\\Projects\\college",
                github=(
                    GitHubProjectBinding(repository="NielPieterse0/college")
                    if github
                    else None
                ),
            ),
        ),
    )


def pr_api_pages(
    *,
    number: int = 7,
    head: str = TARGET,
    base: str = "main",
    title: str = "Review exact change",
    body: str = "Ready for review.",
    state: str = "open",
    draft: bool = False,
) -> str:
    item = {
        "number": number,
        "html_url": f"https://github.com/nielpieterse0/college/pull/{number}",
        "title": title,
        "body": body,
        "head": {"sha": head},
        "base": {"ref": base},
        "state": state,
        "draft": draft,
    }
    return json.dumps([[item]]) + "\n"


def test_kis_github_cli_state_uses_explicit_project_state_directory() -> None:
    operations = RegisteredGitHubOperations(
        registry(),
        runner=QueueRunner(()),
        gh_config_dir=Path("C:\\Projects\\.kis-mcp\\github-cli"),
    )

    environment = operations.command_environment()

    assert environment["GH_CONFIG_DIR"] == "C:\\Projects\\.kis-mcp\\github-cli"


def test_publication_requires_explicit_approval_and_registered_github_binding() -> None:
    runner = QueueRunner(())
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        operations.publish_commit(
            project_id="college",
            commit="f04d30a",
            branch="feature/example",
            expected_remote_base=BASE,
            approved=False,
        )

    without_github = RegisteredGitHubOperations(registry(github=False), runner=runner)
    with pytest.raises(ToolError, match="GITHUB_BINDING_REQUIRED"):
        without_github.publish_commit(
            project_id="college",
            commit="f04d30a",
            branch="feature/example",
            expected_remote_base=BASE,
            approved=True,
        )

    assert runner.calls == []


def test_publish_existing_commit_uses_exact_lease_and_verifies_remote_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        monkeypatch.setenv(key, "must-not-reach-child-process")
    remote_ref = "refs/heads/feature/example"
    runner = QueueRunner(
        (
            Result(),
            Result(stdout=f"{TARGET}\n"),
            Result(),
            Result(),
            Result(stdout=f"{BASE}\t{remote_ref}\n"),
            Result(),
            Result(stdout=f"{TARGET}\t{remote_ref}\n"),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.publish_commit(
        project_id="college",
        commit="f04d30a",
        branch="feature/example",
        expected_remote_base=BASE,
        approved=True,
    )

    assert result["schema_version"] == 1
    assert result["state"] == "published"
    assert result["operation_state"] == "applied"
    assert str(result["operation_id"]).startswith("rgm-")
    assert result["elapsed_ms"] >= 0
    assert result["project_id"] == "college"
    assert result["repository"] == "nielpieterse0/college"
    assert result["branch"] == "feature/example"
    assert result["commit_sha"] == TARGET
    assert result["previous_remote_sha"] == BASE
    assert result["publication_semantics"] == "exact_git_object"
    commands = [call[0] for call in runner.calls]
    assert commands[0] == ("git", "check-ref-format", "--branch", "feature/example")
    assert commands[1] == (
        "git",
        "rev-parse",
        "--verify",
        "--end-of-options",
        "f04d30a^{commit}",
    )
    assert commands[2] == ("git", "merge-base", "--is-ancestor", BASE, TARGET)
    assert commands[3] == ("gh", "auth", "status", "--active", "--hostname", "github.com")
    push = commands[5]
    assert "--force-with-lease=refs/heads/feature/example:" + BASE in push
    assert f"{TARGET}:refs/heads/feature/example" in push
    assert "--force" not in push
    assert all("auth token" not in " ".join(command) for command in commands)
    assert all("auth setup-git" not in " ".join(command) for command in commands)
    forbidden_env = {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"}
    assert all(not (forbidden_env & set(environment)) for _, _, environment in runner.calls)
    assert runner.results == []


def test_publish_rejects_non_ancestor_before_authentication_or_network() -> None:
    runner = QueueRunner((Result(), Result(stdout=f"{TARGET}\n"), Result(returncode=1)))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="NON_FAST_FORWARD_PUBLICATION"):
        operations.publish_commit(
            project_id="college",
            commit="f04d30a",
            branch="feature/example",
            expected_remote_base=BASE,
            approved=True,
        )

    assert len(runner.calls) == 3
    assert all(call[0][0] != "gh" for call in runner.calls)


def test_publish_rejects_stale_remote_base_without_push() -> None:
    remote_ref = "refs/heads/feature/example"
    runner = QueueRunner(
        (
            Result(),
            Result(stdout=f"{TARGET}\n"),
            Result(),
            Result(),
            Result(stdout=f"{OTHER}\t{remote_ref}\n"),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="REMOTE_BASE_MISMATCH"):
        operations.publish_commit(
            project_id="college",
            commit="f04d30a",
            branch="feature/example",
            expected_remote_base=BASE,
            approved=True,
        )

    assert not any("push" in call[0] for call in runner.calls)


def test_repository_landing_policy_disables_squash_rebase_and_auto_cleanup() -> None:
    policy = {
        "allow_merge_commit": True,
        "allow_squash_merge": False,
        "allow_rebase_merge": False,
        "delete_branch_on_merge": False,
    }
    runner = QueueRunner((Result(), Result(stdout="{}\n"), Result(stdout=json.dumps(policy) + "\n")))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.configure_repository_landing_policy(
        project_id="college",
        approved=True,
    )

    assert result["state"] == "configured"
    patch = runner.calls[1][0]
    assert patch[:5] == ("gh", "api", "--method", "PATCH", "repos/nielpieterse0/college")
    assert "allow_merge_commit=true" in patch
    assert "allow_squash_merge=false" in patch
    assert "allow_rebase_merge=false" in patch
    assert "delete_branch_on_merge=false" in patch


@pytest.mark.parametrize(
    "keyword",
    ["close", "closes", "closed", "fix", "fixes", "fixed", "resolve", "resolves", "resolved"],
)
@pytest.mark.parametrize("reference", ["#379", "NielPieterse0/kis-mcp#379"])
@pytest.mark.parametrize("transform", [str.lower, str.upper, str.swapcase])
def test_issue_closing_reference_detection_covers_keyword_families(
    keyword: str, reference: str, transform: Callable[[str], str]
) -> None:
    assert _contains_issue_closing_reference(f"{transform(keyword)} {reference}") is True


@pytest.mark.parametrize("separator", [" ", "  ", "\t", "\n", "\r\n", "\v", "\f"])
@pytest.mark.parametrize("reference", ["#379", "NielPieterse0/kis-mcp#379"])
def test_issue_closing_reference_detection_accepts_whitespace_separators(
    separator: str, reference: str
) -> None:
    assert _contains_issue_closing_reference(f"ClOsEs{separator}{reference}") is True


def test_issue_closing_reference_detection_allows_normal_references() -> None:
    for text in (
        "See #379",
        "Related: NielPieterse0/kis-mcp#379",
        "This fixes the regression described in #379",
        "prefixes #379",
        "closes#379",
        "fixesNielPieterse0/kis-mcp#379",
    ):
        assert _contains_issue_closing_reference(text) is False


def test_merge_rejects_closing_reference_in_pull_request_body_before_mutation() -> None:
    before = {
        "headRefOid": TARGET,
        "state": "OPEN",
        "isDraft": False,
        "body": "Closes #379",
        "commits": [],
    }
    runner = QueueRunner((Result(), Result(stdout=json.dumps(before) + "\n")))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="ISSUE_CLOSING_REFERENCE_BLOCKED"):
        operations.merge_pull_request(
            project_id="college",
            pull_number=7,
            expected_head=TARGET,
            merge_method="merge",
            approved=True,
        )

    assert not any(call[0][:3] == ("gh", "pr", "merge") for call in runner.calls)


def test_merge_rejects_closing_reference_in_commit_message_before_mutation() -> None:
    before = {
        "headRefOid": TARGET,
        "state": "OPEN",
        "isDraft": False,
        "body": "Related: #379",
        "commits": [
            {"messageHeadline": "Guard merge boundary", "messageBody": "FiXeS NielPieterse0/kis-mcp#379"}
        ],
    }
    runner = QueueRunner((Result(), Result(stdout=json.dumps(before) + "\n")))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="ISSUE_CLOSING_REFERENCE_BLOCKED"):
        operations.merge_pull_request(
            project_id="college",
            pull_number=7,
            expected_head=TARGET,
            merge_method="merge",
            approved=True,
        )

    assert not any(call[0][:3] == ("gh", "pr", "merge") for call in runner.calls)


@pytest.mark.parametrize(
    ("override", "error"),
    [
        ({"body": 7}, "pull request body is not text"),
        ({"commits": "not-a-list"}, "pull request commits are not a list"),
        ({"commits": ["not-an-object"]}, "pull request commit is not an object"),
        (
            {"commits": [{"messageHeadline": 7, "messageBody": ""}]},
            "commit message is not text",
        ),
        (
            {"commits": [{"messageHeadline": "ok", "messageBody": 7}]},
            "commit message is not text",
        ),
    ],
)
def test_merge_rejects_unverifiable_pr_payload_before_mutation(
    override: dict[str, object], error: str
) -> None:
    before: dict[str, object] = {
        "headRefOid": TARGET,
        "state": "OPEN",
        "isDraft": False,
        "body": "Related: #379",
        "commits": [],
    }
    before.update(override)
    runner = QueueRunner((Result(), Result(stdout=json.dumps(before) + "\n")))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match=error):
        operations.merge_pull_request(
            project_id="college",
            pull_number=7,
            expected_head=TARGET,
            merge_method="merge",
            approved=True,
        )

    assert not any(call[0][:3] == ("gh", "pr", "merge") for call in runner.calls)


def test_merge_is_approval_gated_exact_head_and_never_admin() -> None:
    runner = QueueRunner(
        (
            Result(),
            Result(stdout='{"headRefOid":"1111111111111111111111111111111111111111","state":"OPEN","isDraft":false}\n'),
            Result(stdout="merged\n"),
            Result(stdout='{"headRefOid":"1111111111111111111111111111111111111111","state":"MERGED","isDraft":false}\n'),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.merge_pull_request(
        project_id="college",
        pull_number=7,
        expected_head=TARGET,
        merge_method="merge",
        approved=True,
    )

    assert result["state"] == "merged"
    assert result["authorized_head"] == TARGET
    merge = runner.calls[2][0]
    assert merge == (
        "gh",
        "pr",
        "merge",
        "7",
        "--repo",
        "nielpieterse0/college",
        "--match-head-commit",
        TARGET,
        "--merge",
    )
    assert "--admin" not in merge


def test_merge_rejects_squash_and_rebase_methods_before_mutation() -> None:
    for method in ("squash", "rebase"):
        runner = QueueRunner(())
        operations = RegisteredGitHubOperations(registry(), runner=runner)
        with pytest.raises(ToolError, match="INVALID_MERGE_METHOD"):
            operations.merge_pull_request(
                project_id="college",
                pull_number=7,
                expected_head=TARGET,
                merge_method=method,
                approved=True,
            )
        assert runner.calls == []


def test_merge_rejects_stale_head_before_mutation() -> None:
    runner = QueueRunner(
        (
            Result(),
            Result(stdout='{"headRefOid":"3333333333333333333333333333333333333333","state":"OPEN","isDraft":false}\n'),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="PULL_REQUEST_HEAD_MISMATCH"):
        operations.merge_pull_request(
            project_id="college",
            pull_number=7,
            expected_head=TARGET,
            merge_method="merge",
            approved=True,
        )

    assert len(runner.calls) == 2


def test_remote_branch_delete_is_not_a_registered_github_operation() -> None:
    operation = "kis_github_delete_registered_branch"
    assert operation not in REGISTERED_GITHUB_OPERATION_SCHEMAS

    runner = QueueRunner(())
    operations = RegisteredGitHubOperations(registry(), runner=runner)
    with pytest.raises(ToolError) as captured:
        execute_registered_github_operation(
            operation,
            {
                "project_id": "college",
                "branch": "feature/example",
                "expected_head": TARGET,
                "approved": True,
            },
            operations=operations,
        )

    assert str(captured.value) == (
        "UNKNOWN_REGISTERED_GITHUB_OPERATION: kis_github_delete_registered_branch"
    )
    assert runner.calls == []


def test_direct_remote_branch_delete_compatibility_stub_rejects_without_side_effects() -> None:
    runner = QueueRunner(())
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError) as captured:
        operations.delete_remote_branch(
            project_id="college",
            branch="feature/example",
            expected_head=TARGET,
            approved=True,
        )

    assert str(captured.value) == (
        "REMOTE_BRANCH_DELETE_PROHIBITED: HR-003 requires recoverable disposition; "
        "remote review branches are retained"
    )
    assert runner.calls == []



def test_reconcile_publish_requires_explicit_approval() -> None:
    runner = QueueRunner(())
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        operations.reconcile_publish_commit(
            project_id="college",
            commit="f04d30a",
            source_base="main",
            branch="feature/example",
            expected_remote_default=REMOTE_DEFAULT,
            expected_remote_branch=None,
            approved=False,
        )

    assert runner.calls == []


def test_reconcile_publish_roots_exact_source_tree_on_verified_remote_default() -> None:
    remote_default_ref = "refs/heads/main"
    target_ref = "refs/heads/feature/example"
    runner = QueueRunner(
        (
            Result(),
            Result(stdout=f"{TARGET}\n"),
            Result(stdout=f"{BASE}\n"),
            Result(),
            Result(stdout=f"{BASE_TREE}\n"),
            Result(stdout=f"{SOURCE_TREE}\n"),
            Result(),
            Result(stdout=f"ref: {remote_default_ref}\tHEAD\n"),
            Result(stdout=f"{REMOTE_DEFAULT}\t{remote_default_ref}\n"),
            Result(stdout=""),
            Result(),
            Result(stdout=f"{REMOTE_DEFAULT}\t{remote_default_ref}\n"),
            Result(stdout=f"{BASE_TREE}\n"),
            Result(stdout=f"{RECONCILED}\n"),
            Result(),
            Result(stdout=f"{RECONCILED}\t{target_ref}\n"),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.reconcile_publish_commit(
        project_id="college",
        commit="f04d30a",
        source_base="main",
        branch="feature/example",
        expected_remote_default=REMOTE_DEFAULT,
        expected_remote_branch=None,
        approved=True,
    )

    assert result["state"] == "published"
    assert result["source_commit_sha"] == TARGET
    assert result["source_base_sha"] == BASE
    assert result["remote_default_branch"] == "main"
    assert result["remote_default_sha"] == REMOTE_DEFAULT
    assert result["tree_sha"] == SOURCE_TREE
    assert result["commit_sha"] == RECONCILED
    assert result["publication_semantics"] == "remote-default-rooted-tree-equivalent"
    commands = [call[0] for call in runner.calls]
    assert commands[3] == ("git", "merge-base", "--is-ancestor", BASE, TARGET)
    assert commands[10][-5:] == (
        "fetch",
        "--no-tags",
        "--no-recurse-submodules",
        "https://github.com/nielpieterse0/college.git",
        remote_default_ref,
    )
    assert commands[13] == (
        "git",
        "commit-tree",
        SOURCE_TREE,
        "-p",
        REMOTE_DEFAULT,
        "-m",
        f"reconcile registered change from {TARGET}",
    )
    push = commands[14]
    assert f"--force-with-lease={target_ref}:" in push
    assert f"{RECONCILED}:{target_ref}" in push
    assert "--force" not in push
    assert runner.results == []


@pytest.mark.parametrize("prior_remote", [None, OTHER])
def test_reconcile_publish_recovers_exact_existing_publication_after_response_loss(
    prior_remote: str | None,
) -> None:
    remote_default_ref = "refs/heads/main"
    target_ref = "refs/heads/feature/example"
    runner = QueueRunner(
        (
            Result(),
            Result(stdout=f"{TARGET}\n"),
            Result(stdout=f"{BASE}\n"),
            Result(),
            Result(stdout=f"{BASE_TREE}\n"),
            Result(stdout=f"{SOURCE_TREE}\n"),
            Result(),
            Result(stdout=f"ref: {remote_default_ref}\tHEAD\n"),
            Result(stdout=f"{REMOTE_DEFAULT}\t{remote_default_ref}\n"),
            Result(stdout=f"{RECONCILED}\t{target_ref}\n"),
            Result(),
            Result(stdout=f"{REMOTE_DEFAULT}\t{remote_default_ref}\n"),
            Result(stdout=f"{BASE_TREE}\n"),
            Result(),
            Result(stdout=f"{RECONCILED}\t{target_ref}\n"),
            Result(stdout=f"{SOURCE_TREE}\n"),
            Result(stdout=f"{RECONCILED} {REMOTE_DEFAULT}\n"),
            Result(stdout=f"reconcile registered change from {TARGET}\n"),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.reconcile_publish_commit(
        project_id="college",
        commit="f04d30a",
        source_base="main",
        branch="feature/example",
        expected_remote_default=REMOTE_DEFAULT,
        expected_remote_branch=prior_remote,
        approved=True,
    )

    assert result["state"] == "published"
    assert result["commit_sha"] == RECONCILED
    assert result["tree_sha"] == SOURCE_TREE
    assert result["recovery"] == "existing_exact"
    commands = [call[0] for call in runner.calls]
    assert any(command[-1] == target_ref and "fetch" in command for command in commands)
    assert not any(command[:2] == ("git", "commit-tree") for command in commands)
    assert not any("push" in command for command in commands)
    assert runner.results == []


def test_reconcile_publish_three_way_merges_diverged_remote_base() -> None:
    remote_default_ref = "refs/heads/main"
    target_ref = "refs/heads/feature/example"
    runner = QueueRunner(
        (
            Result(),
            Result(stdout=f"{TARGET}\n"),
            Result(stdout=f"{BASE}\n"),
            Result(),
            Result(stdout=f"{BASE_TREE}\n"),
            Result(stdout=f"{SOURCE_TREE}\n"),
            Result(),
            Result(stdout=f"ref: {remote_default_ref}\tHEAD\n"),
            Result(stdout=f"{REMOTE_DEFAULT}\t{remote_default_ref}\n"),
            Result(stdout=""),
            Result(),
            Result(stdout=f"{REMOTE_DEFAULT}\t{remote_default_ref}\n"),
            Result(stdout=f"{OTHER_TREE}\n"),
            Result(stdout=f"{MERGED_TREE}\n"),
            Result(stdout=f"{RECONCILED}\n"),
            Result(),
            Result(stdout=f"{RECONCILED}\t{target_ref}\n"),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.reconcile_publish_commit(
        project_id="college",
        commit="f04d30a",
        source_base="main",
        branch="feature/example",
        expected_remote_default=REMOTE_DEFAULT,
        expected_remote_branch=None,
        approved=True,
    )

    assert result["state"] == "published"
    assert result["source_tree_sha"] == SOURCE_TREE
    assert result["tree_sha"] == MERGED_TREE
    assert result["commit_sha"] == RECONCILED
    assert result["base_relation"] == "diverged"
    assert result["publication_semantics"] == "remote-default-rooted-three-way-merge"
    commands = [call[0] for call in runner.calls]
    assert (
        "git",
        "merge-tree",
        "--write-tree",
        "--merge-base",
        BASE,
        REMOTE_DEFAULT,
        TARGET,
    ) in commands
    assert (
        "git",
        "commit-tree",
        MERGED_TREE,
        "-p",
        REMOTE_DEFAULT,
        "-m",
        f"reconcile registered change from {TARGET}",
    ) in commands
    assert any("push" in command for command in commands)
    assert runner.results == []


def test_reconcile_publish_fails_closed_when_diverged_merge_conflicts() -> None:
    remote_default_ref = "refs/heads/main"
    runner = QueueRunner(
        (
            Result(),
            Result(stdout=f"{TARGET}\n"),
            Result(stdout=f"{BASE}\n"),
            Result(),
            Result(stdout=f"{BASE_TREE}\n"),
            Result(stdout=f"{SOURCE_TREE}\n"),
            Result(),
            Result(stdout=f"ref: {remote_default_ref}\tHEAD\n"),
            Result(stdout=f"{REMOTE_DEFAULT}\t{remote_default_ref}\n"),
            Result(stdout=""),
            Result(),
            Result(stdout=f"{REMOTE_DEFAULT}\t{remote_default_ref}\n"),
            Result(stdout=f"{OTHER_TREE}\n"),
            Result(returncode=1, stderr="CONFLICT (content): merge conflict"),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="REMOTE_BASE_RECONCILIATION_CONFLICT"):
        operations.reconcile_publish_commit(
            project_id="college",
            commit="f04d30a",
            source_base="main",
            branch="feature/example",
            expected_remote_default=REMOTE_DEFAULT,
            expected_remote_branch=None,
            approved=True,
        )

    commands = [call[0] for call in runner.calls]
    assert not any(command[:2] == ("git", "commit-tree") for command in commands)
    assert not any("push" in command for command in commands)
    assert runner.results == []


def test_create_registered_pull_request_requires_approval_before_commands() -> None:
    runner = QueueRunner(())
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        operations.create_pull_request(
            project_id="college",
            branch="feature/example",
            expected_head=TARGET,
            expected_remote_default=REMOTE_DEFAULT,
            title="Review exact change",
            body="Ready for review.",
            approved=False,
        )

    assert runner.calls == []


def test_create_registered_pull_request_requires_exact_remote_state() -> None:
    default_ref = "refs/heads/main"
    runner = QueueRunner((
        Result(),
        Result(),
        Result(stdout=f"ref: {default_ref}\tHEAD\n"),
        Result(stdout=f"{OTHER}\t{default_ref}\n"),
    ))
    operations = RegisteredGitHubOperations(registry(), runner=runner)
    with pytest.raises(ToolError, match="REMOTE_DEFAULT_MISMATCH"):
        operations.create_pull_request(
            project_id="college",
            branch="feature/example",
            expected_head=TARGET,
            expected_remote_default=REMOTE_DEFAULT,
            title="Review exact change",
            body="Ready for review.",
            approved=True,
        )

    assert not any(call[0][:3] == ("gh", "pr", "create") for call in runner.calls)


def test_create_registered_pull_request_recovers_exact_existing_open_pr() -> None:
    default_ref = "refs/heads/main"
    target_ref = "refs/heads/feature/example"
    url = "https://github.com/nielpieterse0/college/pull/7"
    runner = QueueRunner((
        Result(),
        Result(),
        Result(stdout=f"ref: {default_ref}\tHEAD\n"),
        Result(stdout=f"{REMOTE_DEFAULT}\t{default_ref}\n"),
        Result(stdout=f"{TARGET}\t{target_ref}\n"),
        Result(stdout=pr_api_pages(number=7)),
    ))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.create_pull_request(
        project_id="college",
        branch="feature/example",
        expected_head=TARGET,
        expected_remote_default=REMOTE_DEFAULT,
        title="Review exact change",
        body="Ready for review.",
        approved=True,
    )

    assert result["state"] == "open"
    assert result["pull_number"] == 7
    assert result["head_sha"] == TARGET
    assert result["recovery"] == "existing_exact"
    assert result["url"] == url
    assert not any(call[0][:3] == ("gh", "pr", "create") for call in runner.calls)


def test_create_registered_pull_request_rejects_conflicting_existing_open_pr() -> None:
    default_ref = "refs/heads/main"
    target_ref = "refs/heads/feature/example"
    runner = QueueRunner((
        Result(),
        Result(),
        Result(stdout=f"ref: {default_ref}\tHEAD\n"),
        Result(stdout=f"{REMOTE_DEFAULT}\t{default_ref}\n"),
        Result(stdout=f"{TARGET}\t{target_ref}\n"),
        Result(stdout=pr_api_pages(number=7, head=OTHER)),
    ))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="OPEN_PULL_REQUEST_EXISTS"):
        operations.create_pull_request(
            project_id="college",
            branch="feature/example",
            expected_head=TARGET,
            expected_remote_default=REMOTE_DEFAULT,
            title="Review exact change",
            body="Ready for review.",
            approved=True,
        )

    assert not any(call[0][:3] == ("gh", "pr", "create") for call in runner.calls)


@pytest.mark.parametrize("terminal_state", ["CLOSED", "MERGED"])
def test_create_registered_pull_request_does_not_recreate_exact_terminal_pr(
    terminal_state: str,
) -> None:
    default_ref = "refs/heads/main"
    target_ref = "refs/heads/feature/example"
    runner = QueueRunner((
        Result(),
        Result(),
        Result(stdout=f"ref: {default_ref}\tHEAD\n"),
        Result(stdout=f"{REMOTE_DEFAULT}\t{default_ref}\n"),
        Result(stdout=f"{TARGET}\t{target_ref}\n"),
        Result(stdout=pr_api_pages(number=7, state=terminal_state.lower())),
    ))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="OPEN_PULL_REQUEST_EXISTS"):
        operations.create_pull_request(
            project_id="college",
            branch="feature/example",
            expected_head=TARGET,
            expected_remote_default=REMOTE_DEFAULT,
            title="Review exact change",
            body="Ready for review.",
            approved=True,
        )

    assert not any(call[0][:3] == ("gh", "pr", "create") for call in runner.calls)


def test_create_registered_pull_request_verifies_exact_open_pr() -> None:
    default_ref = "refs/heads/main"
    target_ref = "refs/heads/feature/example"
    runner = QueueRunner((
        Result(),
        Result(),
        Result(stdout=f"ref: {default_ref}\tHEAD\n"),
        Result(stdout=f"{REMOTE_DEFAULT}\t{default_ref}\n"),
        Result(stdout=f"{TARGET}\t{target_ref}\n"),
        Result(stdout="[[]]\n"),
        Result(stdout="https://github.com/nielpieterse0/college/pull/9\n"),
        Result(stdout='{"number":9,"url":"https://github.com/nielpieterse0/college/pull/9","title":"Review exact change","body":"Ready for review.","headRefOid":"1111111111111111111111111111111111111111","baseRefName":"main","state":"OPEN","isDraft":false}\n'),
    ))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.create_pull_request(
        project_id="college",
        branch="feature/example",
        expected_head=TARGET,
        expected_remote_default=REMOTE_DEFAULT,
        title="Review exact change",
        body="Ready for review.",
        approved=True,
    )

    assert result["state"] == "open"
    assert result["pull_number"] == 9
    assert result["head_sha"] == TARGET
    assert result["base_branch"] == "main"
    commands = [call[0] for call in runner.calls]
    create = commands[6]
    assert create == (
        "gh", "pr", "create", "--repo", "nielpieterse0/college",
        "--head", "feature/example", "--base", "main",
        "--title", "Review exact change", "--body", "Ready for review.",
    )
    assert all("merge" not in command for command in commands)
    assert all("delete" not in command for command in commands)
    assert runner.results == []


def test_create_registered_pull_request_refuses_default_branch() -> None:
    default_ref = "refs/heads/main"
    runner = QueueRunner((
        Result(),
        Result(),
        Result(stdout=f"ref: {default_ref}\tHEAD\n"),
    ))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="DEFAULT_BRANCH_PULL_REQUEST_BLOCKED"):
        operations.create_pull_request(
            project_id="college",
            branch="main",
            expected_head=TARGET,
            expected_remote_default=REMOTE_DEFAULT,
            title="Review exact change",
            body="Ready for review.",
            approved=True,
        )

    assert not any(call[0][:3] == ("gh", "pr", "create") for call in runner.calls)


def test_create_registered_pull_request_rejects_stale_review_head() -> None:
    default_ref = "refs/heads/main"
    target_ref = "refs/heads/feature/example"
    runner = QueueRunner((
        Result(),
        Result(),
        Result(stdout=f"ref: {default_ref}\tHEAD\n"),
        Result(stdout=f"{REMOTE_DEFAULT}\t{default_ref}\n"),
        Result(stdout=f"{OTHER}\t{target_ref}\n"),
    ))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="REMOTE_HEAD_MISMATCH"):
        operations.create_pull_request(
            project_id="college",
            branch="feature/example",
            expected_head=TARGET,
            expected_remote_default=REMOTE_DEFAULT,
            title="Review exact change",
            body="Ready for review.",
            approved=True,
        )

    assert not any(call[0][:3] == ("gh", "pr", "create") for call in runner.calls)


def test_create_registered_pull_request_rejects_unverified_created_head() -> None:
    default_ref = "refs/heads/main"
    target_ref = "refs/heads/feature/example"
    runner = QueueRunner((
        Result(),
        Result(),
        Result(stdout=f"ref: {default_ref}\tHEAD\n"),
        Result(stdout=f"{REMOTE_DEFAULT}\t{default_ref}\n"),
        Result(stdout=f"{TARGET}\t{target_ref}\n"),
        Result(stdout="[[]]\n"),
        Result(stdout="https://github.com/nielpieterse0/college/pull/9\n"),
        Result(stdout='{"number":9,"url":"https://github.com/nielpieterse0/college/pull/9","title":"Review exact change","body":"Ready for review.","headRefOid":"3333333333333333333333333333333333333333","baseRefName":"main","state":"OPEN","isDraft":false}\n'),
        Result(stdout=pr_api_pages(number=9, head=OTHER)),
    ))
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.create_pull_request(
        project_id="college",
        branch="feature/example",
        expected_head=TARGET,
        expected_remote_default=REMOTE_DEFAULT,
        title="Review exact change",
        body="Ready for review.",
        approved=True,
    )

    assert result["state"] == "failed"
    assert result["operation_state"] == "failed"
    assert runner.results == []
