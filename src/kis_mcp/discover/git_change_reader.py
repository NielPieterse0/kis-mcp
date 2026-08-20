from __future__ import annotations

import hashlib
import time
from dataclasses import replace
from pathlib import Path

from .change_inspection_contracts import InspectChangeRequest
from .change_snapshot import collect_mutable_source_snapshot
from .change_targets import ChangeTargetInventory, build_target_arguments, parse_name_status
from .git_reader import GitReader, GitTimeoutExpired
from .read_authority import ReadAuthority, is_within_boundary
from .settings import DiscoverSettings


_FATAL_MESSAGES = {
    "GIT_CHANGE_OUTPUT_TRUNCATED": "Local Git change output exceeded the configured byte limit.",
    "GIT_CHANGE_READ_FAILED": "Local Git change evidence could not be read safely.",
    "CHANGE_SOURCE_FINGERPRINT_UNAVAILABLE": "Local Git source identity could not be fingerprinted safely.",
    "CHANGE_SOURCE_CHANGED_DURING_INSPECTION": "Local Git source changed while bounded change evidence was being inspected.",
    "GIT_EXECUTION_FAILED": "Local Git evidence could not be read safely.",
    "GIT_NOT_REPOSITORY": "No local Git repository metadata was found.",
    "GIT_REPOSITORY_OUTSIDE_BOUNDARY": "Git resolved a repository outside the configured project boundary.",
    "GIT_TARGET_INVALID": "The requested local Git target could not be resolved.",
    "GIT_UNSUPPORTED_MERGE_COMMIT": "Merge commits with more than two parents are not supported for bounded change inspection.",
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
        first = self._git.inspect_local_changes(project_path)
        if first.repository_root is None:
            return first
        root = Path(first.repository_root)
        first_guard = self._working_tree_guard_fingerprint(root, first.changes)
        second = self._git.inspect_local_changes(project_path)
        if second.repository_root is None or second.repository_root != first.repository_root:
            return _with_local_diagnostic(second, "CHANGE_SOURCE_CHANGED_DURING_INSPECTION")
        second_guard = self._working_tree_guard_fingerprint(root, second.changes)
        if first_guard is None or second_guard is None:
            return _with_local_diagnostic(second, "CHANGE_SOURCE_FINGERPRINT_UNAVAILABLE")
        if first_guard != second_guard:
            return _with_local_diagnostic(second, "CHANGE_SOURCE_CHANGED_DURING_INSPECTION")
        source_fingerprint = self._mutable_snapshot_fingerprint(
            root,
            "working_tree",
            second.changes,
        )
        final_guard = self._working_tree_guard_fingerprint(root, second.changes)
        if source_fingerprint is None or final_guard is None:
            return _with_local_diagnostic(second, "CHANGE_SOURCE_FINGERPRINT_UNAVAILABLE")
        if final_guard != second_guard:
            return _with_local_diagnostic(second, "CHANGE_SOURCE_CHANGED_DURING_INSPECTION")
        return replace(second, source_fingerprint=source_fingerprint)

    def inspect_change_target(self, request: InspectChangeRequest) -> ChangeTargetInventory:
        if request.source == "working_tree":
            local = self.inspect_local_changes(request.path)
            return ChangeTargetInventory(
                project_path=local.project_path,
                repository_root=local.repository_root,
                source=request.source,
                changes=local.changes,
                diagnostics=local.diagnostics,
                truncated=local.truncated,
                source_fingerprint=local.source_fingerprint,
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
            resolved_request = self._resolve_request(root, request, deadline)
            if resolved_request is None:
                return _unavailable(
                    request,
                    project.canonical_path,
                    "GIT_TARGET_INVALID",
                    repository_root=repository_root,
                )
            before_fingerprint = (
                self._target_fingerprint(root, resolved_request, deadline)
                if request.source == "staged"
                else None
            )
            target_arguments = build_target_arguments(resolved_request)
            if request.source == "commit":
                assert resolved_request.commit_ref is not None
                identity = self._commit_identity(root, resolved_request.commit_ref, deadline)
                if identity is None:
                    return _unavailable(
                        request,
                        project.canonical_path,
                        "GIT_TARGET_INVALID",
                        repository_root=repository_root,
                    )
                commit_identity, parents = identity
                if len(parents) > 2:
                    return _unavailable(
                        request,
                        project.canonical_path,
                        "GIT_UNSUPPORTED_MERGE_COMMIT",
                        repository_root=repository_root,
                    )
                if len(parents) == 2:
                    target_arguments = (
                        "diff",
                        "--no-ext-diff",
                        "--no-textconv",
                        "--name-status",
                        "-z",
                        "--find-renames",
                        "--find-copies",
                        "--end-of-options",
                        parents[0],
                        commit_identity,
                        "--",
                    )
            target_result = self._git._run(root, target_arguments, deadline)
            source_fingerprint = self._target_fingerprint(
                root,
                resolved_request,
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
        if source_fingerprint is None or (
            request.source == "staged" and before_fingerprint is None
        ):
            return _unavailable(
                request,
                project.canonical_path,
                "CHANGE_SOURCE_FINGERPRINT_UNAVAILABLE",
                repository_root=repository_root,
            )
        if request.source == "staged" and before_fingerprint != source_fingerprint:
            return _unavailable(
                request,
                project.canonical_path,
                "CHANGE_SOURCE_CHANGED_DURING_INSPECTION",
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

        if request.source == "staged" and not truncated:
            snapshot_fingerprint = self._mutable_snapshot_fingerprint(
                root,
                "staged",
                records,
            )
            final_guard = self._target_fingerprint(root, resolved_request, deadline)
            if snapshot_fingerprint is None or final_guard is None:
                return _unavailable(
                    request,
                    project.canonical_path,
                    "CHANGE_SOURCE_FINGERPRINT_UNAVAILABLE",
                    repository_root=repository_root,
                )
            if final_guard != source_fingerprint:
                return _unavailable(
                    request,
                    project.canonical_path,
                    "CHANGE_SOURCE_CHANGED_DURING_INSPECTION",
                    repository_root=repository_root,
                )
            source_fingerprint = snapshot_fingerprint

        return ChangeTargetInventory(
            project_path=project.canonical_path,
            repository_root=str(repository_root),
            source=request.source,
            changes=records,
            commit_ref=request.commit_ref,
            base_ref=request.base_ref,
            head_ref=request.head_ref,
            resolved_commit_ref=resolved_request.commit_ref,
            resolved_base_ref=resolved_request.base_ref,
            resolved_head_ref=resolved_request.head_ref,
            diagnostics=tuple(diagnostics),
            truncated=truncated,
            source_fingerprint=source_fingerprint,
        )

    def _resolve_request(
        self,
        root: Path,
        request: InspectChangeRequest,
        deadline: float,
    ) -> InspectChangeRequest | None:
        if request.source == "staged":
            return request
        if request.source == "commit":
            assert request.commit_ref is not None
            commit = self._resolve_commit(root, request.commit_ref, deadline)
            if commit is None:
                return None
            return InspectChangeRequest(
                path=request.path,
                source=request.source,
                commit_ref=commit,
            )
        assert request.base_ref is not None and request.head_ref is not None
        base = self._resolve_commit(root, request.base_ref, deadline)
        head = self._resolve_commit(root, request.head_ref, deadline)
        if base is None or head is None:
            return None
        return InspectChangeRequest(
            path=request.path,
            source=request.source,
            base_ref=base,
            head_ref=head,
        )

    def _commit_identity(
        self,
        root: Path,
        commit_ref: str,
        deadline: float,
    ) -> tuple[str, tuple[str, ...]] | None:
        result = self._git._run(
            root,
            ("rev-list", "--parents", "-n", "1", commit_ref),
            deadline,
        )
        if result.returncode != 0 or result.truncated:
            return None
        parts = result.stdout.decode("ascii", errors="ignore").strip().casefold().split()
        if not parts:
            return None
        commit_identity = parts[0]
        parents = tuple(parts[1:])
        identities = (commit_identity, *parents)
        if any(
            len(identity) not in {40, 64}
            or any(char not in "0123456789abcdef" for char in identity)
            for identity in identities
        ):
            return None
        return commit_identity, parents

    def _resolve_commit(self, root: Path, ref: str, deadline: float) -> str | None:
        result = self._git._run(
            root,
            ("rev-parse", "--verify", f"{ref}^{{commit}}"),
            deadline,
        )
        if result.returncode != 0 or result.truncated:
            return None
        resolved = result.stdout.decode("ascii", errors="ignore").strip().casefold()
        if len(resolved) not in {40, 64} or any(char not in "0123456789abcdef" for char in resolved):
            return None
        return resolved

    def _target_fingerprint(
        self,
        root: Path,
        request: InspectChangeRequest,
        deadline: float,
    ) -> str | None:
        if request.source == "commit":
            assert request.commit_ref is not None
            return _fingerprint_parts((("source", b"commit"), ("commit", request.commit_ref.encode("ascii"))))
        if request.source in {"range", "branch"}:
            assert request.base_ref is not None and request.head_ref is not None
            return _fingerprint_parts(
                (
                    ("source", request.source.encode("ascii")),
                    ("base", request.base_ref.encode("ascii")),
                    ("head", request.head_ref.encode("ascii")),
                )
            )
        head = self._git._run(root, ("rev-parse", "HEAD"), deadline)
        staged = self._git._run(
            root,
            (
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--cached",
                "--raw",
                "--no-abbrev",
                "-z",
            ),
            deadline,
        )
        if any(result.returncode != 0 or result.truncated for result in (head, staged)):
            return None
        return _fingerprint_parts(
            (("source", b"staged"), ("head", head.stdout.strip()), ("index", staged.stdout))
        )

    def _working_tree_guard_fingerprint(self, root: Path, records) -> str | None:
        deadline = time.monotonic() + self._settings.limits.git_timeout_seconds
        try:
            head = self._git._run(root, ("rev-parse", "HEAD"), deadline)
            status = self._git._run(
                root,
                ("status", "--porcelain=v1", "-z", "--untracked-files=all"),
                deadline,
            )
            staged = self._git._run(
                root,
                (
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--cached",
                    "--raw",
                    "--no-abbrev",
                    "-z",
                ),
                deadline,
            )
            worktree = self._git._run(
                root,
                (
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--raw",
                    "--no-abbrev",
                    "-z",
                ),
                deadline,
            )
            if any(
                result.returncode != 0 or result.truncated
                for result in (head, status, staged, worktree)
            ):
                return None
            parts: list[tuple[str, bytes]] = [
                ("source", b"working_tree"),
                ("head", head.stdout.strip()),
                ("status", status.stdout),
                ("index", staged.stdout),
                ("worktree", worktree.stdout),
            ]
            for record in records:
                if not (record.untracked or record.worktree_status is not None):
                    continue
                label = f"file:{record.path}"
                if record.worktree_status == "deleted":
                    parts.append((label, b"<deleted>"))
                    continue
                hashed = self._git._run(
                    root,
                    ("hash-object", "--no-filters", "--", record.path),
                    deadline,
                )
                if hashed.returncode != 0 or hashed.truncated:
                    return None
                parts.append((label, hashed.stdout.strip()))
            return _fingerprint_parts(tuple(parts))
        except (GitTimeoutExpired, OSError, ValueError):
            return None

    def _mutable_snapshot_fingerprint(
        self,
        root: Path,
        source: str,
        records,
    ) -> str | None:
        deadline = time.monotonic() + self._settings.limits.git_timeout_seconds

        def run_git(arguments: tuple[str, ...]) -> bytes:
            result = self._git._run(root, arguments, deadline)
            if result.returncode != 0 or result.truncated:
                raise ValueError("mutable source snapshot command failed")
            return result.stdout

        try:
            snapshot = collect_mutable_source_snapshot(
                project=root,
                source=source,
                records=tuple(records),
                run_git=run_git,
            )
        except (GitTimeoutExpired, OSError, ValueError):
            return None
        return snapshot.fingerprint


def _with_local_diagnostic(inventory, code: str):
    return replace(
        inventory,
        source_fingerprint=None,
        diagnostics=(
            *inventory.diagnostics,
            {"code": code, "message": _FATAL_MESSAGES[code]},
        ),
    )


def _fingerprint_parts(parts: tuple[tuple[str, bytes], ...]) -> str:
    digest = hashlib.sha256()
    for label, value in parts:
        label_bytes = label.encode("utf-8")
        digest.update(len(label_bytes).to_bytes(4, "big"))
        digest.update(label_bytes)
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


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
