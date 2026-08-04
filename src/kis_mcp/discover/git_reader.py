from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit, urlunsplit

from .contracts import GitSummary
from .read_authority import ReadAuthority, is_within_boundary
from .settings import DiscoverSettings

_SAFE_SCHEMES = {"git", "http", "https", "ssh"}
_REPARSE_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


@dataclass(frozen=True, slots=True)
class _GitCommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    truncated: bool
    nul_items: int


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

    def _validate_metadata(self, root: Path) -> str | None:
        metadata = root / ".git"
        try:
            info = os.lstat(metadata)
        except FileNotFoundError:
            return "GIT_NOT_REPOSITORY"
        if _is_link_or_reparse(info):
            return "GIT_METADATA_UNSAFE"
        if stat.S_ISDIR(info.st_mode):
            return None
        if not stat.S_ISREG(info.st_mode):
            return "GIT_METADATA_INVALID"
        if info.st_size > self._settings.limits.git_metadata_max_bytes:
            return "GIT_METADATA_TOO_LARGE"
        try:
            data = _read_regular_file(
                metadata,
                expected=info,
                maximum=self._settings.limits.git_metadata_max_bytes,
            )
        except OSError:
            return "GIT_METADATA_UNSAFE"
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return "GIT_METADATA_ENCODING_INVALID"
        match = re.fullmatch(r"gitdir:\s*(.+?)\s*\r?\n?", text)
        if match is None:
            return "GIT_METADATA_INVALID"
        raw_target = match.group(1)
        candidate = Path(raw_target)
        target = candidate if candidate.is_absolute() else root / candidate
        target = target.resolve(strict=False)
        if not is_within_boundary(self._authority.boundary, target):
            return "GIT_METADATA_OUTSIDE_BOUNDARY"
        try:
            target_info = os.lstat(target)
        except FileNotFoundError:
            return "GIT_METADATA_TARGET_MISSING"
        if _is_link_or_reparse(target_info):
            return "GIT_METADATA_UNSAFE"
        if not stat.S_ISDIR(target_info.st_mode):
            return "GIT_METADATA_TARGET_NOT_DIRECTORY"
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


def _read_regular_file(path: Path, *, expected: os.stat_result, maximum: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if _identity(expected) != _identity(opened) or not stat.S_ISREG(opened.st_mode):
            raise OSError("Git metadata changed during validation")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if _identity(opened) != _identity(after) or opened.st_size != after.st_size:
            raise OSError("Git metadata changed while reading")
    finally:
        os.close(descriptor)
    if len(data) > maximum:
        raise OSError("Git metadata exceeded its configured limit")
    return data


def _identity(info: os.stat_result) -> tuple[int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode)


def _is_link_or_reparse(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & _REPARSE_FLAG
    )


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
