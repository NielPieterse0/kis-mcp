from __future__ import annotations

import ntpath
from pathlib import Path


class PathValidationError(ValueError):
    pass


def normalize_windows_path(value: str, *, base: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PathValidationError("Path must be a non-empty string")

    raw = value.strip().replace("/", "\\")
    if "\x00" in raw:
        raise PathValidationError("Path must not contain a null byte")
    base_normalized = ntpath.normpath(base.replace("/", "\\"))
    candidate = raw if ntpath.isabs(raw) else ntpath.join(base_normalized, raw)
    normalized = ntpath.normpath(candidate)

    drive, _ = ntpath.splitdrive(normalized)
    if not drive:
        raise PathValidationError(f"Path has no Windows drive: {value}")

    return normalized


def resolve_windows_effective_path(
    value: str,
    *,
    base: str,
    follow_final: bool,
) -> str:
    """Resolve existing links and junctions without requiring the target to exist.

    Content writes follow the final path. Directory-entry mutations resolve only
    the parent so moving or quarantining a link affects the link itself rather
    than the object it references.
    """

    normalized = normalize_windows_path(value, base=base)
    candidate = Path(normalized)
    target = candidate if follow_final else candidate.parent
    try:
        resolved = target.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise PathValidationError(f"Unable to resolve path safely: {value}") from exc
    effective = resolved if follow_final else resolved / candidate.name
    return ntpath.normpath(str(effective))


def is_within_windows_boundary(path: str, *, boundary: str) -> bool:
    normalized_boundary = ntpath.normcase(
        normalize_windows_path(boundary, base=boundary)
    )
    normalized_path = ntpath.normcase(
        normalize_windows_path(path, base=normalized_boundary)
    )

    try:
        return ntpath.commonpath([normalized_boundary, normalized_path]) == normalized_boundary
    except ValueError:
        return False
