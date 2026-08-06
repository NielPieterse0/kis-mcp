from __future__ import annotations

import ntpath

from ...paths import is_within_windows_boundary, normalize_windows_path
from .settings import SerenaSettings

_GLOBAL_PREFIX = "global/"


def _segments(memory_name: str) -> tuple[bool, tuple[str, ...]]:
    if not isinstance(memory_name, str) or not memory_name.strip():
        raise ValueError("memory_name must be a non-empty string")
    raw = memory_name.strip().replace("\\", "/")
    if ntpath.isabs(raw) or raw.startswith("/"):
        raise ValueError("memory_name must be relative")
    global_memory = raw.casefold().startswith(_GLOBAL_PREFIX)
    if global_memory:
        raw = raw[len(_GLOBAL_PREFIX) :]
    parts = tuple(raw.split("/"))
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("memory_name contains a forbidden path segment")
    if any(":" in part or "\x00" in part for part in parts):
        raise ValueError("memory_name contains an invalid path segment")
    return global_memory, parts


def memory_root(
    settings: SerenaSettings,
    *,
    project_root: str,
    global_memory: bool,
) -> str:
    if global_memory:
        root = normalize_windows_path(
            str(settings.global_memory_root),
            base=settings.project_boundary,
        )
    else:
        root = normalize_windows_path(
            ntpath.join(project_root, settings.project_data_directory, "memories"),
            base=project_root,
        )
    if not is_within_windows_boundary(root, boundary=settings.project_boundary):
        raise ValueError("memory root must remain inside project_boundary")
    return root


def resolve_memory_path(
    settings: SerenaSettings,
    memory_name: str,
    *,
    project_root: str,
) -> tuple[str, str]:
    global_memory, parts = _segments(memory_name)
    root = memory_root(
        settings,
        project_root=project_root,
        global_memory=global_memory,
    )
    relative = ntpath.join(*parts) + ".md"
    path = normalize_windows_path(relative, base=root)
    if not is_within_windows_boundary(path, boundary=root):
        raise ValueError("memory_name resolves outside its memory root")
    return path, root


__all__ = ["memory_root", "resolve_memory_path"]