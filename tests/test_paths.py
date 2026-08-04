from __future__ import annotations

from kis_mcp.paths import is_within_windows_boundary, normalize_windows_path


def test_normalizes_relative_path_against_base() -> None:
    assert normalize_windows_path(
        r".\kis-mcp\file.txt", base=r"C:\Projects"
    ) == r"C:\Projects\kis-mcp\file.txt"


def test_boundary_accepts_true_descendant() -> None:
    assert is_within_windows_boundary(
        r"C:\Projects\kis-mcp\file.txt", boundary=r"C:\Projects"
    )


def test_boundary_rejects_similar_prefix() -> None:
    assert not is_within_windows_boundary(
        r"C:\Projects-old\file.txt", boundary=r"C:\Projects"
    )


def test_boundary_is_case_insensitive() -> None:
    assert is_within_windows_boundary(
        r"c:\projects\KIS-MCP\file.txt", boundary=r"C:\Projects"
    )
