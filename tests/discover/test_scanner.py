from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from kis_mcp.discover.read_authority import ReadAuthority
from kis_mcp.discover.scanner import RepositoryScanner


def _scanner(project_root: Path, settings):
    return RepositoryScanner(ReadAuthority(Path(r"C:\Projects"), settings), settings)


def _with_limits(settings, **overrides: int):
    return replace(settings, limits=replace(settings.limits, **overrides))


def test_scanner_recurses_deterministically_and_reports_exclusions(
    project_root: Path,
    discover_settings,
) -> None:
    for label, content in (
        ("z.py", "z = 1\n"),
        ("a.py", "a = 1\n"),
        ("src/b.py", "b = 1\n"),
        ("src/a.py", "a = 2\n"),
        ("tests/test_a.py", "def test_a(): pass\n"),
        ("node_modules/ignored.py", "ignored = True\n"),
        ("build/generated.py", "generated = True\n"),
        ("notes.bin", "ignored"),
    ):
        path = project_root / Path(label)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    snapshot = _scanner(project_root, discover_settings).snapshot(str(project_root))

    assert [item.label for item in snapshot.files] == [
        "a.py",
        "src/a.py",
        "src/b.py",
        "tests/test_a.py",
        "z.py",
    ]
    assert [item.category for item in snapshot.files] == [
        "source",
        "source",
        "source",
        "test",
        "source",
    ]
    assert snapshot.directories == ("src", "tests")
    assert snapshot.excluded_paths == ("build", "node_modules")
    assert snapshot.truncated is False
    assert snapshot.truncation_reasons == ()


def test_exact_file_capacity_is_not_truncation(
    project_root: Path,
    discover_settings,
) -> None:
    settings = _with_limits(discover_settings, max_files=2)
    (project_root / "a.py").write_text("a\n", encoding="utf-8")
    (project_root / "b.py").write_text("b\n", encoding="utf-8")

    snapshot = _scanner(project_root, settings).snapshot(str(project_root))

    assert [item.label for item in snapshot.files] == ["a.py", "b.py"]
    assert snapshot.truncated is False


def test_first_file_over_capacity_sets_max_files_truncation(
    project_root: Path,
    discover_settings,
) -> None:
    settings = _with_limits(discover_settings, max_files=2)
    for name in ("c.py", "a.py", "b.py"):
        (project_root / name).write_text(name, encoding="utf-8")

    snapshot = _scanner(project_root, settings).snapshot(str(project_root))

    assert [item.label for item in snapshot.files] == ["a.py", "b.py"]
    assert snapshot.truncated is True
    assert snapshot.truncation_reasons == ("max_files",)


def test_narrow_file_budget_prioritizes_manifest_and_application_source(
    project_root: Path,
    discover_settings,
) -> None:
    settings = _with_limits(discover_settings, max_files=2)
    for label in (
        ".agents/skills/helper.py",
        ".archive/legacy.py",
        "src/app.py",
    ):
        path = project_root / Path(label)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(label, encoding="utf-8")
    (project_root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    snapshot = _scanner(project_root, settings).snapshot(str(project_root))

    assert [item.label for item in snapshot.files] == ["pyproject.toml", "src/app.py"]
    assert snapshot.truncated is True
    assert snapshot.truncation_reasons == ("max_files",)


def test_total_and_per_file_byte_limits_are_reported(
    project_root: Path,
    discover_settings,
) -> None:
    settings = _with_limits(
        discover_settings,
        max_total_bytes=6,
        max_file_bytes=5,
    )
    (project_root / "a.py").write_bytes(b"12345")
    (project_root / "b.py").write_bytes(b"67890")
    (project_root / "large.py").write_bytes(b"123456")

    snapshot = _scanner(project_root, settings).snapshot(str(project_root))

    assert [item.label for item in snapshot.files] == ["a.py"]
    assert snapshot.total_bytes == 5
    assert snapshot.truncated is True
    assert snapshot.truncation_reasons == ("max_file_bytes", "max_total_bytes")


def test_depth_limit_omits_only_deeper_entries(
    project_root: Path,
    discover_settings,
) -> None:
    settings = _with_limits(discover_settings, max_depth=1)
    (project_root / "root.py").write_text("root\n", encoding="utf-8")
    (project_root / "src").mkdir()
    (project_root / "src" / "first.py").write_text("first\n", encoding="utf-8")
    (project_root / "src" / "nested").mkdir()
    (project_root / "src" / "nested" / "deep.py").write_text(
        "deep\n", encoding="utf-8"
    )

    snapshot = _scanner(project_root, settings).snapshot(str(project_root))

    assert [item.label for item in snapshot.files] == ["root.py", "src/first.py"]
    assert snapshot.directories == ("src",)
    assert snapshot.truncated is True
    assert snapshot.truncation_reasons == ("max_depth",)


def test_directory_limit_is_deterministic(
    project_root: Path,
    discover_settings,
) -> None:
    settings = _with_limits(discover_settings, max_directories=1)
    for name in ("b", "a"):
        directory = project_root / name
        directory.mkdir()
        (directory / "file.py").write_text(name, encoding="utf-8")

    snapshot = _scanner(project_root, settings).snapshot(str(project_root))

    assert snapshot.directories == ("a",)
    assert [item.label for item in snapshot.files] == ["a/file.py"]
    assert snapshot.truncated is True
    assert snapshot.truncation_reasons == ("max_directories",)


def test_visited_entry_limit_stops_before_unbounded_collection(
    project_root: Path,
    discover_settings,
) -> None:
    settings = _with_limits(discover_settings, max_visited_entries=2)
    for name in ("a.py", "b.py", "c.py"):
        (project_root / name).write_text(name, encoding="utf-8")

    snapshot = _scanner(project_root, settings).snapshot(str(project_root))

    assert [item.label for item in snapshot.files] == ["a.py", "b.py"]
    assert snapshot.visited_entries == 2
    assert snapshot.truncated is True
    assert snapshot.truncation_reasons == ("max_visited_entries",)
