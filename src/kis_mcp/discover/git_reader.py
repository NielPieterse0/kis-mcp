from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit, urlunsplit

from .change_contracts import ChangePathRecord, ChangeSummary, LocalChangeInventory
from .contracts import GitSummary
from .git_metadata import GitMetadataValidationError, validate_git_metadata_graph
from .read_authority import ReadAuthority, is_within_boundary
from .settings import DiscoverSettings

_SAFE_SCHEMES = {"git", "http", "https", "ssh"}


@dataclass(frozen=True, slots=True)
class _GitCommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    truncated: bool
    nul_items: int


@dataclass(slots=True)
class _MutableChange:
    path: str
    previous_path: str | None = None
    staged_status: str | None = None
    worktree_status: str | None = None
    untracked: bool = False

    def freeze(self) -> ChangePathRecord:
        return ChangePathRecord(
            path=self.path,
            previous_path=self.previous_path,
            staged_status=self.staged_status,
            worktree_status=self.worktree_status,
            untracked=self.untracked,
        )


class GitReader:
    def __init__(
        self,
        *,
        authority: ReadAuthority,
        settings: DiscoverSettings,
    ) -> None:
        self._authority = authority
        self._settings = settings
        self._executable = shutil.which("git")

    def inspect(self, project_path: str) -> GitSummary:
        project = self._authority.resolve_project(project_path)
        root = Path(project.canonical_path)
        metadata_error = self._validate_metadata(root)
        if metadata_error is not None:
            return _unavailable(metadata_error)
        if self._executable is None:
            return _unavailable("GIT_UNAVAILABLE")

        deadline = time.monotonic() + self._settings.limits.git_timeout_seconds
        diagnostics: list[dict[str, str]] = []
        results: list[_GitCommandResult] = []
        try:
            root_result = self._run(root, ("rev-parse", "--show-toplevel"), deadline)
            results.append(root_result)
            if root_result.returncode != 0:
                return _unavailable("GIT_NOT_REPOSITORY")
            repository_root = Path(_decode(root_result.stdout).strip()).resolve(strict=True)
            if not is_within_boundary(self._authority.boundary, repository_root):
                return _unavailable("GIT_REPOSITORY_OUTSIDE_BOUNDARY")

            branch_result = self._run(
                root,
                ("symbolic-ref", "--short", "-q", "HEAD"),
                deadline,
            )
            head_result = self._run(root, ("rev-parse", "HEAD"), deadline)
            status_result = self._run(
                root,
                ("status", "--porcelain=v1", "-z", "--branch", "--untracked-files=normal"),
                deadline,
            )
            tracked_result = self._run(root, ("ls-files", "-z"), deadline)
            remote_result = self._run(root, ("remote", "-v"), deadline)
            log_result = self._run(
                root,
                (
                    "log",
                    f"-n{self._settings.limits.git_history_limit}",
                    "--format=%H%x09%aI%x09%s",
                ),
                deadline,
            )
            results.extend(
                (
                    branch_result,
                    head_result,
                    status_result,
                    tracked_result,
                    remote_result,
                    log_result,
                )
            )
        except subprocess.TimeoutExpired:
            return _unavailable("GIT_TIMEOUT")
        except (OSError, ValueError):
            return _unavailable("GIT_EXECUTION_FAILED")

        branch = _decode(branch_result.stdout).strip() or None
        head = _decode(head_result.stdout).strip() or None
        status_entries = _parse_status(status_result.stdout)
        dirty = any(not entry.startswith("##") for entry in status_entries)
        remote = _preferred_remote(_decode(remote_result.stdout))
        recent_commits = _parse_log(_decode(log_result.stdout))
        if any(result.truncated for result in results):
            diagnostics.append(
                {
                    "code": "GIT_OUTPUT_TRUNCATED",
                    "message": "One or more Git command outputs exceeded the configured byte limit.",
                }
            )
        return GitSummary(
            available=True,
            repository=True,
            branch=branch,
            detached=branch is None,
            head=head,
            status="dirty" if dirty else "clean",
            tracked_files=tracked_result.nul_items,
            remote=remote,
            recent_commits=recent_commits,
            diagnostics=tuple(diagnostics),
            truncated=bool(diagnostics),
        )

    def inspect_local_changes(self, project_path: str) -> LocalChangeInventory:
        project = self._authority.resolve_project(project_path)
        root = Path(project.canonical_path)
        metadata_error = self._validate_metadata(root)
        if metadata_error is not None:
            return _change_unavailable(project.canonical_path, metadata_error)
        if self._executable is None:
            return _change_unavailable(project.canonical_path, "GIT_UNAVAILABLE")

        deadline = time.monotonic() + self._settings.limits.git_timeout_seconds
        try:
            root_result = self._run(root, ("rev-parse", "--show-toplevel"), deadline)
            if root_result.returncode != 0:
                return _change_unavailable(project.canonical_path, "GIT_NOT_REPOSITORY")
            if root_result.truncated:
                return _change_unavailable(
                    project.canonical_path,
                    "GIT_CHANGE_OUTPUT_TRUNCATED",
                    truncated=True,
                )
            repository_root = Path(_decode(root_result.stdout).strip()).resolve(strict=True)
            if not is_within_boundary(self._authority.boundary, repository_root):
                return _change_unavailable(
                    project.canonical_path,
                    "GIT_REPOSITORY_OUTSIDE_BOUNDARY",
                )

            staged_result = self._run(
                root,
                (
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--cached",
                    "--name-status",
                    "-z",
                    "--find-renames",
                    "--find-copies",
                ),
                deadline,
            )
            worktree_result = self._run(
                root,
                (
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--name-status",
                    "-z",
                    "--find-renames",
                    "--find-copies",
                ),
                deadline,
            )
            untracked_result = self._run(
                root,
                ("ls-files", "--others", "--exclude-standard", "-z"),
                deadline,
            )
        except subprocess.TimeoutExpired:
            return _change_unavailable(project.canonical_path, "GIT_TIMEOUT")
        except (OSError, ValueError):
            return _change_unavailable(project.canonical_path, "GIT_EXECUTION_FAILED")

        if any(
            result.returncode != 0
            for result in (staged_result, worktree_result, untracked_result)
        ):
            return _change_unavailable(
                project.canonical_path,
                "GIT_CHANGE_READ_FAILED",
                repository_root=repository_root,
            )

        changes: dict[str, _MutableChange] = {}
        for status, path, previous_path in _parse_name_status(staged_result.stdout):
            change = changes.setdefault(path, _MutableChange(path=path))
            change.staged_status = status
            if previous_path is not None and change.previous_path is None:
                change.previous_path = previous_path
        for status, path, previous_path in _parse_name_status(worktree_result.stdout):
            change = changes.setdefault(path, _MutableChange(path=path))
            change.worktree_status = status
            if previous_path is not None and change.previous_path is None:
                change.previous_path = previous_path
        for path in _parse_nul_paths(untracked_result.stdout):
            change = changes.setdefault(path, _MutableChange(path=path))
            change.untracked = True

        ordered_paths = sorted(changes, key=lambda value: (value.casefold(), value))
        diagnostics: list[dict[str, str]] = []
        truncated = any(
            result.truncated
            for result in (staged_result, worktree_result, untracked_result)
        )
        if truncated:
            diagnostics.append(
                {
                    "code": "GIT_CHANGE_OUTPUT_TRUNCATED",
                    "message": "Local Git change output exceeded the configured byte limit.",
                }
            )
        if len(ordered_paths) > self._settings.limits.max_files:
            ordered_paths = ordered_paths[: self._settings.limits.max_files]
            diagnostics.append(
                {
                    "code": "CHANGE_ENTRY_LIMIT_REACHED",
                    "message": "Local Git changes exceeded the configured file limit.",
                }
            )
            truncated = True

        records = tuple(changes[path].freeze() for path in ordered_paths)
        return LocalChangeInventory(
            project_path=project.canonical_path,
            repository_root=str(repository_root),
            changes=records,
            summary=_summarize_changes(records),
            diagnostics=tuple(diagnostics),
            truncated=truncated,
        )

    def _validate_metadata(self, root: Path) -> str | None:
        try:
            validate_git_metadata_graph(
                root,
                boundary=self._authority.boundary,
                maximum_file_bytes=self._settings.limits.git_metadata_max_bytes,
            )
        except GitMetadataValidationError as exc:
            return exc.code
        return None

    def _run(
        self,
        root: Path,
        arguments: tuple[str, ...],
        deadline: float,
    ) -> _GitCommandResult:
        executable = self._executable
        if executable is None:
            raise OSError("Git executable is unavailable")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(cmd="git", timeout=0)
        environment = _isolated_environment()
        command = [
            executable,
            "--no-pager",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "core.attributesFile=",
            "-c",
            "core.excludesFile=",
            "-c",
            "core.pager=cat",
            "-c",
            "pager.status=false",
            "-c",
            "diff.external=",
            "-c",
            "diff.trustExitCode=false",
            "-c",
            "credential.helper=",
            "-C",
            str(root),
            *arguments,
        ]
        return _run_bounded(
            command,
            cwd=root,
            environment=environment,
            timeout_seconds=max(0.001, remaining),
            max_output_bytes=self._settings.limits.git_max_output_bytes,
        )


def _parse_name_status(
    output: bytes,
) -> tuple[tuple[str, str, str | None], ...]:
    fields = _complete_nul_fields(output)
    parsed: list[tuple[str, str, str | None]] = []
    index = 0
    while index < len(fields):
        raw_status = fields[index]
        index += 1
        status = _normalize_change_status(raw_status)
        if raw_status[:1].upper() in {"C", "R"}:
            if index + 1 >= len(fields):
                break
            previous_path = fields[index]
            path = fields[index + 1]
            index += 2
        else:
            if index >= len(fields):
                break
            previous_path = None
            path = fields[index]
            index += 1
        if path:
            parsed.append((status, path, previous_path))
    return tuple(parsed)


def _parse_nul_paths(output: bytes) -> tuple[str, ...]:
    return tuple(path for path in _complete_nul_fields(output) if path)


def _complete_nul_fields(output: bytes) -> tuple[str, ...]:
    if not output:
        return ()
    fields = output.split(b"\x00")
    fields.pop()
    return tuple(_decode(field) for field in fields)


def _normalize_change_status(raw_status: str) -> str:
    return {
        "A": "added",
        "C": "copied",
        "D": "deleted",
        "M": "modified",
        "R": "renamed",
        "T": "type_changed",
        "U": "unmerged",
    }.get(raw_status[:1].upper(), "unknown")


def _summarize_changes(records: tuple[ChangePathRecord, ...]) -> ChangeSummary:
    return ChangeSummary(
        total=len(records),
        staged=sum(record.staged_status is not None for record in records),
        unstaged=sum(record.worktree_status is not None for record in records),
        untracked=sum(record.untracked for record in records),
        renamed=sum("renamed" in (record.staged_status, record.worktree_status) for record in records),
        copied=sum("copied" in (record.staged_status, record.worktree_status) for record in records),
        deleted=sum("deleted" in (record.staged_status, record.worktree_status) for record in records),
        conflicted=sum("unmerged" in (record.staged_status, record.worktree_status) for record in records),
    )


def _change_unavailable(
    project_path: str,
    code: str,
    *,
    repository_root: Path | None = None,
    truncated: bool = False,
) -> LocalChangeInventory:
    messages = {
        "GIT_CHANGE_OUTPUT_TRUNCATED": "Local Git change output exceeded the configured byte limit.",
        "GIT_CHANGE_READ_FAILED": "Local Git change evidence could not be read safely.",
        "GIT_EXECUTION_FAILED": "Local Git evidence could not be read safely.",
        "GIT_METADATA_ENCODING_INVALID": "Linked-worktree metadata is not valid UTF-8.",
        "GIT_METADATA_INVALID": "The .git metadata shape is invalid.",
        "GIT_METADATA_OUTSIDE_BOUNDARY": "Linked-worktree metadata points outside the configured project boundary.",
        "GIT_METADATA_TARGET_MISSING": "Linked-worktree metadata target does not exist.",
        "GIT_METADATA_TARGET_NOT_DIRECTORY": "Linked-worktree metadata target is not a directory.",
        "GIT_METADATA_TOO_LARGE": "Linked-worktree metadata exceeds the configured byte limit.",
        "GIT_METADATA_UNSAFE": "Git metadata is linked, replaced, or otherwise unsafe.",
        "GIT_NOT_REPOSITORY": "No local Git repository metadata was found.",
        "GIT_REPOSITORY_OUTSIDE_BOUNDARY": "Git resolved a repository outside the configured project boundary.",
        "GIT_TIMEOUT": "Local Git evidence exceeded the configured time limit.",
        "GIT_UNAVAILABLE": "The Git executable is unavailable.",
    }
    return LocalChangeInventory(
        project_path=project_path,
        repository_root=str(repository_root) if repository_root is not None else None,
        diagnostics=({"code": code, "message": messages.get(code, code)},),
        truncated=truncated,
    )


def _run_bounded(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout_seconds: float,
    max_output_bytes: int,
) -> _GitCommandResult:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise OSError("Git output streams were unavailable")

    stdout = bytearray()
    stderr = bytearray()
    state = {"truncated": False, "nul_items": 0}

    def drain(stream: BinaryIO, target: bytearray, *, count_nuls: bool) -> None:
        while True:
            chunk = stream.read(65_536)
            if not chunk:
                break
            if count_nuls:
                state["nul_items"] += chunk.count(b"\x00")
            remaining = max_output_bytes - len(target)
            if remaining > 0:
                target.extend(chunk[:remaining])
            if len(chunk) > remaining:
                state["truncated"] = True

    stdout_thread = threading.Thread(
        target=drain,
        args=(process.stdout, stdout),
        kwargs={"count_nuls": True},
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=drain,
        args=(process.stderr, stderr),
        kwargs={"count_nuls": False},
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        stdout_thread.join()
        stderr_thread.join()
        raise
    stdout_thread.join()
    stderr_thread.join()
    return _GitCommandResult(
        returncode=returncode,
        stdout=bytes(stdout),
        stderr=bytes(stderr),
        truncated=bool(state["truncated"]),
        nul_items=int(state["nul_items"]),
    )


def _isolated_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_NAMESPACE",
        "GIT_CEILING_DIRECTORIES",
    ):
        environment.pop(key, None)
    environment.update(
        {
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_PAGER": "cat",
            "PAGER": "cat",
            "GCM_INTERACTIVE": "Never",
            "GIT_ASKPASS": "",
            "SSH_ASKPASS": "",
            "GIT_EDITOR": "true",
            "GIT_SEQUENCE_EDITOR": "true",
        }
    )
    return environment


def _decode(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _parse_status(output: bytes) -> tuple[str, ...]:
    text = _decode(output)
    if "\x00" in text:
        return tuple(item for item in text.split("\x00") if item)
    return tuple(line for line in text.splitlines() if line)


def _parse_log(output: str) -> tuple[dict[str, str], ...]:
    commits: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            commits.append(
                {"sha": parts[0], "authored_at": parts[1], "subject": parts[2]}
            )
    return tuple(commits)


def _preferred_remote(output: str) -> str | None:
    entries: list[tuple[str, str, str]] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        name, raw_url, role = parts[0], parts[1], parts[2].strip("()")
        entries.append((name, role, _redact_url(raw_url)))
    entries.sort(key=lambda item: (item[0] != "origin", item[0], item[1] != "fetch", item[1]))
    return entries[0][2] if entries else None


def _redact_url(value: str) -> str:
    if "://" in value:
        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname or ""
            port_value = parsed.port
        except ValueError:
            return "remote:<malformed>"
        if not hostname:
            return f"local:{_safe_repo_leaf(parsed.path)}"
        scheme = (
            parsed.scheme.casefold()
            if parsed.scheme.casefold() in _SAFE_SCHEMES
            else "remote"
        )
        port = f":{port_value}" if port_value else ""
        return urlunsplit((scheme, f"{hostname}{port}", parsed.path, "", ""))
    scp = re.match(r"(?:[^@\s]+@)?([^:\s]+):(.+)$", value)
    if scp and not re.match(r"^[A-Za-z]:[\\/]", value):
        path = re.split(r"[?#]", scp.group(2), maxsplit=1)[0]
        return f"{scp.group(1)}:{path}"
    return f"local:{_safe_repo_leaf(value)}"


def _safe_repo_leaf(value: str) -> str:
    cleaned = value.replace("\\", "/").rstrip("/")
    leaf = cleaned.rsplit("/", 1)[-1] or "repository"
    return leaf[:-4] if leaf.casefold().endswith(".git") else leaf


def _unavailable(code: str) -> GitSummary:
    messages = {
        "GIT_EXECUTION_FAILED": "Local Git evidence could not be read safely.",
        "GIT_METADATA_ENCODING_INVALID": "Linked-worktree metadata is not valid UTF-8.",
        "GIT_METADATA_INVALID": "The .git metadata shape is invalid.",
        "GIT_METADATA_OUTSIDE_BOUNDARY": "Linked-worktree metadata points outside the configured project boundary.",
        "GIT_METADATA_TARGET_MISSING": "Linked-worktree metadata target does not exist.",
        "GIT_METADATA_TARGET_NOT_DIRECTORY": "Linked-worktree metadata target is not a directory.",
        "GIT_METADATA_TOO_LARGE": "Linked-worktree metadata exceeds the configured byte limit.",
        "GIT_METADATA_UNSAFE": "Git metadata is linked, replaced, or otherwise unsafe.",
        "GIT_NOT_REPOSITORY": "No local Git repository metadata was found.",
        "GIT_REPOSITORY_OUTSIDE_BOUNDARY": "Git resolved a repository outside the configured project boundary.",
        "GIT_TIMEOUT": "Local Git evidence exceeded the configured time limit.",
        "GIT_UNAVAILABLE": "The Git executable is unavailable.",
    }
    return GitSummary(
        available=False,
        repository=False,
        branch=None,
        detached=False,
        head=None,
        status="unavailable",
        tracked_files=0,
        remote=None,
        diagnostics=({"code": code, "message": messages.get(code, code)},),
        truncated=False,
    )


__all__ = ["GitReader"]
