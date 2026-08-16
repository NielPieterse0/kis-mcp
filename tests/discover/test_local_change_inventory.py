from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.change_contracts import (
    ChangePathRecord,
    ChangeSummary,
    LocalChangeInventory,
)
from kis_mcp.discover.read_authority import ReadAuthority


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPOSITORY_ROOT / "contracts" / "discover" / "local-change-inventory.schema.json"


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
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


def _commit_files(root: Path, files: dict[str, str], subject: str) -> None:
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(root, "add", "--", *files)
    _git(root, "commit", "-m", subject)


def _reader(settings):
    from kis_mcp.discover.git_reader import GitReader

    return GitReader(
        authority=ReadAuthority(Path(r"C:\Projects"), settings),
        settings=settings,
    )


def _with_limits(settings, **overrides: int):
    return replace(settings, limits=replace(settings.limits, **overrides))


def _example_inventory() -> LocalChangeInventory:
    return LocalChangeInventory(
        project_path=r"C:\Projects\example",
        repository_root=r"C:\Projects\example",
        changes=(
            ChangePathRecord(
                path="src/new.py",
                previous_path="src/old.py",
                staged_status="renamed",
                worktree_status="modified",
                untracked=False,
            ),
            ChangePathRecord(
                path="tests/test_new.py",
                previous_path=None,
                staged_status=None,
                worktree_status=None,
                untracked=True,
            ),
        ),
        summary=ChangeSummary(
            total=2,
            staged=1,
            unstaged=1,
            untracked=1,
            renamed=1,
            copied=0,
            deleted=0,
            conflicted=0,
        ),
        diagnostics=(
            {
                "code": "GIT_CHANGE_OUTPUT_TRUNCATED",
                "message": "Local Git change output exceeded the configured byte limit.",
            },
        ),
        truncated=True,
    )


def test_local_change_inventory_serializes_stable_contract() -> None:
    payload = _example_inventory().to_json_dict()

    assert payload == {
        "schema_version": 1,
        "source": "local_git",
        "project_path": r"C:\Projects\example",
        "repository_root": r"C:\Projects\example",
        "changes": [
            {
                "path": "src/new.py",
                "previous_path": "src/old.py",
                "staged_status": "renamed",
                "worktree_status": "modified",
                "untracked": False,
            },
            {
                "path": "tests/test_new.py",
                "previous_path": None,
                "staged_status": None,
                "worktree_status": None,
                "untracked": True,
            },
        ],
        "summary": {
            "total": 2,
            "staged": 1,
            "unstaged": 1,
            "untracked": 1,
            "renamed": 1,
            "copied": 0,
            "deleted": 0,
            "conflicted": 0,
        },
        "diagnostics": [
            {
                "code": "GIT_CHANGE_OUTPUT_TRUNCATED",
                "message": "Local Git change output exceeded the configured byte limit.",
            },
        ],
        "truncated": True,
    }


def test_local_change_inventory_payload_matches_checked_in_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    errors = sorted(
        validator.iter_errors(_example_inventory().to_json_dict()),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )

    assert errors == []


def test_clean_repository_returns_empty_inventory(
    project_root: Path,
    discover_settings,
) -> None:
    _init_repository(project_root)
    _commit_files(project_root, {"tracked.txt": "tracked\n"}, "initial")

    inventory = _reader(discover_settings).inspect_local_changes(str(project_root))

    assert inventory.project_path == str(project_root.resolve())
    assert inventory.repository_root == str(project_root.resolve())
    assert inventory.changes == ()
    assert inventory.summary == ChangeSummary()
    assert inventory.diagnostics == ()
    assert inventory.truncated is False


def test_merges_staged_unstaged_and_untracked_changes_deterministically(
    project_root: Path,
    discover_settings,
) -> None:
    _init_repository(project_root)
    _commit_files(
        project_root,
        {
            "shared.txt": "base\n",
            "worktree.txt": "base\n",
        },
        "initial",
    )

    (project_root / "staged.txt").write_text("staged\n", encoding="utf-8")
    _git(project_root, "add", "--", "staged.txt")

    (project_root / "shared.txt").write_text("staged shared\n", encoding="utf-8")
    _git(project_root, "add", "--", "shared.txt")
    (project_root / "shared.txt").write_text("unstaged shared\n", encoding="utf-8")

    (project_root / "worktree.txt").write_text("unstaged\n", encoding="utf-8")
    (project_root / "untracked.txt").write_text("untracked\n", encoding="utf-8")

    reader = _reader(discover_settings)
    first = reader.inspect_local_changes(str(project_root))
    second = reader.inspect_local_changes(str(project_root))

    assert first == second
    assert [change.path for change in first.changes] == [
        "shared.txt",
        "staged.txt",
        "untracked.txt",
        "worktree.txt",
    ]
    assert first.changes == (
        ChangePathRecord(
            path="shared.txt",
            staged_status="modified",
            worktree_status="modified",
        ),
        ChangePathRecord(path="staged.txt", staged_status="added"),
        ChangePathRecord(path="untracked.txt", untracked=True),
        ChangePathRecord(path="worktree.txt", worktree_status="modified"),
    )
    assert first.summary == ChangeSummary(
        total=4,
        staged=2,
        unstaged=2,
        untracked=1,
        renamed=0,
        copied=0,
        deleted=0,
        conflicted=0,
    )
    assert first.diagnostics == ()
    assert first.truncated is False


def test_records_renames_copies_and_deletions(
    project_root: Path,
    discover_settings,
) -> None:
    _init_repository(project_root)
    _commit_files(
        project_root,
        {
            "rename-old.txt": "rename content\n",
            "copy-source.txt": "copy content\n",
            "deleted.txt": "delete content\n",
        },
        "initial",
    )

    _git(project_root, "mv", "rename-old.txt", "rename-new.txt")
    (project_root / "copy-target.txt").write_text("copy content\n", encoding="utf-8")
    (project_root / "copy-source.txt").write_text("changed source\n", encoding="utf-8")
    (project_root / "deleted.txt").unlink()
    _git(project_root, "add", "-A")

    inventory = _reader(discover_settings).inspect_local_changes(str(project_root))
    by_path = {change.path: change for change in inventory.changes}

    assert by_path["rename-new.txt"] == ChangePathRecord(
        path="rename-new.txt",
        previous_path="rename-old.txt",
        staged_status="renamed",
    )
    assert by_path["copy-target.txt"] == ChangePathRecord(
        path="copy-target.txt",
        previous_path="copy-source.txt",
        staged_status="copied",
    )
    assert by_path["deleted.txt"] == ChangePathRecord(
        path="deleted.txt",
        staged_status="deleted",
    )
    assert inventory.summary.renamed == 1
    assert inventory.summary.copied == 1
    assert inventory.summary.deleted == 1


def test_normalizes_type_change_and_conflict_statuses() -> None:
    from kis_mcp.discover.git_reader import _normalize_change_status

    assert _normalize_change_status("T") == "type_changed"
    assert _normalize_change_status("U") == "unmerged"
    assert _normalize_change_status("D") == "deleted"
    assert _normalize_change_status("R100") == "renamed"
    assert _normalize_change_status("C087") == "copied"
    assert _normalize_change_status("X") == "unknown"


def test_record_limit_is_deterministic_and_explicit(
    project_root: Path,
    discover_settings,
) -> None:
    _init_repository(project_root)
    _commit_files(project_root, {"tracked.txt": "tracked\n"}, "initial")
    for name in ("charlie.txt", "alpha.txt", "bravo.txt"):
        (project_root / name).write_text(name, encoding="utf-8")

    inventory = _reader(
        _with_limits(discover_settings, max_files=2)
    ).inspect_local_changes(str(project_root))

    assert [change.path for change in inventory.changes] == ["alpha.txt", "bravo.txt"]
    assert inventory.summary.total == 2
    assert [item["code"] for item in inventory.diagnostics] == [
        "CHANGE_ENTRY_LIMIT_REACHED"
    ]
    assert inventory.truncated is True


def test_bounded_output_discards_incomplete_final_path_and_reports_truncation(
    project_root: Path,
    discover_settings,
) -> None:
    _init_repository(project_root)
    _commit_files(project_root, {"tracked.txt": "tracked\n"}, "initial")
    expected = {
        f"untracked-{index:03}-{'x' * 40}.txt"
        for index in range(30)
    }
    for name in expected:
        (project_root / name).write_text("x\n", encoding="utf-8")

    inventory = _reader(
        _with_limits(discover_settings, git_max_output_bytes=256)
    ).inspect_local_changes(str(project_root))

    assert {change.path for change in inventory.changes}.issubset(expected)
    assert [item["code"] for item in inventory.diagnostics] == [
        "GIT_CHANGE_OUTPUT_TRUNCATED"
    ]
    assert inventory.truncated is True


def test_truncated_repository_root_is_not_accepted(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kis_mcp.discover import git_reader

    (project_root / ".git").mkdir()
    calls = 0

    def fake_run(command, *, cwd, environment, timeout_seconds, max_output_bytes):
        nonlocal calls
        calls += 1
        return git_reader._GitCommandResult(
            0,
            str(project_root.parent).encode(),
            b"",
            True,
            0,
        )

    monkeypatch.setattr(git_reader, "_run_bounded", fake_run)

    inventory = _reader(discover_settings).inspect_local_changes(str(project_root))

    assert calls == 1
    assert inventory.repository_root is None
    assert inventory.changes == ()
    assert [item["code"] for item in inventory.diagnostics] == [
        "GIT_CHANGE_OUTPUT_TRUNCATED"
    ]
    assert inventory.truncated is True


def test_uses_fixed_non_executing_git_change_commands(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kis_mcp.discover import git_reader

    (project_root / ".git").mkdir()
    calls: list[tuple[str, ...]] = []
    configurations: list[tuple[str, ...]] = []
    environments: list[dict[str, str]] = []
    configured_system = r"C:\Projects\system.gitconfig"
    monkeypatch.delenv("GIT_CONFIG_NOSYSTEM", raising=False)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", configured_system)

    def fake_run(command, *, cwd, environment, timeout_seconds, max_output_bytes):
        marker = command.index("-C")
        configurations.append(tuple(command[:marker]))
        environments.append(environment)
        arguments = tuple(command[marker + 2 :])
        calls.append(arguments)
        if arguments == ("rev-parse", "--show-toplevel"):
            stdout = str(project_root).encode()
        elif arguments and arguments[0] == "config":
            stdout = b"core.autocrlf\nyes\x00core.eol\nnative\x00"
        else:
            stdout = b""
        return git_reader._GitCommandResult(0, stdout, b"", False, 0)

    monkeypatch.setattr(git_reader, "_run_bounded", fake_run)

    inventory = _reader(discover_settings).inspect_local_changes(str(project_root))

    assert inventory.changes == ()
    config_probe = (
        "config",
        "--includes",
        "-z",
        "--get-regexp",
        r"^core\.(autocrlf|eol)$",
    )
    assert calls == [
        ("rev-parse", "--show-toplevel"),
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
        config_probe,
        (
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--name-status",
            "-z",
            "--find-renames",
            "--find-copies",
        ),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ]
    for arguments, configuration, environment in zip(calls, configurations, environments, strict=True):
        if arguments == config_probe:
            assert configuration[-1] == "--no-pager"
            assert environment["GIT_CONFIG_SYSTEM"] == configured_system
            assert "GIT_CONFIG_NOSYSTEM" not in environment
            continue
        assert "core.attributesFile=" in configuration
        assert "core.excludesFile=" in configuration
        if arguments and arguments[0] == "diff":
            if "--cached" in arguments:
                assert "core.autocrlf=true" not in configuration
                assert "core.eol=native" not in configuration
            else:
                assert "core.autocrlf=true" in configuration
                assert "core.eol=native" in configuration
            assert environment["GIT_CONFIG_SYSTEM"] == os.devnull


def test_non_repository_returns_structural_diagnostic(
    project_root: Path,
    discover_settings,
) -> None:
    inventory = _reader(discover_settings).inspect_local_changes(str(project_root))

    assert inventory.repository_root is None
    assert inventory.changes == ()
    assert inventory.summary == ChangeSummary()
    assert [item["code"] for item in inventory.diagnostics] == [
        "GIT_NOT_REPOSITORY"
    ]
    assert inventory.truncated is False
