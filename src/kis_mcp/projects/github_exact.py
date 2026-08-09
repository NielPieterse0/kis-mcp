from __future__ import annotations

"""Exact GitHub operations for centrally registered repositories."""

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ..config import load_runtime_config
from .contracts import ProjectDefinition
from .registry import ProjectRegistry
from .settings import load_project_registry_settings

_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], Any]
MergeMethod = Literal["merge", "squash", "rebase"]


def _default_runner(
    args: Sequence[str],
    cwd: Path,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            cwd=cwd,
            env=dict(env),
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"REGISTERED_GITHUB_COMMAND_MISSING: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"REGISTERED_GITHUB_COMMAND_TIMEOUT: {args[0]}") from exc


class RegisteredGitHubOperations:
    """Bounded exact-ref GitHub operations resolved from the central registry."""

    def __init__(
        self,
        projects: ProjectRegistry,
        *,
        runner: CommandRunner | None = None,
        gh_config_dir: Path | None = None,
    ) -> None:
        self.projects = projects
        self.runner = runner or _default_runner
        self.gh_config_dir = gh_config_dir

    @staticmethod
    def _require_approval(approved: bool) -> None:
        if approved is not True:
            raise ToolError(
                "APPROVAL_REQUIRED: explicit approval is required for this GitHub mutation"
            )

    def _target(self, project_id: str) -> tuple[ProjectDefinition, str, str]:
        try:
            project = self.projects.project(project_id)
        except KeyError as exc:
            raise ToolError(f"REGISTERED_PROJECT_REQUIRED: {project_id}") from exc
        if project.github is None:
            raise ToolError(f"GITHUB_BINDING_REQUIRED: {project_id}")
        repository = project.github.repository
        return project, repository, f"https://github.com/{repository}.git"

    @staticmethod
    def _require_sha(value: str, label: str) -> str:
        normalized = str(value).strip().lower()
        if _SHA.fullmatch(normalized) is None:
            raise ToolError(f"INVALID_GITHUB_SHA: {label} must be a full 40-character SHA")
        return normalized

    def command_environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        for key in (
            "GH_TOKEN",
            "GITHUB_TOKEN",
            "GH_ENTERPRISE_TOKEN",
            "GITHUB_ENTERPRISE_TOKEN",
        ):
            environment.pop(key, None)
        if self.gh_config_dir is not None:
            environment["GH_CONFIG_DIR"] = str(self.gh_config_dir)
        environment["GIT_TERMINAL_PROMPT"] = "0"
        environment["GCM_INTERACTIVE"] = "Never"
        return environment

    def _run(
        self,
        args: Sequence[str],
        cwd: Path,
        *,
        allowed_returncodes: frozenset[int] = frozenset({0}),
    ) -> Any:
        result = self.runner(tuple(args), cwd, self.command_environment())
        returncode = int(getattr(result, "returncode", -1))
        if returncode not in allowed_returncodes:
            detail = str(getattr(result, "stderr", "")).strip() or str(
                getattr(result, "stdout", "")
            ).strip()
            if len(detail) > 1000:
                detail = detail[:1000] + "...<truncated>"
            raise ToolError(
                f"REGISTERED_GITHUB_COMMAND_FAILED: {args[0]} exited {returncode}"
                + (f": {detail}" if detail else "")
            )
        return result

    @staticmethod
    def _git_network_prefix() -> tuple[str, ...]:
        return (
            "git",
            "-c",
            "credential.https://github.com.helper=",
            "-c",
            "credential.https://github.com.helper=!gh auth git-credential",
        )

    def _validate_branch(self, branch: str, cwd: Path) -> str:
        normalized = str(branch).strip()
        if not normalized or normalized.startswith("-"):
            raise ToolError("INVALID_GITHUB_BRANCH: branch must be a non-option Git branch name")
        self._run(("git", "check-ref-format", "--branch", normalized), cwd)
        return normalized

    def _authenticate(self, cwd: Path) -> None:
        self._run(
            ("gh", "auth", "status", "--active", "--hostname", "github.com"),
            cwd,
        )

    def _remote_branch_sha(self, remote_url: str, ref: str, cwd: Path) -> str | None:
        result = self._run(
            (*self._git_network_prefix(), "ls-remote", "--refs", remote_url, ref),
            cwd,
        )
        output = str(getattr(result, "stdout", "")).strip()
        if not output:
            return None
        for line in output.splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[1] == ref:
                return self._require_sha(fields[0], "remote ref")
        raise ToolError(f"REMOTE_REF_UNVERIFIABLE: {ref}")

    def _default_branch(self, remote_url: str, cwd: Path) -> str:
        result = self._run(
            (*self._git_network_prefix(), "ls-remote", "--symref", remote_url, "HEAD"),
            cwd,
        )
        for line in str(getattr(result, "stdout", "")).splitlines():
            if not line.startswith("ref:") or "HEAD" not in line:
                continue
            fields = line.replace("\t", " ").split()
            if len(fields) >= 3 and fields[0] == "ref:" and fields[2] == "HEAD":
                ref = fields[1]
                prefix = "refs/heads/"
                if ref.startswith(prefix) and len(ref) > len(prefix):
                    return ref[len(prefix) :]
        raise ToolError("DEFAULT_BRANCH_UNVERIFIABLE: remote HEAD did not identify a branch")

    def publish_commit(
        self,
        *,
        project_id: str,
        commit: str,
        branch: str,
        expected_remote_base: str | None,
        approved: bool,
    ) -> dict[str, object]:
        self._require_approval(approved)
        project, repository, remote_url = self._target(project_id)
        cwd = Path(project.local_root)
        branch_name = self._validate_branch(branch, cwd)
        target_result = self._run(
            (
                "git",
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{str(commit).strip()}^{{commit}}",
            ),
            cwd,
        )
        target_sha = self._require_sha(
            str(getattr(target_result, "stdout", "")).strip(),
            "local commit",
        )
        expected_sha = (
            None
            if expected_remote_base is None
            else self._require_sha(expected_remote_base, "expected_remote_base")
        )
        if expected_sha is not None:
            ancestor = self._run(
                ("git", "merge-base", "--is-ancestor", expected_sha, target_sha),
                cwd,
                allowed_returncodes=frozenset({0, 1}),
            )
            if int(getattr(ancestor, "returncode", -1)) != 0:
                raise ToolError(
                    "NON_FAST_FORWARD_PUBLICATION: expected remote base is not an ancestor "
                    "of the immutable local commit"
                )

        self._authenticate(cwd)
        ref = f"refs/heads/{branch_name}"
        observed = self._remote_branch_sha(remote_url, ref, cwd)
        if observed != expected_sha:
            raise ToolError(
                "REMOTE_BASE_MISMATCH: expected "
                f"{expected_sha or '<absent>'}, observed {observed or '<absent>'}"
            )

        lease = f"--force-with-lease={ref}:{expected_sha or ''}"
        self._run(
            (
                *self._git_network_prefix(),
                "push",
                lease,
                remote_url,
                f"{target_sha}:{ref}",
            ),
            cwd,
        )
        published = self._remote_branch_sha(remote_url, ref, cwd)
        if published != target_sha:
            raise ToolError(
                "PUBLICATION_NOT_VERIFIED: remote branch does not resolve to the exact local commit"
            )
        return {
            "schema_version": 1,
            "state": "published",
            "project_id": project.project_id,
            "repository": repository,
            "branch": branch_name,
            "commit_sha": target_sha,
            "previous_remote_sha": expected_sha,
            "publication_semantics": "exact_git_object",
        }

    def _pr_view(self, repository: str, pull_number: int, cwd: Path) -> dict[str, object]:
        result = self._run(
            (
                "gh",
                "pr",
                "view",
                str(pull_number),
                "--repo",
                repository,
                "--json",
                "headRefOid,state,isDraft",
            ),
            cwd,
        )
        try:
            payload = json.loads(str(getattr(result, "stdout", "")))
        except json.JSONDecodeError as exc:
            raise ToolError("PULL_REQUEST_STATE_UNVERIFIABLE: gh returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ToolError("PULL_REQUEST_STATE_UNVERIFIABLE: gh returned a non-object")
        return payload

    def merge_pull_request(
        self,
        *,
        project_id: str,
        pull_number: int,
        expected_head: str,
        merge_method: MergeMethod,
        approved: bool,
    ) -> dict[str, object]:
        self._require_approval(approved)
        project, repository, _ = self._target(project_id)
        if isinstance(pull_number, bool) or not isinstance(pull_number, int) or pull_number <= 0:
            raise ToolError("INVALID_PULL_REQUEST: pull_number must be a positive integer")
        if merge_method not in {"merge", "squash", "rebase"}:
            raise ToolError("INVALID_MERGE_METHOD: use merge, squash, or rebase")
        authorized_head = self._require_sha(expected_head, "expected_head")
        cwd = Path(project.local_root)
        self._authenticate(cwd)
        before = self._pr_view(repository, pull_number, cwd)
        observed_head = str(before.get("headRefOid", "")).lower()
        if observed_head != authorized_head:
            raise ToolError(
                f"PULL_REQUEST_HEAD_MISMATCH: expected {authorized_head}, observed {observed_head or '<unknown>'}"
            )
        if before.get("state") != "OPEN" or before.get("isDraft") is True:
            raise ToolError("PULL_REQUEST_NOT_MERGEABLE_STATE: pull request must be open and non-draft")

        self._run(
            (
                "gh",
                "pr",
                "merge",
                str(pull_number),
                "--repo",
                repository,
                "--match-head-commit",
                authorized_head,
                f"--{merge_method}",
            ),
            cwd,
        )
        after = self._pr_view(repository, pull_number, cwd)
        after_head = str(after.get("headRefOid", "")).lower()
        if after.get("state") != "MERGED" or after_head != authorized_head:
            raise ToolError(
                "MERGE_NOT_VERIFIED: pull request is not merged at the explicitly authorized head"
            )
        return {
            "schema_version": 1,
            "state": "merged",
            "project_id": project.project_id,
            "repository": repository,
            "pull_number": pull_number,
            "authorized_head": authorized_head,
            "merge_method": merge_method,
        }

    def delete_remote_branch(
        self,
        *,
        project_id: str,
        branch: str,
        expected_head: str,
        approved: bool,
    ) -> dict[str, object]:
        self._require_approval(approved)
        project, repository, remote_url = self._target(project_id)
        expected_sha = self._require_sha(expected_head, "expected_head")
        cwd = Path(project.local_root)
        branch_name = self._validate_branch(branch, cwd)
        self._authenticate(cwd)
        if branch_name.casefold() == self._default_branch(remote_url, cwd).casefold():
            raise ToolError("DEFAULT_BRANCH_DELETE_BLOCKED: refusing to delete the repository default branch")

        ref = f"refs/heads/{branch_name}"
        observed = self._remote_branch_sha(remote_url, ref, cwd)
        if observed is None:
            raise ToolError(f"REMOTE_BRANCH_NOT_FOUND: {branch_name}")
        if observed != expected_sha:
            raise ToolError(
                f"REMOTE_HEAD_MISMATCH: expected {expected_sha}, observed {observed}"
            )
        self._run(
            (
                *self._git_network_prefix(),
                "push",
                f"--force-with-lease={ref}:{expected_sha}",
                remote_url,
                f":{ref}",
            ),
            cwd,
        )
        if self._remote_branch_sha(remote_url, ref, cwd) is not None:
            raise ToolError("BRANCH_DELETE_NOT_VERIFIED: remote branch still exists")
        return {
            "schema_version": 1,
            "state": "deleted",
            "project_id": project.project_id,
            "repository": repository,
            "branch": branch_name,
            "deleted_head": expected_sha,
            "recovery_sha": expected_sha,
        }


REGISTERED_GITHUB_OPERATION_SCHEMAS: dict[str, dict[str, object]] = {
    "kis_github_publish_registered_commit": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "commit": {"type": "string"},
            "branch": {"type": "string"},
            "expected_remote_base": {
                "anyOf": [{"type": "string"}, {"type": "null"}]
            },
            "approved": {"type": "boolean"},
        },
        "required": ["project_id", "commit", "branch", "approved"],
        "additionalProperties": False,
    },
    "kis_github_merge_registered_pull_request": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "pull_number": {"type": "integer", "minimum": 1},
            "expected_head": {"type": "string"},
            "merge_method": {
                "type": "string",
                "enum": ["merge", "squash", "rebase"],
            },
            "approved": {"type": "boolean"},
        },
        "required": [
            "project_id",
            "pull_number",
            "expected_head",
            "merge_method",
            "approved",
        ],
        "additionalProperties": False,
    },
    "kis_github_delete_registered_branch": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "branch": {"type": "string"},
            "expected_head": {"type": "string"},
            "approved": {"type": "boolean"},
        },
        "required": ["project_id", "branch", "expected_head", "approved"],
        "additionalProperties": False,
    },
}


def _validated_arguments(
    operation: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    schema = REGISTERED_GITHUB_OPERATION_SCHEMAS.get(operation)
    if schema is None:
        raise ToolError(f"UNKNOWN_REGISTERED_GITHUB_OPERATION: {operation}")
    if not isinstance(arguments, Mapping):
        raise ToolError("INVALID_ACTION_ARGUMENTS: arguments must be an object")
    properties = schema["properties"]
    required = set(schema["required"])
    values = dict(arguments)
    unknown = sorted(set(values) - set(properties))
    missing = sorted(required - set(values))
    if unknown:
        raise ToolError(
            "INVALID_REGISTERED_GITHUB_ARGUMENTS: unknown fields: "
            + ", ".join(unknown)
        )
    if missing:
        raise ToolError(
            "INVALID_REGISTERED_GITHUB_ARGUMENTS: missing fields: "
            + ", ".join(missing)
        )
    if values.get("approved") is not True:
        raise ToolError("APPROVAL_REQUIRED: approved must be true")
    for name in ("project_id", "commit", "branch", "expected_head", "merge_method"):
        if name in values and (not isinstance(values[name], str) or not values[name].strip()):
            raise ToolError(
                f"INVALID_REGISTERED_GITHUB_ARGUMENTS: {name} must be a non-empty string"
            )
    if "expected_remote_base" in values and values["expected_remote_base"] is not None:
        if not isinstance(values["expected_remote_base"], str):
            raise ToolError(
                "INVALID_REGISTERED_GITHUB_ARGUMENTS: expected_remote_base must be a string or null"
            )
    if "pull_number" in values and (
        isinstance(values["pull_number"], bool)
        or not isinstance(values["pull_number"], int)
        or values["pull_number"] <= 0
    ):
        raise ToolError(
            "INVALID_REGISTERED_GITHUB_ARGUMENTS: pull_number must be a positive integer"
        )
    return values


def _runtime_operations() -> RegisteredGitHubOperations:
    runtime = load_runtime_config()
    projects = load_project_registry_settings(boundary=runtime.project_boundary)
    return RegisteredGitHubOperations(
        projects,
        gh_config_dir=Path(runtime.github_cli_config_dir),
    )


def execute_registered_github_operation(
    operation: str,
    arguments: Mapping[str, Any],
    *,
    operations: RegisteredGitHubOperations | None = None,
) -> dict[str, object]:
    values = _validated_arguments(operation, arguments)
    service = operations or _runtime_operations()
    if operation == "kis_github_publish_registered_commit":
        return service.publish_commit(
            project_id=values["project_id"],
            commit=values["commit"],
            branch=values["branch"],
            expected_remote_base=values.get("expected_remote_base"),
            approved=values["approved"],
        )
    if operation == "kis_github_merge_registered_pull_request":
        return service.merge_pull_request(
            project_id=values["project_id"],
            pull_number=values["pull_number"],
            expected_head=values["expected_head"],
            merge_method=values["merge_method"],
            approved=values["approved"],
        )
    return service.delete_remote_branch(
        project_id=values["project_id"],
        branch=values["branch"],
        expected_head=values["expected_head"],
        approved=values["approved"],
    )


__all__ = [
    "REGISTERED_GITHUB_OPERATION_SCHEMAS",
    "RegisteredGitHubOperations",
    "execute_registered_github_operation",
]
