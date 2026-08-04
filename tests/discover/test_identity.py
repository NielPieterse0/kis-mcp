from __future__ import annotations

from pathlib import Path

import pytest

from kis_mcp.discover.errors import DiscoverError


def test_resolves_canonical_project_identity(project_root: Path, discover_settings) -> None:
    from kis_mcp.discover.read_authority import ReadAuthority

    authority = ReadAuthority(
        boundary=Path(r"C:\Projects"),
        settings=discover_settings,
    )

    identity = authority.resolve_project(str(project_root))

    assert identity.canonical_path == str(project_root.resolve())
    assert identity.repository_root == str(project_root.resolve())
    assert identity.project_id.startswith("local:")
    assert identity.git_root is None
    assert identity.remote_identity is None


def test_project_identity_rejects_empty_nul_missing_and_file_paths(
    project_root: Path,
    discover_settings,
) -> None:
    from kis_mcp.discover.read_authority import ReadAuthority

    authority = ReadAuthority(Path(r"C:\Projects"), discover_settings)
    source = project_root / "file.py"
    source.write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(DiscoverError, match="non-empty") as empty:
        authority.resolve_project("")
    assert empty.value.code == "DISCOVER_PATH_INVALID"

    with pytest.raises(DiscoverError, match="NUL") as nul:
        authority.resolve_project(str(project_root) + "\x00")
    assert nul.value.code == "DISCOVER_PATH_INVALID"

    with pytest.raises(DiscoverError, match="does not exist") as missing:
        authority.resolve_project(str(project_root / "missing"))
    assert missing.value.code == "DISCOVER_PATH_NOT_FOUND"

    with pytest.raises(DiscoverError, match="directory") as file_error:
        authority.resolve_project(str(source))
    assert file_error.value.code == "DISCOVER_PATH_NOT_DIRECTORY"


def test_project_identity_rejects_outside_root_and_prefix_collisions(
    discover_settings,
) -> None:
    from kis_mcp.discover.read_authority import ReadAuthority, is_within_boundary

    boundary = Path(r"C:\Projects")
    authority = ReadAuthority(boundary, discover_settings)

    assert is_within_boundary(boundary, Path(r"C:\Projects\demo")) is True
    assert is_within_boundary(boundary, Path(r"C:\Projects-escape\demo")) is False

    with pytest.raises(DiscoverError) as captured:
        authority.resolve_project(r"C:\Windows")
    assert captured.value.code == "DISCOVER_PATH_OUTSIDE_ROOT"
    assert not captured.value.code.startswith("HR-")
