from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from kis_mcp.discover.read_authority import ReadAuthority


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=check,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )


def _init_repository(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Discover Tests")
    _git(root, "config", "user.email", "discover@example.invalid")


def _commit(root: Path, label: str, content: str, subject: str) -> None:
    path = root / label
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(root, "add", "--", label)
    _git(root, "commit", "-m", subject)


def _reader(settings):
    from kis_mcp.discover.git_reader import GitReader

    return GitReader(
        authority=ReadAuthority(Path(r"C:\Projects"), settings),
        settings=settings,
    )


def test_reads_branch_status_tracked_files_history_and_redacted_remote(
    project_root: Path,
    discover_settings,
) -> None:
    _init_repository(project_root)
    _commit(project_root, "alpha.txt", "alpha\n", "first commit")
    _commit(project_root, "beta.txt", "beta\n", "second commit")
    _git(
        project_root,
        "remote",
        "add",
        "origin",
        "https://user:secret@github.com/example/repository.git?token=hidden#fragment",
    )
    (project_root / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.available is True
    assert summary.repository is True
    assert summary.branch == "main"
    assert summary.detached is False
    assert len(summary.head or "") == 40
    assert summary.status == "dirty"
    assert summary.tracked_files == 2
    assert summary.remote == "https://github.com/example/repository.git"
    assert [item["subject"] for item in summary.recent_commits] == [
        "second commit",
        "first commit",
    ]
    assert summary.truncated is False
    assert summary.diagnostics == ()


def test_redacts_query_and_fragment_from_scp_style_remote(
    project_root: Path,
    discover_settings,
) -> None:
    _init_repository(project_root)
    _commit(project_root, "tracked.txt", "tracked\n", "initial")
    _git(
        project_root,
        "remote",
        "add",
        "origin",
        "git@github.com:example/repository.git?token=hidden#fragment",
    )

    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.remote == "github.com:example/repository.git"
    assert "hidden" not in (summary.remote or "")


def test_reads_detached_head_and_linked_worktree(
    project_root: Path,
    discover_settings,
) -> None:
    _init_repository(project_root)
    _commit(project_root, "tracked.txt", "tracked\n", "initial")
    linked = project_root.parent / f"{project_root.name}-linked"
    _git(project_root, "worktree", "add", "-b", "linked", str(linked))

    linked_summary = _reader(discover_settings).inspect(str(linked))

    assert (linked / ".git").is_file()
    assert linked_summary.available is True
    assert linked_summary.branch == "linked"
    assert linked_summary.detached is False
    assert linked_summary.tracked_files == 1

    _git(project_root, "checkout", "--detach")
    detached = _reader(discover_settings).inspect(str(project_root))

    assert detached.available is True
    assert detached.branch is None
    assert detached.detached is True
    assert detached.head is not None


def test_non_git_directory_is_explicitly_unavailable(
    project_root: Path,
    discover_settings,
) -> None:
    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.available is False
    assert summary.repository is False
    assert summary.status == "unavailable"
    assert [item["code"] for item in summary.diagnostics] == ["GIT_NOT_REPOSITORY"]
    assert summary.tracked_files == 0


@pytest.mark.parametrize(
    ("metadata", "code"),
    [
        (b"not-a-gitdir-record\n", "GIT_METADATA_INVALID"),
        (b"gitdir: missing-target\n", "GIT_METADATA_TARGET_MISSING"),
        (b"gitdir: C:\\Windows\\Temp\\outside\n", "GIT_METADATA_OUTSIDE_BOUNDARY"),
        (b"\xff\xfe\xfd", "GIT_METADATA_ENCODING_INVALID"),
    ],
)
def test_invalid_git_metadata_is_rejected(
    project_root: Path,
    discover_settings,
    metadata: bytes,
    code: str,
) -> None:
    (project_root / ".git").write_bytes(metadata)

    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.available is False
    assert summary.repository is False
    assert [item["code"] for item in summary.diagnostics] == [code]


def test_oversized_and_non_directory_git_metadata_targets_are_rejected(
    project_root: Path,
    discover_settings,
) -> None:
    from dataclasses import replace

    target = project_root / "git-target"
    target.write_text("not a directory\n", encoding="utf-8")
    (project_root / ".git").write_text("gitdir: git-target\n", encoding="utf-8")

    not_directory = _reader(discover_settings).inspect(str(project_root))

    assert [item["code"] for item in not_directory.diagnostics] == [
        "GIT_METADATA_TARGET_NOT_DIRECTORY"
    ]

    settings = replace(
        discover_settings,
        limits=replace(discover_settings.limits, git_metadata_max_bytes=8),
    )
    (project_root / ".git").write_text("gitdir: some-target\n", encoding="utf-8")

    oversized = _reader(settings).inspect(str(project_root))

    assert [item["code"] for item in oversized.diagnostics] == [
        "GIT_METADATA_TOO_LARGE"
    ]
