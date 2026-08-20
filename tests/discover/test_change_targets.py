from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from kis_mcp.discover.change_inspection_contracts import InspectChangeRequest
from kis_mcp.discover.change_service import InspectChangeService
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


def _git_with_system_config(
    root: Path,
    system_config: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.pop("GIT_CONFIG_NOSYSTEM", None)
    environment.update(
        {
            "GIT_CONFIG_SYSTEM": str(system_config),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )


def _write_crlf(path: Path, content: str) -> None:
    path.write_bytes(content.replace("\n", "\r\n").encode("utf-8"))


def _create_autocrlf_linked_worktree(project_root: Path) -> tuple[Path, Path]:
    system_config = project_root.parent / f"{project_root.name}-system.gitconfig"
    system_config.write_text("[core]\n\tautocrlf = true\n\teol = native\n", encoding="utf-8")
    _git_with_system_config(project_root, system_config, "init", "-b", "main")
    _git_with_system_config(
        project_root, system_config, "config", "user.name", "Discover Tests"
    )
    _git_with_system_config(
        project_root,
        system_config,
        "config",
        "user.email",
        "discover@example.invalid",
    )
    (project_root / ".gitattributes").write_text(
        "attributes.txt text eol=crlf\n",
        encoding="utf-8",
    )
    for name in ("system.txt", "attributes.txt", "staged.txt", "unstaged.txt", "both.txt"):
        _write_crlf(project_root / name, f"base {name}\n")
    _git_with_system_config(project_root, system_config, "add", "--all")
    _git_with_system_config(project_root, system_config, "commit", "-m", "initial")
    linked = project_root.parent / f"{project_root.name}-autocrlf-linked"
    _git_with_system_config(
        project_root,
        system_config,
        "worktree",
        "add",
        "-b",
        "autocrlf-linked",
        str(linked),
    )
    return linked, system_config


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "--all")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def test_working_tree_inspection_matches_native_autocrlf_in_linked_worktree(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linked, system_config = _create_autocrlf_linked_worktree(project_root)
    monkeypatch.delenv("GIT_CONFIG_NOSYSTEM", raising=False)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(system_config))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)

    native = _git_with_system_config(linked, system_config, "diff", "--name-only")
    assert native.stdout == ""
    assert b"\r\n" in (linked / "system.txt").read_bytes()
    assert b"\r\n" in (linked / "attributes.txt").read_bytes()

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )
    result = reader.inspect_local_changes(str(linked))
    response = InspectChangeService(reader).inspect(
        InspectChangeRequest(path=str(linked), source="working_tree")
    )

    assert result.changes == ()
    assert result.diagnostics == ()
    assert result.source_fingerprint is not None
    assert response.changed_files == ()
    assert response.change.fingerprint == result.source_fingerprint


def test_linked_worktree_inventory_matches_native_staged_unstaged_and_untracked(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linked, system_config = _create_autocrlf_linked_worktree(project_root)
    monkeypatch.delenv("GIT_CONFIG_NOSYSTEM", raising=False)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(system_config))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)

    _write_crlf(linked / "staged.txt", "staged change\n")
    _git_with_system_config(linked, system_config, "add", "--", "staged.txt")
    _write_crlf(linked / "unstaged.txt", "unstaged change\n")
    _write_crlf(linked / "both.txt", "both staged\n")
    _git_with_system_config(linked, system_config, "add", "--", "both.txt")
    _write_crlf(linked / "both.txt", "both unstaged\n")
    _write_crlf(linked / "untracked.txt", "untracked\n")

    native_staged = set(
        _git_with_system_config(
            linked, system_config, "diff", "--cached", "--name-only"
        ).stdout.splitlines()
    )
    native_unstaged = set(
        _git_with_system_config(linked, system_config, "diff", "--name-only").stdout.splitlines()
    )
    native_untracked = set(
        _git_with_system_config(
            linked,
            system_config,
            "ls-files",
            "--others",
            "--exclude-standard",
        ).stdout.splitlines()
    )

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )
    result = reader.inspect_local_changes(str(linked))
    by_path = {item.path: item for item in result.changes}

    assert {path for path, item in by_path.items() if item.staged_status is not None} == native_staged
    assert {path for path, item in by_path.items() if item.worktree_status is not None} == native_unstaged
    assert {path for path, item in by_path.items() if item.untracked} == native_untracked
    assert by_path["both.txt"].staged_status == "modified"
    assert by_path["both.txt"].worktree_status == "modified"
    assert result.diagnostics == ()
    assert result.source_fingerprint is not None


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


def test_reader_inspects_two_parent_merge_as_first_parent_delta(
    project_root: Path,
    discover_settings,
) -> None:
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Discover Tests")
    _git(project_root, "config", "user.email", "discover@example.invalid")
    (project_root / "base.txt").write_text("base\n", encoding="utf-8")
    _commit(project_root, "initial")
    _git(project_root, "switch", "-c", "feature")
    (project_root / "feature.txt").write_text("feature\n", encoding="utf-8")
    _commit(project_root, "feature")
    _git(project_root, "switch", "main")
    (project_root / "main.txt").write_text("main\n", encoding="utf-8")
    _commit(project_root, "main work")
    _git(project_root, "merge", "--no-ff", "feature", "-m", "merge feature")
    merge_commit = _git(project_root, "rev-parse", "HEAD").stdout.strip()

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )
    result = reader.inspect_change_target(
        InspectChangeRequest(path=str(project_root), source="commit", commit_ref=merge_commit)
    )

    assert [item.path for item in result.changes] == ["feature.txt"]
    assert result.diagnostics == ()


def test_reader_rejects_multi_parent_merge_commit(
    project_root: Path,
    discover_settings,
) -> None:
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Discover Tests")
    _git(project_root, "config", "user.email", "discover@example.invalid")
    (project_root / "base.txt").write_text("base\n", encoding="utf-8")
    base = _commit(project_root, "initial")
    parents = [base]
    for index in range(2):
        branch = f"feature-{index}"
        _git(project_root, "switch", "-c", branch, base)
        (project_root / f"feature-{index}.txt").write_text(f"{index}\n", encoding="utf-8")
        parents.append(_commit(project_root, branch))
    tree = _git(project_root, "rev-parse", f"{base}^{{tree}}").stdout.strip()
    merge_commit = _git(
        project_root,
        "commit-tree",
        tree,
        "-p",
        parents[0],
        "-p",
        parents[1],
        "-p",
        parents[2],
        "-m",
        "synthetic three-parent merge",
    ).stdout.strip()

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )
    result = reader.inspect_change_target(
        InspectChangeRequest(path=str(project_root), source="commit", commit_ref=merge_commit)
    )

    assert result.changes == ()
    assert result.diagnostics[0]["code"] == "GIT_UNSUPPORTED_MERGE_COMMIT"


def test_working_tree_inspection_rejects_inventory_fingerprint_race(
    project_root: Path,
    discover_settings,
    monkeypatch,
) -> None:
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Discover Tests")
    _git(project_root, "config", "user.email", "discover@example.invalid")
    tracked = project_root / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    _commit(project_root, "initial")
    tracked.write_text("after\n", encoding="utf-8")

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )
    original = reader._git.inspect_local_changes
    calls = 0

    def racing_inventory(path: str):
        nonlocal calls
        calls += 1
        inventory = original(path)
        if calls == 2:
            (project_root / "late.txt").write_text("late\n", encoding="utf-8")
        return inventory

    monkeypatch.setattr(reader._git, "inspect_local_changes", racing_inventory)

    result = reader.inspect_local_changes(str(project_root))

    assert result.source_fingerprint is None
    assert any(
        item["code"] == "CHANGE_SOURCE_CHANGED_DURING_INSPECTION"
        for item in result.diagnostics
    )


def test_staged_inspection_rejects_inventory_fingerprint_race(
    project_root: Path,
    discover_settings,
    monkeypatch,
) -> None:
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Discover Tests")
    _git(project_root, "config", "user.email", "discover@example.invalid")
    tracked = project_root / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    _commit(project_root, "initial")
    tracked.write_text("after\n", encoding="utf-8")
    _git(project_root, "add", "tracked.txt")

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )
    original_run = reader._git._run
    raced = False

    def racing_run(root: Path, arguments: tuple[str, ...], deadline: float):
        nonlocal raced
        result = original_run(root, arguments, deadline)
        if not raced and "--name-status" in arguments and "--cached" in arguments:
            raced = True
            late = project_root / "late.txt"
            late.write_text("late\n", encoding="utf-8")
            _git(project_root, "add", "late.txt")
        return result

    monkeypatch.setattr(reader._git, "_run", racing_run)

    result = reader.inspect_change_target(
        InspectChangeRequest(path=str(project_root), source="staged")
    )

    assert result.source_fingerprint is None
    assert result.diagnostics[0]["code"] == "CHANGE_SOURCE_CHANGED_DURING_INSPECTION"


def test_reader_source_fingerprint_changes_when_content_changes_at_same_path(
    project_root: Path,
    discover_settings,
) -> None:
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Discover Tests")
    _git(project_root, "config", "user.email", "discover@example.invalid")
    tracked = project_root / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    _commit(project_root, "initial")

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )

    tracked.write_text("after-one\n", encoding="utf-8")
    first = reader.inspect_local_changes(str(project_root))
    tracked.write_text("after-two\n", encoding="utf-8")
    second = reader.inspect_local_changes(str(project_root))

    assert [item.path for item in first.changes] == ["tracked.txt"]
    assert [item.path for item in second.changes] == ["tracked.txt"]
    assert first.source_fingerprint is not None
    assert second.source_fingerprint is not None
    assert first.source_fingerprint != second.source_fingerprint


def test_reader_resolves_movable_target_refs_into_source_fingerprint(
    project_root: Path,
    discover_settings,
) -> None:
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Discover Tests")
    _git(project_root, "config", "user.email", "discover@example.invalid")
    tracked = project_root / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    _commit(project_root, "initial")
    _git(project_root, "switch", "-c", "feature")
    tracked.write_text("one\n", encoding="utf-8")
    _commit(project_root, "one")

    reader = GitChangeReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )
    request = InspectChangeRequest(
        path=str(project_root),
        source="branch",
        base_ref="main",
        head_ref="feature",
    )
    first = reader.inspect_change_target(request)
    first_response = InspectChangeService(reader).inspect(request)

    tracked.write_text("two\n", encoding="utf-8")
    _commit(project_root, "two")
    second = reader.inspect_change_target(request)
    second_response = InspectChangeService(reader).inspect(request)

    assert [item.path for item in first.changes] == ["tracked.txt"]
    assert [item.path for item in second.changes] == ["tracked.txt"]
    assert first.source_fingerprint != second.source_fingerprint
    assert first_response.change.fingerprint == first.source_fingerprint
    assert second_response.change.fingerprint == second.source_fingerprint


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
