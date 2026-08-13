from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.projects import GitHubProjectBinding, ProjectDefinition, ProjectRegistry
from kis_mcp.projects.github_tracking import RegisteredGitHubTrackingOperations

LOCAL = "1111111111111111111111111111111111111111"
OLD = "2222222222222222222222222222222222222222"
REMOTE = "3333333333333333333333333333333333333333"
OTHER = "4444444444444444444444444444444444444444"
TREE = "5555555555555555555555555555555555555555"


@dataclass(frozen=True)
class Result:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def registry() -> ProjectRegistry:
    return ProjectRegistry(
        default_project_id="college",
        projects=(
            ProjectDefinition(
                project_id="college",
                display_name="College",
                local_root="C:\\Projects\\college",
                github=GitHubProjectBinding(repository="NielPieterse0/college"),
            ),
        ),
    )


class RefreshRunner:
    def __init__(
        self,
        *,
        origin: str = "https://github.com/NielPieterse0/college.git",
        drift: bool = False,
        default_branch_drift: bool = False,
    ) -> None:
        self.origin = origin
        self.drift = drift
        self.default_branch_drift = default_branch_drift
        self.calls: list[tuple[str, ...]] = []
        self.remote_reads = 0
        self.default_branch_reads = 0
        self.tracking_reads = 0

    def __call__(
        self, args: Sequence[str], cwd: Path, env: Mapping[str, str]
    ) -> Result:
        del cwd, env
        command = tuple(args)
        self.calls.append(command)
        if command[:4] == ("git", "remote", "get-url", "origin"):
            return Result(stdout=self.origin + "\n")
        if command[:3] == ("gh", "auth", "status"):
            return Result()
        if "ls-remote" in command and "--symref" in command:
            self.default_branch_reads += 1
            branch = (
                "trunk"
                if self.default_branch_drift and self.default_branch_reads > 1
                else "main"
            )
            return Result(stdout=f"ref: refs/heads/{branch}\tHEAD\n")
        if "ls-remote" in command and "--refs" in command:
            self.remote_reads += 1
            sha = OTHER if self.drift and self.remote_reads > 1 else REMOTE
            return Result(stdout=f"{sha}\trefs/heads/main\n")
        if command[:4] == ("git", "show-ref", "--verify", "--hash"):
            if command[-1] == "refs/remotes/origin/main":
                self.tracking_reads += 1
                return Result(stdout=f"{OLD if self.tracking_reads == 1 else REMOTE}\n")
            return Result(stdout=f"{LOCAL}\n")
        if command[:3] == ("git", "cat-file", "-e"):
            return Result(returncode=128)
        if "fetch" in command:
            return Result()
        if command[:4] == ("git", "rev-parse", "--verify", "--end-of-options"):
            return Result(stdout=f"{TREE}\n")
        if command[:3] == ("git", "update-ref", "refs/remotes/origin/main"):
            return Result()
        raise AssertionError(f"unexpected command: {command}")


def test_refresh_requires_explicit_approval_before_commands() -> None:
    runner = RefreshRunner()
    operations = RegisteredGitHubTrackingOperations(registry(), runner=runner)
    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        operations.refresh_default_branch(
            project_id="college", expected_remote_default=REMOTE, approved=False
        )
    assert runner.calls == []


def test_refresh_rejects_origin_mismatch_before_auth_or_network() -> None:
    runner = RefreshRunner(origin="https://github.com/NielPieterse0/other.git")
    operations = RegisteredGitHubTrackingOperations(registry(), runner=runner)
    with pytest.raises(ToolError, match="REGISTERED_REMOTE_MISMATCH"):
        operations.refresh_default_branch(
            project_id="college", expected_remote_default=REMOTE, approved=True
        )
    assert runner.calls == [("git", "remote", "get-url", "origin")]


def test_refresh_fetches_exact_commit_and_cas_updates_only_tracking_ref() -> None:
    runner = RefreshRunner()
    operations = RegisteredGitHubTrackingOperations(registry(), runner=runner)
    result = operations.refresh_default_branch(
        project_id="college", expected_remote_default=REMOTE, approved=True
    )

    assert result["state"] == "refreshed"
    assert result["local_default_sha"] == LOCAL
    assert result["previous_tracking_sha"] == OLD
    assert result["tracking_sha"] == REMOTE
    assert result["github_default_sha"] == REMOTE
    assert result["relation"] == "tree_equivalent"
    assert result["fetched"] is True
    updates = [call for call in runner.calls if call[:2] == ("git", "update-ref")]
    assert updates == [("git", "update-ref", "refs/remotes/origin/main", REMOTE, OLD)]
    assert not any("refs/heads/main" in call[:3] for call in updates)
    fetch = next(call for call in runner.calls if "fetch" in call)
    assert fetch[-6:] == (
        "fetch",
        "--no-tags",
        "--no-recurse-submodules",
        "--no-write-fetch-head",
        "https://github.com/nielpieterse0/college.git",
        "refs/heads/main",
    )


def test_refresh_fails_closed_if_remote_changes_during_materialization() -> None:
    runner = RefreshRunner(drift=True)
    operations = RegisteredGitHubTrackingOperations(registry(), runner=runner)
    with pytest.raises(ToolError, match="REMOTE_DEFAULT_CHANGED"):
        operations.refresh_default_branch(
            project_id="college", expected_remote_default=REMOTE, approved=True
        )
    assert not any(call[:2] == ("git", "update-ref") for call in runner.calls)


def test_refresh_fails_closed_if_default_branch_name_changes() -> None:
    runner = RefreshRunner(default_branch_drift=True)
    operations = RegisteredGitHubTrackingOperations(registry(), runner=runner)
    with pytest.raises(ToolError, match="DEFAULT_BRANCH_CHANGED"):
        operations.refresh_default_branch(
            project_id="college", expected_remote_default=REMOTE, approved=True
        )
    assert not any(call[:2] == ("git", "update-ref") for call in runner.calls)
