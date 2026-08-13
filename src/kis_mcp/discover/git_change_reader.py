from __future__ import annotations

import time
from pathlib import Path

from .change_inspection_contracts import InspectChangeRequest
from .change_targets import ChangeTargetInventory, build_target_arguments, parse_name_status
from .git_reader import GitReader, GitTimeoutExpired
from .read_authority import ReadAuthority, is_within_boundary
from .settings import DiscoverSettings


_FATAL_MESSAGES = {
    "GIT_CHANGE_OUTPUT_TRUNCATED": "Local Git change output exceeded the configured byte limit.",
    "GIT_CHANGE_READ_FAILED": "Local Git change evidence could not be read safely.",
    "GIT_EXECUTION_FAILED": "Local Git evidence could not be read safely.",
    "GIT_NOT_REPOSITORY": "No local Git repository metadata was found.",
    "GIT_REPOSITORY_OUTSIDE_BOUNDARY": "Git resolved a repository outside the configured project boundary.",
    "GIT_TARGET_INVALID": "The requested local Git target could not be resolved.",
    "GIT_TIMEOUT": "Local Git evidence exceeded the configured time limit.",
    "GIT_UNAVAILABLE": "The Git executable is unavailable.",
}


class GitChangeReader:
    """Read bounded local change targets through hardened Git templates."""

    def __init__(
        self,
        *,
        authority: ReadAuthority,
        settings: DiscoverSettings,
    ) -> None:
        self._authority = authority
        self._settings = settings
        self._git = GitReader(authority=authority, settings=settings)

    @property
    def authority(self) -> ReadAuthority:
        return self._authority

    @property
    def settings(self) -> DiscoverSettings:
        return self._settings

    def inspect_local_changes(self, project_path: str):
        return self._git.inspect_local_changes(project_path)

    def inspect_change_target(self, request: InspectChangeRequest) -> ChangeTargetInventory:
        if request.source == "working_tree":
            local = self._git.inspect_local_changes(request.path)
            return ChangeTargetInventory(
                project_path=local.project_path,
                repository_root=local.repository_root,
                source=request.source,
                changes=local.changes,
                diagnostics=local.diagnostics,
                truncated=local.truncated,
            )

        project = self._authority.resolve_project(request.path)
        root = Path(project.canonical_path)
        metadata_error = self._git._validate_metadata(root)
        if metadata_error is not None:
            return _unavailable(request, project.canonical_path, metadata_error)
        if self._git._executable is None:
            return _unavailable(request, project.canonical_path, "GIT_UNAVAILABLE")

        deadline = time.monotonic() + self._settings.limits.git_timeout_seconds
        try:
            root_result = self._git._run(root, ("rev-parse", "--show-toplevel"), deadline)
            if root_result.returncode != 0:
                return _unavailable(request, project.canonical_path, "GIT_NOT_REPOSITORY")
            if root_result.truncated:
                return _unavailable(
                    request,
                    project.canonical_path,
                    "GIT_CHANGE_OUTPUT_TRUNCATED",
                    truncated=True,
                )
            repository_root = Path(
                root_result.stdout.decode("utf-8", errors="replace").strip()
            ).resolve(strict=True)
            if not is_within_boundary(self._authority.boundary, repository_root):
                return _unavailable(
                    request,
                    project.canonical_path,
                    "GIT_REPOSITORY_OUTSIDE_BOUNDARY",
                )
            target_result = self._git._run(
                root,
                build_target_arguments(request),
                deadline,
            )
        except GitTimeoutExpired:
            return _unavailable(request, project.canonical_path, "GIT_TIMEOUT")
        except (OSError, ValueError):
            return _unavailable(request, project.canonical_path, "GIT_EXECUTION_FAILED")

        if target_result.returncode != 0:
            return _unavailable(
                request,
                project.canonical_path,
                "GIT_TARGET_INVALID",
                repository_root=repository_root,
            )

        records = parse_name_status(target_result.stdout)
        diagnostics: list[dict[str, str]] = []
        truncated = target_result.truncated
        if truncated:
            diagnostics.append(
                {
                    "code": "GIT_CHANGE_OUTPUT_TRUNCATED",
                    "message": _FATAL_MESSAGES["GIT_CHANGE_OUTPUT_TRUNCATED"],
                }
            )
        if len(records) > self._settings.limits.max_files:
            records = records[: self._settings.limits.max_files]
            diagnostics.append(
                {
                    "code": "CHANGE_ENTRY_LIMIT_REACHED",
                    "message": "Local Git changes exceeded the configured file limit.",
                }
            )
            truncated = True

        return ChangeTargetInventory(
            project_path=project.canonical_path,
            repository_root=str(repository_root),
            source=request.source,
            changes=records,
            commit_ref=request.commit_ref,
            base_ref=request.base_ref,
            head_ref=request.head_ref,
            diagnostics=tuple(diagnostics),
            truncated=truncated,
        )


def _unavailable(
    request: InspectChangeRequest,
    project_path: str,
    code: str,
    *,
    repository_root: Path | None = None,
    truncated: bool = False,
) -> ChangeTargetInventory:
    return ChangeTargetInventory(
        project_path=project_path,
        repository_root=str(repository_root) if repository_root is not None else None,
        source=request.source,
        commit_ref=request.commit_ref,
        base_ref=request.base_ref,
        head_ref=request.head_ref,
        diagnostics=(
            {
                "code": code,
                "message": _FATAL_MESSAGES.get(code, code),
            },
        ),
        truncated=truncated,
    )


__all__ = ["GitChangeReader"]
