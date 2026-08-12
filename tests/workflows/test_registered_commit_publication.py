from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.projects import GitHubProjectBinding, ProjectDefinition, ProjectRegistry
from kis_mcp.projects.github_exact import RegisteredGitHubOperations

TARGET = "1111111111111111111111111111111111111111"
BASE = "2222222222222222222222222222222222222222"
OTHER = "3333333333333333333333333333333333333333"
REMOTE_DEFAULT = "4444444444444444444444444444444444444444"
SOURCE_TREE = "5555555555555555555555555555555555555555"
BASE_TREE = "6666666666666666666666666666666666666666"
OTHER_TREE = "7777777777777777777777777777777777777777"
RECONCILED = "8888888888888888888888888888888888888888"


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

    assert result == {
        "schema_version": 1,
        "state": "published",
        "project_id": "college",
        "repository": "nielpieterse0/college",
        "branch": "feature/example",
        "commit_sha": TARGET,
        "previous_remote_sha": BASE,
        "publication_semantics": "exact_git_object",
    }
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
        merge_method="squash",
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
        "--squash",
    )
    assert "--admin" not in merge


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


def test_delete_remote_branch_refuses_default_branch() -> None:
    runner = QueueRunner(
        (
            Result(),
            Result(),
            Result(stdout="ref: refs/heads/main\tHEAD\n"),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="DEFAULT_BRANCH_DELETE_BLOCKED"):
        operations.delete_remote_branch(
            project_id="college",
            branch="main",
            expected_head=TARGET,
            approved=True,
        )

    assert len(runner.calls) == 3


def test_delete_remote_branch_requires_exact_head_and_verifies_absence() -> None:
    remote_ref = "refs/heads/feature/example"
    runner = QueueRunner(
        (
            Result(),
            Result(),
            Result(stdout="ref: refs/heads/main\tHEAD\n"),
            Result(stdout=f"{TARGET}\t{remote_ref}\n"),
            Result(),
            Result(stdout=""),
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    result = operations.delete_remote_branch(
        project_id="college",
        branch="feature/example",
        expected_head=TARGET,
        approved=True,
    )

    assert result == {
        "schema_version": 1,
        "state": "deleted",
        "project_id": "college",
        "repository": "nielpieterse0/college",
        "branch": "feature/example",
        "deleted_head": TARGET,
        "recovery_sha": TARGET,
    }
    delete = runner.calls[4][0]
    assert "--force-with-lease=refs/heads/feature/example:" + TARGET in delete
    assert ":refs/heads/feature/example" in delete
    assert runner.results == []



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


def test_reconcile_publish_rejects_remote_tree_mismatch_before_commit_or_push() -> None:
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
        )
    )
    operations = RegisteredGitHubOperations(registry(), runner=runner)

    with pytest.raises(ToolError, match="REMOTE_BASE_TREE_MISMATCH"):
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
