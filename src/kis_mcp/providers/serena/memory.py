from __future__ import annotations

import ntpath
from dataclasses import dataclass
from pathlib import Path

from ...paths import is_within_windows_boundary, normalize_windows_path
from ...quarantine import QuarantineRecord, QuarantineService
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
    if any(any(marker in part for marker in ("*", "?", "[", "]")) for part in parts):
        raise ValueError("memory_name wildcard syntax is not accepted for safety interception")
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
            ntpath.join(str(settings.ensure_project_data_path(project_root)), "memories"),
            base=str(settings.project_data_root),
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


__all__ = [
    "SerenaMemoryArtifactSet",
    "SerenaMemoryQuarantineResult",
    "memory_root",
    "quarantine_serena_memory_delete",
    "resolve_memory_path",
    "resolve_serena_memory_artifacts",
]

@dataclass(frozen=True, slots=True)
class SerenaMemoryArtifactSet:
    memory_name: str
    artifacts: tuple[str, ...]
    catalogue_model: str = "derived_from_markdown_files"
    pinned_version: str = "1.6.1"


@dataclass(frozen=True, slots=True)
class SerenaMemoryQuarantineResult:
    memory_name: str
    artifacts: tuple[str, ...]
    records: tuple[QuarantineRecord, ...]
    forwarded_delete: bool = False
    status: str = "quarantined"


def resolve_serena_memory_artifacts(
    settings: SerenaSettings,
    memory_name: str,
    *,
    project_root: str,
) -> SerenaMemoryArtifactSet:
    if settings.package_version != "1.6.1":
        raise ValueError("Serena delete-memory artifact proof is pinned to version 1.6.1")
    path, _root = resolve_memory_path(
        settings,
        memory_name,
        project_root=project_root,
    )
    return SerenaMemoryArtifactSet(memory_name=memory_name, artifacts=(path,))


def quarantine_serena_memory_delete(
    settings: SerenaSettings,
    memory_name: str,
    *,
    project_root: str,
    quarantine: QuarantineService,
) -> SerenaMemoryQuarantineResult:
    affected = resolve_serena_memory_artifacts(
        settings,
        memory_name,
        project_root=project_root,
    )
    existing = tuple(path for path in affected.artifacts if Path(path).exists() or Path(path).is_symlink())
    if not existing:
        return SerenaMemoryQuarantineResult(
            memory_name=memory_name,
            artifacts=affected.artifacts,
            records=(),
            status="not_found",
        )
    records = tuple(quarantine.quarantine_many(existing))
    return SerenaMemoryQuarantineResult(
        memory_name=memory_name,
        artifacts=affected.artifacts,
        records=records,
    )
