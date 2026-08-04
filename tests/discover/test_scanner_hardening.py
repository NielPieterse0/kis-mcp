from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

from kis_mcp.discover.read_authority import ReadAuthority
from kis_mcp.discover.scanner import RepositoryScanner


def _scanner(project_root: Path, settings):
    return RepositoryScanner(ReadAuthority(Path(r"C:\Projects"), settings), settings)


def _with_limits(settings, **overrides: int):
    return replace(settings, limits=replace(settings.limits, **overrides))


def test_scanner_never_reads_file_contents(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (project_root / "example.py").write_text("raise RuntimeError\n", encoding="utf-8")
    authority = ReadAuthority(Path(r"C:\Projects"), discover_settings)

    def fail_read(*args, **kwargs):
        raise AssertionError("scanner must not read file content")

    monkeypatch.setattr(authority, "read_relative_text", fail_read)

    snapshot = RepositoryScanner(authority, discover_settings).snapshot(str(project_root))

    assert [item.label for item in snapshot.files] == ["example.py"]


def test_scanner_reports_unsafe_links_and_hard_links(
    project_root: Path,
    discover_settings,
) -> None:
    target = project_root / "target.py"
    target.write_text("target = True\n", encoding="utf-8")
    hard = project_root / "hard.py"
    try:
        os.link(target, hard)
    except OSError:
        hard = None

    linked = project_root / "linked.py"
    try:
        linked.symlink_to(target)
    except OSError:
        linked = None

    snapshot = _scanner(project_root, discover_settings).snapshot(str(project_root))

    expected_excluded = []
    if hard is not None:
        expected_excluded.extend(["hard.py", "target.py"])
    if linked is not None:
        expected_excluded.append("linked.py")
    if not expected_excluded:
        pytest.skip("Links are unavailable on this platform")
    assert snapshot.excluded_paths == tuple(sorted(expected_excluded, key=str.casefold))
    assert snapshot.truncated is True
    assert "unsafe_file" in snapshot.truncation_reasons


def test_traversal_deadline_returns_bounded_partial_result(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _with_limits(discover_settings, traversal_timeout_seconds=1)
    for name in ("a.py", "b.py"):
        (project_root / name).write_text(name, encoding="utf-8")

    moments = iter((0.0, 0.1, 2.0, 2.0, 2.0))
    monkeypatch.setattr(
        "kis_mcp.discover.scanner.time.monotonic",
        lambda: next(moments, 2.0),
    )

    snapshot = _scanner(project_root, settings).snapshot(str(project_root))

    assert [item.label for item in snapshot.files] == ["a.py"]
    assert snapshot.truncated is True
    assert snapshot.truncation_reasons == ("traversal_timeout",)


def test_excluded_segment_matching_is_case_insensitive(
    project_root: Path,
    discover_settings,
) -> None:
    excluded = project_root / "NODE_MODULES"
    excluded.mkdir()
    (excluded / "ignored.py").write_text("ignored\n", encoding="utf-8")

    snapshot = _scanner(project_root, discover_settings).snapshot(str(project_root))

    assert snapshot.files == ()
    assert snapshot.directories == ()
    assert snapshot.excluded_paths == ("NODE_MODULES",)
    assert snapshot.truncated is False
