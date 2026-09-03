from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from kis_mcp.capabilities import governed_change


def _completed(argv: list[str], *, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")


def test_commit_change_treats_git_diff_returncode_one_as_staged_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(governed_change, "_within_project_boundary", lambda _raw: tmp_path)

    def fake_run(argv: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "branch", "--show-current"]:
            return _completed(argv, stdout="change/638-test\n")
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return _completed(argv, stdout="abc123\n")
        return _completed(argv)

    monkeypatch.setattr(governed_change, "_run", fake_run)
    returncodes = iter((0, 1))
    monkeypatch.setattr(
        governed_change.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], next(returncodes)),
    )

    result = governed_change._commit_change(
        {"path": str(tmp_path), "message": "test", "paths": ["src/example.py"]}
    )

    assert result["head"] == "abc123"
    assert result["branch"] == "change/638-test"


def test_commit_change_rejects_when_selected_paths_have_no_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(governed_change, "_within_project_boundary", lambda _raw: tmp_path)
    monkeypatch.setattr(
        governed_change,
        "_run",
        lambda argv, *, cwd: _completed(argv, stdout="change/638-test\n")
        if argv[:3] == ["git", "branch", "--show-current"]
        else _completed(argv),
    )
    returncodes = iter((0, 0))
    monkeypatch.setattr(
        governed_change.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], next(returncodes)),
    )

    with pytest.raises(ValueError, match="NO_STAGED_CHANGE"):
        governed_change._commit_change(
            {"path": str(tmp_path), "message": "test", "paths": ["src/example.py"]}
        )



def test_commit_change_rejects_preexisting_staged_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(governed_change, "_within_project_boundary", lambda _raw: tmp_path)
    monkeypatch.setattr(
        governed_change,
        "_run",
        lambda argv, *, cwd: _completed(argv, stdout="change/638-test\n")
        if argv[:3] == ["git", "branch", "--show-current"]
        else _completed(argv),
    )
    monkeypatch.setattr(
        governed_change.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1),
    )

    with pytest.raises(ValueError, match="PREEXISTING_STAGED_CHANGES"):
        governed_change._commit_change(
            {"path": str(tmp_path), "message": "test", "paths": ["src/example.py"]}
        )
