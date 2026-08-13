"""Bounded remote-tracking refresh for centrally registered GitHub repositories."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastmcp.exceptions import ToolError

from ..config import load_runtime_config
from .github_exact import CommandRunner, RegisteredGitHubOperations
from .registry import ProjectRegistry
from .settings import load_project_registry_settings

_ZERO_SHA = "0" * 40


def _normalized_github_repository(value: str) -> str | None:
    raw = str(value).strip()
    if raw.lower().startswith("git@github.com:"):
        path = raw.split(":", 1)[1]
    elif "://" in raw:
        parsed = urlsplit(raw)
        if (parsed.hostname or "").casefold() != "github.com":
            return None
        path = parsed.path.lstrip("/")
    else:
        return None
    if path.casefold().endswith(".git"):
        path = path[:-4]
    parts = [part for part in path.split("/") if part]
    if len(parts) != 2:
        return None
    return f"{parts[0].casefold()}/{parts[1].casefold()}"


class RegisteredGitHubTrackingOperations(RegisteredGitHubOperations):
    """Refresh only the verified registered remote-tracking default-branch ref."""

    def __init__(
        self,
        projects: ProjectRegistry,
        *,
        runner: CommandRunner | None = None,
        gh_config_dir: Path | None = None,
    ) -> None:
        super().__init__(projects, runner=runner, gh_config_dir=gh_config_dir)

    def _ref_sha(self, cwd: Path, ref: str) -> str | None:
        result = self._run(
            ("git", "show-ref", "--verify", "--hash", ref),
            cwd,
            allowed_returncodes=frozenset({0, 1}),
        )
        if int(getattr(result, "returncode", -1)) != 0:
            return None
        return self._require_sha(str(getattr(result, "stdout", "")).strip(), ref)

    def _tree_sha(self, cwd: Path, commit: str) -> str:
        result = self._run(
            ("git", "rev-parse", "--verify", "--end-of-options", f"{commit}^{{tree}}"),
            cwd,
        )
        return self._require_sha(str(getattr(result, "stdout", "")).strip(), "tree")

    def refresh_default_branch(
        self,
        *,
        project_id: str,
        expected_remote_default: str,
        approved: bool,
    ) -> dict[str, object]:
        self._require_approval(approved)
        project, repository, remote_url = self._target(project_id)
        cwd = Path(project.local_root)
        expected_sha = self._require_sha(
            expected_remote_default, "expected_remote_default"
        )

        origin_result = self._run(("git", "remote", "get-url", "origin"), cwd)
        origin_repository = _normalized_github_repository(
            str(getattr(origin_result, "stdout", "")).strip()
        )
        if origin_repository != repository.casefold():
            raise ToolError(
                "REGISTERED_REMOTE_MISMATCH: origin does not identify the registered GitHub repository"
            )

        self._authenticate(cwd)
        default_branch = self._default_branch(remote_url, cwd)
        default_ref = f"refs/heads/{default_branch}"
        tracking_ref = f"refs/remotes/origin/{default_branch}"
        observed = self._remote_branch_sha(remote_url, default_ref, cwd)
        if observed != expected_sha:
            raise ToolError(
                f"REMOTE_DEFAULT_MISMATCH: expected {expected_sha}, observed {observed or '<absent>'}"
            )
        previous_tracking = self._ref_sha(cwd, tracking_ref)
        object_probe = self._run(
            ("git", "cat-file", "-e", f"{expected_sha}^{{commit}}"),
            cwd,
            allowed_returncodes=frozenset({0, 1, 128}),
        )
        fetched = int(getattr(object_probe, "returncode", -1)) != 0
        if fetched:
            self._run(
                (
                    *self._git_network_prefix(),
                    "fetch",
                    "--no-tags",
                    "--no-recurse-submodules",
                    "--no-write-fetch-head",
                    remote_url,
                    default_ref,
                ),
                cwd,
            )

        observed_after_materialization = self._remote_branch_sha(
            remote_url, default_ref, cwd
        )
        if observed_after_materialization != expected_sha:
            raise ToolError(
                "REMOTE_DEFAULT_CHANGED: remote default branch changed during refresh"
            )
        default_branch_after_materialization = self._default_branch(remote_url, cwd)
        if default_branch_after_materialization.casefold() != default_branch.casefold():
            raise ToolError(
                "DEFAULT_BRANCH_CHANGED: repository default branch changed during refresh"
            )

        github_tree = self._tree_sha(cwd, expected_sha)
        local_ref = f"refs/heads/{default_branch}"
        local_sha = self._ref_sha(cwd, local_ref)
        local_tree = self._tree_sha(cwd, local_sha) if local_sha is not None else None
        if local_sha == expected_sha:
            relation = "same_commit"
        elif local_tree is not None and local_tree == github_tree:
            relation = "tree_equivalent"
        else:
            relation = "content_divergent"

        if previous_tracking != expected_sha:
            self._run(
                (
                    "git",
                    "update-ref",
                    tracking_ref,
                    expected_sha,
                    previous_tracking or _ZERO_SHA,
                ),
                cwd,
            )
        tracking_sha = self._ref_sha(cwd, tracking_ref)
        if tracking_sha != expected_sha:
            raise ToolError(
                "TRACKING_REF_UPDATE_NOT_VERIFIED: tracking ref does not equal GitHub default"
            )

        return {
            "schema_version": 1,
            "state": "current" if previous_tracking == expected_sha else "refreshed",
            "project_id": project.project_id,
            "repository": repository,
            "default_branch": default_branch,
            "local_default_ref": local_ref,
            "local_default_sha": local_sha,
            "local_default_tree": local_tree,
            "tracking_ref": tracking_ref,
            "previous_tracking_sha": previous_tracking,
            "tracking_sha": tracking_sha,
            "github_default_ref": default_ref,
            "github_default_sha": expected_sha,
            "github_default_tree": github_tree,
            "relation": relation,
            "fetched": fetched,
        }


REGISTERED_GITHUB_TRACKING_OPERATION_SCHEMAS: dict[str, dict[str, object]] = {
    "kis_github_refresh_registered_default_branch": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "expected_remote_default": {"type": "string"},
            "approved": {"type": "boolean"},
        },
        "required": ["project_id", "expected_remote_default", "approved"],
        "additionalProperties": False,
    }
}


def _validated_arguments(
    operation: str, arguments: Mapping[str, Any]
) -> dict[str, Any]:
    schema = REGISTERED_GITHUB_TRACKING_OPERATION_SCHEMAS.get(operation)
    if schema is None:
        raise ToolError(f"UNKNOWN_REGISTERED_GITHUB_TRACKING_OPERATION: {operation}")
    if not isinstance(arguments, Mapping):
        raise ToolError("INVALID_ACTION_ARGUMENTS: arguments must be an object")
    properties = schema["properties"]
    required = set(schema["required"])
    values = dict(arguments)
    unknown = sorted(set(values) - set(properties))
    missing = sorted(required - set(values))
    if unknown:
        raise ToolError(
            "INVALID_REGISTERED_GITHUB_TRACKING_ARGUMENTS: unknown fields: "
            + ", ".join(unknown)
        )
    if missing:
        raise ToolError(
            "INVALID_REGISTERED_GITHUB_TRACKING_ARGUMENTS: missing fields: "
            + ", ".join(missing)
        )
    if values.get("approved") is not True:
        raise ToolError("APPROVAL_REQUIRED: approved must be true")
    for name in ("project_id", "expected_remote_default"):
        if not isinstance(values[name], str) or not values[name].strip():
            raise ToolError(
                f"INVALID_REGISTERED_GITHUB_TRACKING_ARGUMENTS: {name} must be non-empty"
            )
    return values


def _runtime_tracking_operations() -> RegisteredGitHubTrackingOperations:
    runtime = load_runtime_config()
    projects = load_project_registry_settings(boundary=runtime.project_boundary)
    return RegisteredGitHubTrackingOperations(
        projects,
        gh_config_dir=Path(runtime.github_cli_config_dir),
    )


def execute_registered_github_tracking_operation(
    operation: str,
    arguments: Mapping[str, Any],
    *,
    operations: RegisteredGitHubTrackingOperations | None = None,
) -> dict[str, object]:
    values = _validated_arguments(operation, arguments)
    service = operations or _runtime_tracking_operations()
    return service.refresh_default_branch(
        project_id=values["project_id"],
        expected_remote_default=values["expected_remote_default"],
        approved=values["approved"],
    )


__all__ = [
    "REGISTERED_GITHUB_TRACKING_OPERATION_SCHEMAS",
    "RegisteredGitHubTrackingOperations",
    "execute_registered_github_tracking_operation",
]
