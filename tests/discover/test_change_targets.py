from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from kis_mcp.discover.change_inspection_contracts import InspectChangeRequest
from kis_mcp.discover.change_targets import build_target_arguments, parse_name_status
from kis_mcp.discover.git_change_reader import GitChangeReader
from kis_mcp.discover.read_authority import ReadAuthority


def test_build_target_arguments_uses_fixed_templates() -> None:
    staged = InspectChangeRequest(path=r"C:\Projects\repo", source="staged")
    assert build_target_arguments(staged) == (
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--cached",
        "--name-status",
        "-z",
        "--find-renames",
        "--find-copies",
    )

    commit = InspectChangeRequest(
        path=r"C:\Projects\repo",
        source="commit",
        commit_ref="a" * 40,
    )
    assert build_target_arguments(commit) == (
        "diff-tree",
        "--root",
        "--no-commit-id",
        "-r",
        "--no-ext-diff",
        "--no-textconv",
        "--name-status",
        "-z",
        "--find-renames",
        "--find-copies",
        "--end-of-options",
        "a" * 40,
        "--",
    )

    comparison = InspectChangeRequest(
        path=r"C:\Projects\repo",
        source="range",
        base_ref="main",
        head_ref="feature/discover",
    )
    assert build_target_arguments(comparison)[-3:] == (
        "--end-of-options",
        "main...feature/discover",
        "--",
    )


@pytest.mark.parametrize("source", ["working_tree", "unknown"])
def test_build_target_arguments_rejects_unsupported_direct_target(source: str) -> None:
    request = object.__new__(InspectChangeRequest)
    object.__setattr__(request, "path", r"C:\Projects\repo")
    object.__setattr__(request, "source", source)
    object.__setattr__(request, "commit_ref", None)
    object.__setattr__(request, "base_ref", None)
    object.__setattr__(request, "head_ref", None)

    with pytest.raises(ValueError, match="target source"):
        build_target_arguments(request)


def test_parse_name_status_preserves_rename_copy_and_order() -> None:
    output = (
        b"R100\x00legacy/old.py\x00src/new.py\x00"
        b"C075\x00src/base.py\x00src/copy.py\x00"
        b"M\x00README.md\x00"
    )

    records = parse_name_status(output)

    assert [(item.path, item.previous_path, item.staged_status) for item in records] == [
        ("README.md", None, "modified"),
        ("src/copy.py", "src/base.py", "copied"),
        ("src/new.py", "legacy/old.py", "renamed"),
    ]


def test_parse_name_status_drops_incomplete_trailing_record() -> None:
    assert parse_name_status(b"R100\x00old.py\x00") == ()


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


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "--all")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def test_reader_inspects_commit_range_and_branch_targets(
    project_root: Path,
    discover_settings,
) -> None:
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Discover Tests")
    _git(project_root, "config", "user.email", "discover@example.invalid")
    source = project_root / "src" / "value.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    first = _commit(project_root, "initial")

    _git(project_root, "switch", "-c", "feature/discover")
    source.write_text("value = 2\n", encoding="utf-8")
    test_file = project_root / "tests" / "test_value.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_value():\n    assert True\n", encoding="utf-8")
    second = _commit(project_root, "change value")

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )

    commit = reader.inspect_change_target(
        InspectChangeRequest(
            path=str(project_root),
            source="commit",
            commit_ref=second,
        )
    )
    comparison = reader.inspect_change_target(
        InspectChangeRequest(
            path=str(project_root),
            source="range",
            base_ref=first,
            head_ref=second,
        )
    )
    branch = reader.inspect_change_target(
        InspectChangeRequest(
            path=str(project_root),
            source="branch",
            base_ref="main",
            head_ref="feature/discover",
        )
    )

    expected = ["src/value.py", "tests/test_value.py"]
    assert [item.path for item in commit.changes] == expected
    assert [item.path for item in comparison.changes] == expected
    assert [item.path for item in branch.changes] == expected
    assert commit.diagnostics == comparison.diagnostics == branch.diagnostics == ()
    assert commit.repository_root == str(project_root)


def test_reader_inspects_staged_target_only(
    project_root: Path,
    discover_settings,
) -> None:
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Discover Tests")
    _git(project_root, "config", "user.email", "discover@example.invalid")
    tracked = project_root / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    _commit(project_root, "initial")

    tracked.write_text("after\n", encoding="utf-8")
    staged = project_root / "staged.txt"
    staged.write_text("staged\n", encoding="utf-8")
    _git(project_root, "add", "--", "staged.txt")

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )
    result = reader.inspect_change_target(
        InspectChangeRequest(path=str(project_root), source="staged")
    )

    assert [item.path for item in result.changes] == ["staged.txt"]
    assert result.changes[0].staged_status == "added"
