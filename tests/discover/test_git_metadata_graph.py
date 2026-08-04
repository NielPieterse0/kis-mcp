from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

from kis_mcp.discover.read_authority import ReadAuthority


def _reader(settings):
    from kis_mcp.discover.git_reader import GitReader

    return GitReader(
        authority=ReadAuthority(Path(r"C:\Projects"), settings),
        settings=settings,
    )


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"},
    )


def _init(root: Path, *, commit: bool = False) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Discover Tests")
    _git(root, "config", "user.email", "discover@example.invalid")
    if commit:
        (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        _git(root, "add", "tracked.txt")
        _git(root, "commit", "-m", "initial")


def _assert_rejected_before_git(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
    expected_code: str,
) -> None:
    def should_not_run(*args, **kwargs):
        raise AssertionError("Git subprocess must not run after metadata rejection")

    monkeypatch.setattr("kis_mcp.discover.git_reader._run_bounded", should_not_run)
    summary = _reader(discover_settings).inspect(str(project_root))
    assert summary.available is False
    assert [item["code"] for item in summary.diagnostics] == [expected_code]


def test_rejects_common_directory_outside_discover_boundary(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    git_dir = project_root / ".git"
    git_dir.mkdir()
    (git_dir / "commondir").write_text(
        r"C:\Windows\Temp\common" + "\n",
        encoding="utf-8",
    )

    _assert_rejected_before_git(
        project_root,
        discover_settings,
        monkeypatch,
        "GIT_METADATA_OUTSIDE_BOUNDARY",
    )


def test_rejects_active_alternate_object_database_outside_boundary(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _init(project_root, commit=True)
    alternates = project_root / ".git" / "objects" / "info"
    alternates.mkdir(parents=True, exist_ok=True)
    (alternates / "alternates").write_text(
        r"C:\Windows\Temp\objects" + "\n",
        encoding="utf-8",
    )

    _assert_rejected_before_git(
        project_root,
        discover_settings,
        monkeypatch,
        "GIT_METADATA_OUTSIDE_BOUNDARY",
    )


def test_unborn_repository_does_not_follow_passive_alternate_record(
    project_root: Path,
    discover_settings,
) -> None:
    _init(project_root)
    alternates = project_root / ".git" / "objects" / "info"
    alternates.mkdir(parents=True, exist_ok=True)
    (alternates / "alternates").write_text(
        r"C:\Windows\Temp\objects" + "\n",
        encoding="utf-8",
    )

    summary = _reader(discover_settings).inspect(str(project_root))

    assert "GIT_METADATA_OUTSIDE_BOUNDARY" not in {
        item["code"] for item in summary.diagnostics
    }


def test_rejects_active_local_git_config_include_outside_boundary(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    git_dir = project_root / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        '[include]\n    path = C:\\Windows\\Temp\\outside.gitconfig\n',
        encoding="utf-8",
    )

    _assert_rejected_before_git(
        project_root,
        discover_settings,
        monkeypatch,
        "GIT_METADATA_OUTSIDE_BOUNDARY",
    )


def test_inactive_conditional_include_outside_boundary_is_ignored(
    project_root: Path,
    discover_settings,
) -> None:
    _init(project_root, commit=True)
    _git(
        project_root,
        "config",
        "--add",
        'includeIf.onbranch:never-matches.path',
        r"C:\Windows\Temp\outside.gitconfig",
    )

    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.available is True
    assert "GIT_METADATA_OUTSIDE_BOUNDARY" not in {
        item["code"] for item in summary.diagnostics
    }


def test_disabled_worktree_config_is_not_loaded(
    project_root: Path,
    discover_settings,
) -> None:
    _init(project_root, commit=True)
    (project_root / ".git" / "config.worktree").write_text(
        '[include]\n    path = C:\\Windows\\Temp\\outside.gitconfig\n',
        encoding="utf-8",
    )

    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.available is True
    assert "GIT_METADATA_OUTSIDE_BOUNDARY" not in {
        item["code"] for item in summary.diagnostics
    }


def test_harmless_remote_url_is_not_treated_as_metadata_path(
    project_root: Path,
    discover_settings,
) -> None:
    _init(project_root, commit=True)
    _git(
        project_root,
        "remote",
        "add",
        "origin",
        "https://example.com/example/repository.git",
    )

    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.available is True
    assert summary.remote == "https://example.com/example/repository.git"


def test_rejects_nested_link_or_reparse_component_in_active_metadata(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    git_dir = project_root / ".git"
    objects = git_dir / "objects"
    objects.mkdir(parents=True)
    original_lstat = __import__("kis_mcp.discover.git_reader", fromlist=["os"]).os.lstat

    def fake_lstat(path):
        info = original_lstat(path)
        if Path(path) == objects:
            class ReparseStat:
                st_mode = info.st_mode
                st_file_attributes = 0x400
                st_dev = info.st_dev
                st_ino = info.st_ino
                st_size = info.st_size

            return ReparseStat()
        return info

    monkeypatch.setattr("kis_mcp.discover.git_reader.os.lstat", fake_lstat)

    _assert_rejected_before_git(
        project_root,
        discover_settings,
        monkeypatch,
        "GIT_METADATA_UNSAFE",
    )


def test_git_repository_override_environment_is_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    from kis_mcp.discover.git_reader import _isolated_environment

    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
    ):
        monkeypatch.setenv(key, r"C:\Windows\Temp\escape")

    environment = _isolated_environment()

    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
    ):
        assert key not in environment
