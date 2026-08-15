"""Exact GitHub operations for centrally registered repositories."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ..config import load_runtime_config
from ..providers.github.projects.schema_commissioning import (
    GitHubProjectSchemaClient,
    ProjectSchemaTarget,
)
from ..work_management.schema import load_project_schema_manifest
from .contracts import ProjectDefinition
from .registry import ProjectRegistry
from .settings import load_project_registry_settings

_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], Any]
MergeMethod = Literal["merge"]


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

    def _merge_reconciled_tree(
        self,
        *,
        source_base_sha: str,
        remote_default_sha: str,
        source_sha: str,
        cwd: Path,
    ) -> str:
        result = self._run(
            (
                "git",
                "merge-tree",
                "--write-tree",
                "--merge-base",
                source_base_sha,
                remote_default_sha,
                source_sha,
            ),
            cwd,
            allowed_returncodes=frozenset({0, 1}),
        )
        if int(getattr(result, "returncode", -1)) != 0:
            raise ToolError(
                "REMOTE_BASE_RECONCILIATION_CONFLICT: source change conflicts with "
                "the verified remote default branch"
            )
        lines = str(getattr(result, "stdout", "")).splitlines()
        if not lines:
            raise ToolError(
                "REMOTE_BASE_RECONCILIATION_UNVERIFIABLE: merge-tree returned no tree"
            )
        return self._require_sha(lines[0].strip(), "reconciled tree")

    def _select_reconciled_tree(
        self,
        *,
        source_tree: str,
        local_base_tree: str,
        remote_default_tree: str,
        source_base_sha: str,
        remote_default_sha: str,
        source_sha: str,
        cwd: Path,
    ) -> tuple[str, str, str]:
        if remote_default_tree == local_base_tree:
            return source_tree, "tree_equivalent", "remote-default-rooted-tree-equivalent"
        merged_tree = self._merge_reconciled_tree(
            source_base_sha=source_base_sha,
            remote_default_sha=remote_default_sha,
            source_sha=source_sha,
            cwd=cwd,
        )
        return merged_tree, "diverged", "remote-default-rooted-three-way-merge"

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

    def reconcile_publish_commit(
        self,
        *,
        project_id: str,
        commit: str,
        source_base: str,
        branch: str,
        expected_remote_default: str,
        expected_remote_branch: str | None,
        approved: bool,
    ) -> dict[str, object]:
        self._require_approval(approved)
        project, repository, remote_url = self._target(project_id)
        cwd = Path(project.local_root)
        branch_name = self._validate_branch(branch, cwd)

        source_result = self._run(
            (
                "git",
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{str(commit).strip()}^{{commit}}",
            ),
            cwd,
        )
        source_sha = self._require_sha(
            str(getattr(source_result, "stdout", "")).strip(),
            "source commit",
        )
        base_result = self._run(
            (
                "git",
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{str(source_base).strip()}^{{commit}}",
            ),
            cwd,
        )
        source_base_sha = self._require_sha(
            str(getattr(base_result, "stdout", "")).strip(),
            "source base",
        )
        ancestor = self._run(
            ("git", "merge-base", "--is-ancestor", source_base_sha, source_sha),
            cwd,
            allowed_returncodes=frozenset({0, 1}),
        )
        if int(getattr(ancestor, "returncode", -1)) != 0:
            raise ToolError(
                "LOCAL_BASE_NOT_ANCESTOR: source_base is not an ancestor of the source commit"
            )

        local_base_tree_result = self._run(
            (
                "git",
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{source_base_sha}^{{tree}}",
            ),
            cwd,
        )
        local_base_tree = self._require_sha(
            str(getattr(local_base_tree_result, "stdout", "")).strip(),
            "source base tree",
        )
        source_tree_result = self._run(
            (
                "git",
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{source_sha}^{{tree}}",
            ),
            cwd,
        )
        source_tree = self._require_sha(
            str(getattr(source_tree_result, "stdout", "")).strip(),
            "source tree",
        )
        expected_default_sha = self._require_sha(
            expected_remote_default,
            "expected_remote_default",
        )
        expected_branch_sha = (
            None
            if expected_remote_branch is None
            else self._require_sha(expected_remote_branch, "expected_remote_branch")
        )

        self._authenticate(cwd)
        default_branch = self._default_branch(remote_url, cwd)
        if branch_name.casefold() == default_branch.casefold():
            raise ToolError(
                "DEFAULT_BRANCH_PUBLICATION_BLOCKED: reconciliation must publish to a review branch"
            )
        default_ref = f"refs/heads/{default_branch}"
        observed_default = self._remote_branch_sha(remote_url, default_ref, cwd)
        if observed_default != expected_default_sha:
            raise ToolError(
                "REMOTE_DEFAULT_MISMATCH: expected "
                f"{expected_default_sha}, observed {observed_default or '<absent>'}"
            )

        target_ref = f"refs/heads/{branch_name}"
        observed_target = self._remote_branch_sha(remote_url, target_ref, cwd)
        recovering_existing = observed_target is not None and observed_target != expected_branch_sha
        if observed_target != expected_branch_sha and not recovering_existing:
            raise ToolError(
                "REMOTE_BRANCH_MISMATCH: expected "
                f"{expected_branch_sha or '<absent>'}, observed {observed_target or '<absent>'}"
            )

        self._run(
            (
                *self._git_network_prefix(),
                "fetch",
                "--no-tags",
                "--no-recurse-submodules",
                remote_url,
                default_ref,
            ),
            cwd,
        )
        observed_after_fetch = self._remote_branch_sha(remote_url, default_ref, cwd)
        if observed_after_fetch != expected_default_sha:
            raise ToolError(
                "REMOTE_DEFAULT_CHANGED: remote default branch changed during reconciliation"
            )
        remote_tree_result = self._run(
            (
                "git",
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{expected_default_sha}^{{tree}}",
            ),
            cwd,
        )
        remote_default_tree = self._require_sha(
            str(getattr(remote_tree_result, "stdout", "")).strip(),
            "remote default tree",
        )
        base_relation = (
            "tree_equivalent"
            if remote_default_tree == local_base_tree
            else "diverged"
        )

        published_tree, base_relation, publication_semantics = self._select_reconciled_tree(
            source_tree=source_tree,
            local_base_tree=local_base_tree,
            remote_default_tree=remote_default_tree,
            source_base_sha=source_base_sha,
            remote_default_sha=expected_default_sha,
            source_sha=source_sha,
            cwd=cwd,
        )

        message = f"reconcile registered change from {source_sha}"
        if recovering_existing:
            self._run(
                (
                    *self._git_network_prefix(),
                    "fetch",
                    "--no-tags",
                    "--no-recurse-submodules",
                    remote_url,
                    target_ref,
                ),
                cwd,
            )
            observed_after_target_fetch = self._remote_branch_sha(remote_url, target_ref, cwd)
            if observed_after_target_fetch != observed_target:
                raise ToolError(
                    "REMOTE_BRANCH_CHANGED: review branch changed while recovering prior publication"
                )
            existing_tree_result = self._run(
                (
                    "git",
                    "rev-parse",
                    "--verify",
                    "--end-of-options",
                    f"{observed_target}^{{tree}}",
                ),
                cwd,
            )
            existing_tree = self._require_sha(
                str(getattr(existing_tree_result, "stdout", "")).strip(),
                "existing reconciliation tree",
            )
            existing_parents_result = self._run(
                ("git", "rev-list", "--parents", "-n", "1", observed_target),
                cwd,
            )
            existing_parents = str(getattr(existing_parents_result, "stdout", "")).strip().split()
            existing_message_result = self._run(
                ("git", "log", "-1", "--format=%B", observed_target),
                cwd,
            )
            existing_message = str(getattr(existing_message_result, "stdout", "")).strip()
            if (
                existing_tree != published_tree
                or existing_parents != [observed_target, expected_default_sha]
                or existing_message != message
            ):
                raise ToolError(
                    "REMOTE_BRANCH_CONFLICT: existing review branch does not match this exact reconciliation request"
                )
            return {
                "schema_version": 1,
                "state": "published",
                "project_id": project.project_id,
                "repository": repository,
                "branch": branch_name,
                "source_commit_sha": source_sha,
                "source_base_sha": source_base_sha,
                "remote_default_branch": default_branch,
                "remote_default_sha": expected_default_sha,
                "source_tree_sha": source_tree,
                "tree_sha": published_tree,
                "commit_sha": observed_target,
                "previous_remote_sha": expected_branch_sha,
                "base_relation": base_relation,
                "publication_semantics": publication_semantics,
                "recovery": "existing_exact",
            }

        commit_result = self._run(
            (
                "git",
                "commit-tree",
                published_tree,
                "-p",
                expected_default_sha,
                "-m",
                message,
            ),
            cwd,
        )
        reconciled_sha = self._require_sha(
            str(getattr(commit_result, "stdout", "")).strip(),
            "reconciled commit",
        )
        lease = f"--force-with-lease={target_ref}:{expected_branch_sha or ''}"
        self._run(
            (
                *self._git_network_prefix(),
                "push",
                lease,
                remote_url,
                f"{reconciled_sha}:{target_ref}",
            ),
            cwd,
        )
        published = self._remote_branch_sha(remote_url, target_ref, cwd)
        if published != reconciled_sha:
            raise ToolError(
                "PUBLICATION_NOT_VERIFIED: reconciliation branch does not resolve to the generated commit"
            )
        return {
            "schema_version": 1,
            "state": "published",
            "project_id": project.project_id,
            "repository": repository,
            "branch": branch_name,
            "source_commit_sha": source_sha,
            "source_base_sha": source_base_sha,
            "remote_default_branch": default_branch,
            "remote_default_sha": expected_default_sha,
            "source_tree_sha": source_tree,
            "tree_sha": published_tree,
            "commit_sha": reconciled_sha,
            "previous_remote_sha": expected_branch_sha,
            "base_relation": base_relation,
            "publication_semantics": publication_semantics,
        }

    def create_pull_request(
        self,
        *,
        project_id: str,
        branch: str,
        expected_head: str,
        expected_remote_default: str,
        title: str,
        body: str,
        approved: bool,
    ) -> dict[str, object]:
        self._require_approval(approved)
        project, repository, remote_url = self._target(project_id)
        cwd = Path(project.local_root)
        branch_name = self._validate_branch(branch, cwd)
        head_sha = self._require_sha(expected_head, "expected_head")
        default_sha = self._require_sha(expected_remote_default, "expected_remote_default")
        if not isinstance(title, str):
            raise ToolError("INVALID_PULL_REQUEST_TITLE: title must be a string")
        title_text = title.strip()
        if not title_text or len(title_text) > 256:
            raise ToolError("INVALID_PULL_REQUEST_TITLE: title must contain 1 to 256 characters")
        if not isinstance(body, str) or len(body) > 20_000:
            raise ToolError("INVALID_PULL_REQUEST_BODY: body must be a string of at most 20000 characters")

        self._authenticate(cwd)
        default_branch = self._default_branch(remote_url, cwd)
        if branch_name.casefold() == default_branch.casefold():
            raise ToolError("DEFAULT_BRANCH_PULL_REQUEST_BLOCKED: review branch must not be the default branch")
        default_ref = f"refs/heads/{default_branch}"
        observed_default = self._remote_branch_sha(remote_url, default_ref, cwd)
        if observed_default != default_sha:
            raise ToolError(
                f"REMOTE_DEFAULT_MISMATCH: expected {default_sha}, observed {observed_default or '<absent>'}"
            )
        target_ref = f"refs/heads/{branch_name}"
        observed_head = self._remote_branch_sha(remote_url, target_ref, cwd)
        if observed_head != head_sha:
            raise ToolError(
                f"REMOTE_HEAD_MISMATCH: expected {head_sha}, observed {observed_head or '<absent>'}"
            )

        existing_result = self._run(
            (
                "gh", "pr", "list", "--repo", repository,
                "--head", branch_name, "--base", default_branch,
                "--state", "all", "--limit", "100",
                "--json", "number,url,title,body,headRefOid,baseRefName,state,isDraft",
            ),
            cwd,
        )
        try:
            existing = json.loads(str(getattr(existing_result, "stdout", "")))
        except json.JSONDecodeError as exc:
            raise ToolError("PULL_REQUEST_STATE_UNVERIFIABLE: gh returned invalid JSON") from exc
        if not isinstance(existing, list):
            raise ToolError("PULL_REQUEST_STATE_UNVERIFIABLE: gh returned a non-array PR list")
        if existing:
            if not all(isinstance(item, Mapping) for item in existing):
                raise ToolError("PULL_REQUEST_STATE_UNVERIFIABLE: gh returned malformed pull request entries")
            exact = [
                item
                for item in existing
                if str(item.get("headRefOid", "")).lower() == head_sha
                and item.get("baseRefName") == default_branch
                and item.get("title") == title_text
                and item.get("body") == body
            ]
            if len(exact) != 1:
                raise ToolError(
                    "OPEN_PULL_REQUEST_EXISTS: existing pull request history conflicts with this exact request"
                )
            recovered = exact[0]
            pull_number = recovered.get("number")
            if isinstance(pull_number, bool) or not isinstance(pull_number, int) or pull_number <= 0:
                raise ToolError("PULL_REQUEST_STATE_UNVERIFIABLE: existing pull request number is invalid")
            if recovered.get("state") != "OPEN" or recovered.get("isDraft") is True:
                raise ToolError(
                    "OPEN_PULL_REQUEST_EXISTS: exact prior pull request is no longer an open non-draft review"
                )
            return {
                "schema_version": 1,
                "state": "open",
                "project_id": project.project_id,
                "repository": repository,
                "pull_number": pull_number,
                "url": str(recovered.get("url") or ""),
                "branch": branch_name,
                "head_sha": head_sha,
                "base_branch": default_branch,
                "base_sha": default_sha,
                "recovery": "existing_exact",
            }

        create_result = self._run(
            (
                "gh", "pr", "create", "--repo", repository,
                "--head", branch_name, "--base", default_branch,
                "--title", title_text, "--body", body,
            ),
            cwd,
        )
        created_url = str(getattr(create_result, "stdout", "")).strip()
        match = re.search(r"/pull/(\d+)(?:\?.*)?$", created_url)
        if match is None:
            raise ToolError("PULL_REQUEST_CREATE_UNVERIFIABLE: gh did not return a pull request URL")
        pull_number = int(match.group(1))
        after = self._pr_view(repository, pull_number, cwd)
        after_head = str(after.get("headRefOid", "")).lower()
        if (
            after.get("state") != "OPEN"
            or after.get("isDraft") is True
            or after_head != head_sha
            or after.get("baseRefName") != default_branch
        ):
            raise ToolError("PULL_REQUEST_CREATE_NOT_VERIFIED: created pull request state/head/base mismatch")
        return {
            "schema_version": 1,
            "state": "open",
            "project_id": project.project_id,
            "repository": repository,
            "pull_number": pull_number,
            "url": str(after.get("url") or created_url),
            "branch": branch_name,
            "head_sha": head_sha,
            "base_branch": default_branch,
            "base_sha": default_sha,
        }

    def configure_repository_landing_policy(
        self,
        *,
        project_id: str,
        approved: bool,
    ) -> dict[str, object]:
        self._require_approval(approved)
        project, repository, _ = self._target(project_id)
        cwd = Path(project.local_root)
        self._authenticate(cwd)
        self._run(
            (
                "gh",
                "api",
                "--method",
                "PATCH",
                f"repos/{repository}",
                "-F",
                "allow_merge_commit=true",
                "-F",
                "allow_squash_merge=false",
                "-F",
                "allow_rebase_merge=false",
                "-F",
                "delete_branch_on_merge=false",
            ),
            cwd,
        )
        observed = self._run(("gh", "api", f"repos/{repository}"), cwd)
        try:
            payload = json.loads(str(getattr(observed, "stdout", "")))
        except json.JSONDecodeError as exc:
            raise ToolError("REPOSITORY_POLICY_UNVERIFIABLE: gh returned invalid JSON") from exc
        if not isinstance(payload, Mapping):
            raise ToolError("REPOSITORY_POLICY_UNVERIFIABLE: gh returned a non-object")
        expected = {
            "allow_merge_commit": True,
            "allow_squash_merge": False,
            "allow_rebase_merge": False,
            "delete_branch_on_merge": False,
        }
        if any(payload.get(key) is not value for key, value in expected.items()):
            raise ToolError("REPOSITORY_POLICY_NOT_VERIFIED: landing settings do not match KIS policy")
        return {
            "schema_version": 1,
            "state": "configured",
            "project_id": project.project_id,
            "repository": repository,
            **expected,
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
                "number,url,headRefOid,baseRefName,state,isDraft",
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
        if merge_method != "merge":
            raise ToolError("INVALID_MERGE_METHOD: repository policy requires merge commits")
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

    def commission_project_schema(
        self,
        *,
        project_id: str,
        project_binding_id: str,
        approved: bool,
    ) -> dict[str, object]:
        self._require_approval(approved)
        if not isinstance(project_binding_id, str) or not project_binding_id.strip():
            raise ToolError(
                "INVALID_REGISTERED_GITHUB_ARGUMENTS: project_binding_id must be a non-empty string"
            )
        project, _repository, _remote_url = self._target(project_id)
        if project.github is None:
            raise ToolError(f"GITHUB_BINDING_REQUIRED: {project_id}")
        project_binding_id = project_binding_id.strip()
        resource = next(
            (
                item
                for item in project.github.projects
                if item.binding_id == project_binding_id
            ),
            None,
        )
        if resource is None:
            raise ToolError(
                f"REGISTERED_GITHUB_PROJECT_REQUIRED: {project_id}/{project_binding_id}"
            )
        if self.gh_config_dir is None:
            raise ToolError("REGISTERED_GITHUB_AUTH_STATE_REQUIRED: GH_CONFIG_DIR is not configured")
        cwd = Path(project.local_root)
        self._authenticate(cwd)
        client = GitHubProjectSchemaClient(
            gh_config_dir=self.gh_config_dir,
            cwd=cwd,
            runner=self.runner,
        )
        try:
            result = client.commission(
                ProjectSchemaTarget(
                    owner=resource.owner,
                    owner_type=resource.owner_type,
                    project_number=resource.project_number,
                ),
                load_project_schema_manifest(),
            )
        except Exception as exc:
            raise ToolError(
                f"REGISTERED_GITHUB_PROJECT_SCHEMA_FAILED: {type(exc).__name__}: {exc}"
            ) from exc
        return {
            "schema_version": 1,
            "state": "ready",
            "project_id": project.project_id,
            "project_binding_id": resource.binding_id,
            "owner": resource.owner,
            "owner_type": resource.owner_type,
            "project_number": resource.project_number,
            **result,
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
    "kis_github_reconcile_registered_commit": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "commit": {"type": "string"},
            "source_base": {"type": "string"},
            "branch": {"type": "string"},
            "expected_remote_default": {"type": "string"},
            "expected_remote_branch": {
                "anyOf": [{"type": "string"}, {"type": "null"}]
            },
            "approved": {"type": "boolean"},
        },
        "required": [
            "project_id",
            "commit",
            "source_base",
            "branch",
            "expected_remote_default",
            "expected_remote_branch",
            "approved",
        ],
        "additionalProperties": False,
    },
    "kis_github_create_registered_pull_request": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "branch": {"type": "string"},
            "expected_head": {"type": "string"},
            "expected_remote_default": {"type": "string"},
            "title": {"type": "string", "minLength": 1, "maxLength": 256},
            "body": {"type": "string", "maxLength": 20000},
            "approved": {"type": "boolean"},
        },
        "required": [
            "project_id",
            "branch",
            "expected_head",
            "expected_remote_default",
            "title",
            "body",
            "approved",
        ],
        "additionalProperties": False,
    },
    "kis_github_configure_registered_repository": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "approved": {"type": "boolean"},
        },
        "required": ["project_id", "approved"],
        "additionalProperties": False,
    },
    "kis_github_commission_registered_project_schema": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "project_binding_id": {"type": "string"},
            "approved": {"type": "boolean"},
        },
        "required": ["project_id", "project_binding_id", "approved"],
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
                "enum": ["merge"],
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
    for name in (
        "project_id",
        "project_binding_id",
        "commit",
        "source_base",
        "branch",
        "expected_remote_default",
        "expected_head",
        "merge_method",
        "title",
    ):
        if name in values and (not isinstance(values[name], str) or not values[name].strip()):
            raise ToolError(
                f"INVALID_REGISTERED_GITHUB_ARGUMENTS: {name} must be a non-empty string"
            )
    for name in ("expected_remote_base", "expected_remote_branch"):
        if name in values and values[name] is not None and not isinstance(values[name], str):
            raise ToolError(
                f"INVALID_REGISTERED_GITHUB_ARGUMENTS: {name} must be a string or null"
            )
    if "title" in values and len(values["title"].strip()) > 256:
        raise ToolError("INVALID_REGISTERED_GITHUB_ARGUMENTS: title is too long")
    if "body" in values and (
        not isinstance(values["body"], str) or len(values["body"]) > 20_000
    ):
        raise ToolError("INVALID_REGISTERED_GITHUB_ARGUMENTS: body must be a string of at most 20000 characters")
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
    if operation == "kis_github_reconcile_registered_commit":
        return service.reconcile_publish_commit(
            project_id=values["project_id"],
            commit=values["commit"],
            source_base=values["source_base"],
            branch=values["branch"],
            expected_remote_default=values["expected_remote_default"],
            expected_remote_branch=values["expected_remote_branch"],
            approved=values["approved"],
        )
    if operation == "kis_github_create_registered_pull_request":
        return service.create_pull_request(
            project_id=values["project_id"],
            branch=values["branch"],
            expected_head=values["expected_head"],
            expected_remote_default=values["expected_remote_default"],
            title=values["title"],
            body=values["body"],
            approved=values["approved"],
        )
    if operation == "kis_github_configure_registered_repository":
        return service.configure_repository_landing_policy(
            project_id=values["project_id"],
            approved=values["approved"],
        )
    if operation == "kis_github_commission_registered_project_schema":
        return service.commission_project_schema(
            project_id=values["project_id"],
            project_binding_id=values["project_binding_id"],
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
