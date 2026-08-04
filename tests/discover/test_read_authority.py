from __future__ import annotations

import os
from pathlib import Path

import pytest

from kis_mcp.discover.errors import DiscoverError


def test_reads_only_safe_relative_text(
    project_root: Path,
    discover_settings,
) -> None:
    from kis_mcp.discover.read_authority import ReadAuthority

    source = project_root / "src" / "example.py"
    source.parent.mkdir()
    source.write_text("alpha\nbeta\n", encoding="utf-8")
    authority = ReadAuthority(Path(r"C:\Projects"), discover_settings)

    info = authority.inspect(str(project_root))
    text = authority.read_relative_text(
        str(project_root),
        "src/example.py",
        max_bytes=100,
    )

    assert info.kind == "directory"
    assert info.label == "."
    assert text.label == "src/example.py"
    assert text.content == "alpha\nbeta\n"
    assert text.truncated is False


@pytest.mark.parametrize(
    "label",
    [
        "../outside.py",
        "src/../example.py",
        "/absolute.py",
        r"C:\Projects\other.py",
        "src//example.py",
        "src/./example.py",
    ],
)
def test_relative_reads_reject_escape_and_ambiguous_labels(
    project_root: Path,
    discover_settings,
    label: str,
) -> None:
    from kis_mcp.discover.read_authority import ReadAuthority

    authority = ReadAuthority(Path(r"C:\Projects"), discover_settings)

    with pytest.raises(DiscoverError) as captured:
        authority.read_relative_text(str(project_root), label, max_bytes=100)

    assert captured.value.code == "DISCOVER_RELATIVE_PATH_INVALID"


def test_read_revalidates_size_after_snapshot(
    project_root: Path,
    discover_settings,
) -> None:
    from kis_mcp.discover.read_authority import ReadAuthority
    from kis_mcp.discover.scanner import RepositoryScanner

    source = project_root / "small.py"
    source.write_text("x = 1\n", encoding="utf-8")
    authority = ReadAuthority(Path(r"C:\Projects"), discover_settings)
    snapshot = RepositoryScanner(authority, discover_settings).snapshot(str(project_root))
    assert snapshot.files[0].label == "small.py"

    source.write_text("x" * 2_000, encoding="utf-8")

    with pytest.raises(DiscoverError, match="size limit") as captured:
        authority.read_relative_text(str(project_root), "small.py", max_bytes=1_000)
    assert captured.value.code == "DISCOVER_FILE_TOO_LARGE"


def test_read_rejects_hard_linked_files(
    project_root: Path,
    discover_settings,
) -> None:
    from kis_mcp.discover.read_authority import ReadAuthority

    source = project_root / "source.py"
    linked = project_root / "linked.py"
    source.write_text("sensitive = True\n", encoding="utf-8")
    try:
        os.link(source, linked)
    except OSError:
        pytest.skip("Hard links are unavailable on this platform")

    authority = ReadAuthority(Path(r"C:\Projects"), discover_settings)

    with pytest.raises(DiscoverError, match="Hard-linked") as captured:
        authority.read_relative_text(str(project_root), "linked.py", max_bytes=100)
    assert captured.value.code == "DISCOVER_FILE_UNSAFE"


def test_missing_relative_file_returns_structural_error(
    project_root: Path,
    discover_settings,
) -> None:
    from kis_mcp.discover.read_authority import ReadAuthority

    authority = ReadAuthority(Path(r"C:\Projects"), discover_settings)

    with pytest.raises(DiscoverError, match="does not exist") as captured:
        authority.read_relative_text(str(project_root), "missing.py", max_bytes=100)

    assert captured.value.code == "DISCOVER_FILE_NOT_FOUND"


def test_hard_link_rejection_is_controlled_by_settings(
    project_root: Path,
    discover_settings,
) -> None:
    from dataclasses import replace

    from kis_mcp.discover.read_authority import ReadAuthority

    source = project_root / "source.py"
    linked = project_root / "linked.py"
    source.write_text("shared = True\n", encoding="utf-8")
    try:
        os.link(source, linked)
    except OSError:
        pytest.skip("Hard links are unavailable on this platform")

    settings = replace(discover_settings, reject_hard_links=False)
    authority = ReadAuthority(Path(r"C:\Projects"), settings)

    result = authority.read_relative_text(str(project_root), "linked.py", max_bytes=100)

    assert result.content == "shared = True\n"


def test_read_rejects_symlink_or_reparse_chain(
    project_root: Path,
    discover_settings,
) -> None:
    from kis_mcp.discover.read_authority import ReadAuthority

    target = project_root / "real"
    target.mkdir()
    (target / "example.py").write_text("x = 1\n", encoding="utf-8")
    linked = project_root / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are unavailable on this platform")

    authority = ReadAuthority(Path(r"C:\Projects"), discover_settings)

    with pytest.raises(DiscoverError, match="link|reparse") as captured:
        authority.read_relative_text(
            str(project_root),
            "linked/example.py",
            max_bytes=100,
        )
    assert captured.value.code == "DISCOVER_PATH_UNSAFE"
