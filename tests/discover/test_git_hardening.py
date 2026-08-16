from __future__ import annotations

import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from kis_mcp.discover.read_authority import ReadAuthority


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"},
    )


def _init(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Discover Tests")
    _git(root, "config", "user.email", "discover@example.invalid")
    (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "initial")


def _reader(settings):
    from kis_mcp.discover.git_reader import GitReader

    return GitReader(
        authority=ReadAuthority(Path(r"C:\Projects"), settings),
        settings=settings,
    )


def test_git_metadata_read_tolerates_short_reads(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kis_mcp.discover import git_reader

    target = project_root / "git-target"
    target.mkdir()
    (project_root / ".git").write_text("gitdir: git-target\n", encoding="utf-8")
    original_read = git_reader.os.read

    def short_read(descriptor: int, count: int) -> bytes:
        return original_read(descriptor, min(count, 1))

    monkeypatch.setattr(git_reader.os, "read", short_read)
    monkeypatch.setattr(
        git_reader.GitReader,
        "_run",
        lambda *args, **kwargs: git_reader._GitCommandResult(1, b"", b"", False, 0),
    )

    summary = _reader(discover_settings).inspect(str(project_root))

    assert [item["code"] for item in summary.diagnostics] == ["GIT_NOT_REPOSITORY"]


def test_hostile_local_git_configuration_is_not_executed(
    project_root: Path,
    discover_settings,
) -> None:
    _init(project_root)
    marker = project_root / "configuration-executed.txt"
    fsmonitor = project_root / "fsmonitor.cmd"
    fsmonitor.write_text(f"@echo off\r\necho bad>\"{marker}\"\r\n", encoding="utf-8")
    _git(project_root, "config", "core.fsmonitor", str(fsmonitor))
    _git(project_root, "config", "core.pager", str(fsmonitor))
    _git(project_root, "config", "diff.external", str(fsmonitor))
    _git(project_root, "config", "credential.helper", f"!\"{fsmonitor}\"")

    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.available is True
    assert marker.exists() is False


def test_git_output_is_bounded_and_truncation_is_explicit(
    project_root: Path,
    discover_settings,
) -> None:
    _init(project_root)
    for index in range(100):
        (project_root / f"untracked-{index:03}.txt").write_text("x\n", encoding="utf-8")
    settings = replace(
        discover_settings,
        limits=replace(discover_settings.limits, git_max_output_bytes=512),
    )

    summary = _reader(settings).inspect(str(project_root))

    assert summary.available is True
    assert summary.status == "dirty"
    assert summary.truncated is True
    assert "GIT_OUTPUT_TRUNCATED" in {item["code"] for item in summary.diagnostics}


def test_git_timeout_returns_structural_unavailable_result(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _init(project_root)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr("kis_mcp.discover.git_reader._run_bounded", timeout)

    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.available is False
    assert [item["code"] for item in summary.diagnostics] == ["GIT_TIMEOUT"]


def test_git_uses_only_fixed_read_only_commands_and_isolated_environment(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kis_mcp.discover import git_reader

    (project_root / ".git").mkdir()
    calls: list[tuple[tuple[str, ...], dict[str, str]]] = []
    configured_system = r"C:\Projects\system.gitconfig"
    configured_global = r"C:\Projects\global.gitconfig"
    monkeypatch.delenv("GIT_CONFIG_NOSYSTEM", raising=False)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", configured_system)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", configured_global)

    def fake_run(command, *, cwd, environment, timeout_seconds, max_output_bytes):
        calls.append((tuple(command), dict(environment)))
        joined = " ".join(command)
        if "--show-toplevel" in command:
            stdout = str(project_root).encode()
        elif "symbolic-ref" in command:
            stdout = b"main\n"
        elif "rev-parse HEAD" in joined:
            stdout = b"0" * 40 + b"\n"
        elif "status" in command:
            stdout = b"## main\x00"
        elif "ls-files" in command:
            return git_reader._GitCommandResult(0, b"a.txt\x00", b"", False, 1)
        elif "remote" in command:
            stdout = b""
        elif "log" in command:
            stdout = b""
        else:
            stdout = b""
        return git_reader._GitCommandResult(0, stdout, b"", False, 0)

    monkeypatch.setattr(git_reader, "_run_bounded", fake_run)

    summary = _reader(discover_settings).inspect(str(project_root))

    assert summary.available is True
    assert calls
    forbidden = {"add", "branch", "checkout", "clone", "commit", "fetch", "merge", "pull", "push", "reset", "restore", "switch", "tag"}
    config_calls = 0
    for command, environment in calls:
        assert not forbidden.intersection(command)
        assert "--no-pager" in command
        assert environment["GIT_OPTIONAL_LOCKS"] == "0"
        assert environment["GIT_TERMINAL_PROMPT"] == "0"
        assert environment["GCM_INTERACTIVE"] == "Never"
        assert environment["GIT_PAGER"] == "cat"
        if "config" in command:
            config_calls += 1
            assert command[-5:] == (
                "config",
                "--includes",
                "-z",
                "--get-regexp",
                r"^core\.(autocrlf|eol)$",
            )
            assert environment["GIT_CONFIG_SYSTEM"] == configured_system
            assert environment["GIT_CONFIG_GLOBAL"] == configured_global
            assert "GIT_CONFIG_NOSYSTEM" not in environment
            continue
        assert "core.fsmonitor=false" in command
        assert "diff.external=" in command
        assert "credential.helper=" in command
        assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
        assert environment["GIT_CONFIG_SYSTEM"] == os.devnull
        assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert config_calls == 1
