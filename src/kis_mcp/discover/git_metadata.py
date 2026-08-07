from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import os
from pathlib import Path
import re
import stat

from .read_authority import is_within_boundary


_REPARSE_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_MAX_INCLUDE_DEPTH = 8
_HEX_OBJECT_ID = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")


class GitMetadataValidationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GitMetadataGraph:
    git_dir: Path
    common_dir: Path
    object_dir: Path
    index_path: Path
    active_config_files: tuple[Path, ...]
    active_alternates: tuple[Path, ...]


def validate_git_metadata_graph(
    root: Path,
    *,
    boundary: Path,
    maximum_file_bytes: int,
) -> GitMetadataGraph:
    marker = root / ".git"
    git_dir = _resolve_git_dir(
        marker,
        root=root,
        boundary=boundary,
        maximum=maximum_file_bytes,
    )
    common_dir = _resolve_common_dir(
        git_dir,
        boundary=boundary,
        maximum=maximum_file_bytes,
    )

    _validate_directory(git_dir, boundary=boundary, required=True)
    _validate_directory(common_dir, boundary=boundary, required=True)

    object_dir = common_dir / "objects"
    _validate_directory(object_dir, boundary=boundary, required=False)

    config = _GitConfigState(
        git_dir=git_dir,
        branch=_current_branch(git_dir, boundary, maximum_file_bytes),
    )
    active_config_files: list[Path] = []
    common_config = common_dir / "config"
    _load_active_config(
        common_config,
        boundary=boundary,
        maximum=maximum_file_bytes,
        state=config,
        active_files=active_config_files,
        depth=0,
        seen=set(),
    )

    if config.worktree_config_enabled:
        _load_active_config(
            git_dir / "config.worktree",
            boundary=boundary,
            maximum=maximum_file_bytes,
            state=config,
            active_files=active_config_files,
            depth=0,
            seen=set(),
        )

    index_path = git_dir / "index"
    _validate_regular_file_identity(index_path, boundary=boundary, required=False)

    active_alternates: list[Path] = []
    if _resolved_head_object(git_dir, common_dir, boundary, maximum_file_bytes):
        alternates_file = object_dir / "info" / "alternates"
        if alternates_file.exists():
            data = _read_regular_file(
                alternates_file,
                boundary=boundary,
                maximum=maximum_file_bytes,
            )
            for raw_line in data.decode("utf-8", errors="strict").splitlines():
                value = raw_line.strip()
                if not value:
                    continue
                candidate = Path(value)
                target = candidate if candidate.is_absolute() else object_dir / candidate
                target = _canonical_active_path(target, boundary=boundary)
                _validate_directory(target, boundary=boundary, required=True)
                active_alternates.append(target)

    return GitMetadataGraph(
        git_dir=git_dir,
        common_dir=common_dir,
        object_dir=object_dir,
        index_path=index_path,
        active_config_files=tuple(dict.fromkeys(active_config_files)),
        active_alternates=tuple(dict.fromkeys(active_alternates)),
    )


@dataclass(slots=True)
class _GitConfigState:
    git_dir: Path
    branch: str | None
    worktree_config_enabled: bool = False


def _resolve_git_dir(
    marker: Path,
    *,
    root: Path,
    boundary: Path,
    maximum: int,
) -> Path:
    try:
        info = os.lstat(marker)
    except FileNotFoundError as exc:
        raise GitMetadataValidationError("GIT_NOT_REPOSITORY") from exc
    if _is_link_or_reparse(info):
        raise GitMetadataValidationError("GIT_METADATA_UNSAFE")
    if stat.S_ISDIR(info.st_mode):
        return _canonical_active_path(marker, boundary=boundary)
    if not stat.S_ISREG(info.st_mode):
        raise GitMetadataValidationError("GIT_METADATA_INVALID")
    data = _read_regular_file(marker, boundary=boundary, maximum=maximum)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitMetadataValidationError("GIT_METADATA_ENCODING_INVALID") from exc
    match = re.fullmatch(r"gitdir:\s*(.+?)\s*\r?\n?", text)
    if match is None:
        raise GitMetadataValidationError("GIT_METADATA_INVALID")
    candidate = Path(match.group(1))
    target = candidate if candidate.is_absolute() else root / candidate
    target = _canonical_active_path(target, boundary=boundary)
    _validate_directory(target, boundary=boundary, required=True)
    return target


def _resolve_common_dir(git_dir: Path, *, boundary: Path, maximum: int) -> Path:
    marker = git_dir / "commondir"
    if not marker.exists():
        return git_dir
    data = _read_regular_file(marker, boundary=boundary, maximum=maximum)
    try:
        value = data.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise GitMetadataValidationError("GIT_METADATA_ENCODING_INVALID") from exc
    if not value or "\x00" in value:
        raise GitMetadataValidationError("GIT_METADATA_INVALID")
    candidate = Path(value)
    target = candidate if candidate.is_absolute() else git_dir / candidate
    target = _canonical_active_path(target, boundary=boundary)
    _validate_directory(target, boundary=boundary, required=True)
    return target


def _load_active_config(
    path: Path,
    *,
    boundary: Path,
    maximum: int,
    state: _GitConfigState,
    active_files: list[Path],
    depth: int,
    seen: set[Path],
) -> None:
    if depth > _MAX_INCLUDE_DEPTH or not path.exists():
        return
    resolved = _canonical_active_path(path, boundary=boundary)
    if resolved in seen:
        return
    data = _read_regular_file(resolved, boundary=boundary, maximum=maximum)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise GitMetadataValidationError("GIT_METADATA_ENCODING_INVALID") from exc
    seen.add(resolved)
    active_files.append(resolved)

    section = ""
    includes: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        header = re.fullmatch(r"\[(.+)]", line)
        if header:
            section = header.group(1).strip()
            continue
        key, value = _config_assignment(line)
        if key is None:
            continue
        lowered_section = section.casefold()
        lowered_key = key.casefold()
        if lowered_section == "extensions" and lowered_key == "worktreeconfig":
            state.worktree_config_enabled = value.casefold() in {"true", "yes", "on", "1"}
            continue
        if lowered_section == "include" and lowered_key == "path":
            includes.append(("always", value))
            continue
        if lowered_section.startswith("includeif ") and lowered_key == "path":
            includes.append((section, value))

    for condition, raw_path in includes:
        if condition != "always" and not _include_condition_matches(condition, state):
            continue
        if not raw_path or "://" in raw_path:
            raise GitMetadataValidationError("GIT_METADATA_INVALID")
        candidate = Path(os.path.expanduser(raw_path))
        include_path = candidate if candidate.is_absolute() else resolved.parent / candidate
        include_path = _canonical_active_path(include_path, boundary=boundary)
        _load_active_config(
            include_path,
            boundary=boundary,
            maximum=maximum,
            state=state,
            active_files=active_files,
            depth=depth + 1,
            seen=seen,
        )


def _include_condition_matches(section: str, state: _GitConfigState) -> bool:
    match = re.fullmatch(r'includeif\s+"(.+)"', section, re.IGNORECASE)
    if match is None:
        return False
    condition = match.group(1)
    lowered = condition.casefold()
    if lowered.startswith("gitdir/i:"):
        pattern = condition[len("gitdir/i:") :]
        return _path_pattern_matches(pattern, state.git_dir, case_sensitive=False)
    if lowered.startswith("gitdir:"):
        pattern = condition[len("gitdir:") :]
        return _path_pattern_matches(pattern, state.git_dir, case_sensitive=True)
    if lowered.startswith("onbranch:"):
        if state.branch is None:
            return False
        pattern = condition[len("onbranch:") :]
        return fnmatch.fnmatchcase(state.branch, pattern)
    return False


def _path_pattern_matches(pattern: str, path: Path, *, case_sensitive: bool) -> bool:
    expanded = os.path.expanduser(pattern).replace("\\", "/")
    actual = str(path).replace("\\", "/")
    if expanded.endswith("/"):
        expanded += "**"
    if not case_sensitive:
        expanded = expanded.casefold()
        actual = actual.casefold()
    return fnmatch.fnmatchcase(actual, expanded)


def _current_branch(git_dir: Path, boundary: Path, maximum: int) -> str | None:
    head = git_dir / "HEAD"
    if not head.exists():
        return None
    data = _read_regular_file(head, boundary=boundary, maximum=maximum)
    try:
        text = data.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        return None
    prefix = "ref: refs/heads/"
    return text[len(prefix) :] if text.startswith(prefix) else None


def _resolved_head_object(
    git_dir: Path,
    common_dir: Path,
    boundary: Path,
    maximum: int,
) -> str | None:
    head = git_dir / "HEAD"
    if not head.exists():
        return None
    data = _read_regular_file(head, boundary=boundary, maximum=maximum)
    try:
        text = data.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        return None
    if _HEX_OBJECT_ID.fullmatch(text):
        return text.casefold()
    if not text.startswith("ref: "):
        return None
    reference = text[5:].strip()
    for base in (git_dir, common_dir):
        ref_path = base / Path(reference)
        if ref_path.exists():
            value = _read_regular_file(
                ref_path,
                boundary=boundary,
                maximum=maximum,
            ).decode("ascii", errors="ignore").strip()
            if _HEX_OBJECT_ID.fullmatch(value):
                return value.casefold()
    packed = common_dir / "packed-refs"
    if packed.exists():
        text = _read_regular_file(
            packed,
            boundary=boundary,
            maximum=maximum,
        ).decode("utf-8", errors="replace")
        for line in text.splitlines():
            if not line or line.startswith(("#", "^")):
                continue
            oid, separator, name = line.partition(" ")
            if separator and name.strip() == reference and _HEX_OBJECT_ID.fullmatch(oid):
                return oid.casefold()
    return None


def _config_assignment(line: str) -> tuple[str | None, str]:
    key, separator, value = line.partition("=")
    if separator:
        return key.strip(), value.strip().strip('"')
    parts = line.split(None, 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip().strip('"')
    return None, ""


def _canonical_active_path(path: Path, *, boundary: Path) -> Path:
    if not is_within_boundary(boundary, path):
        raise GitMetadataValidationError("GIT_METADATA_OUTSIDE_BOUNDARY")
    _assert_safe_existing_components(path, boundary=boundary)
    resolved = path.resolve(strict=False)
    if not is_within_boundary(boundary, resolved):
        raise GitMetadataValidationError("GIT_METADATA_OUTSIDE_BOUNDARY")
    return resolved


def _assert_safe_existing_components(path: Path, *, boundary: Path) -> None:
    try:
        relative = path.absolute().relative_to(boundary.absolute())
    except ValueError as exc:
        raise GitMetadataValidationError("GIT_METADATA_OUTSIDE_BOUNDARY") from exc
    current = boundary.absolute()
    for part in relative.parts:
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return
        if _is_link_or_reparse(info):
            raise GitMetadataValidationError("GIT_METADATA_UNSAFE")


def _validate_directory(path: Path, *, boundary: Path, required: bool) -> None:
    canonical = _canonical_active_path(path, boundary=boundary)
    try:
        info = os.lstat(canonical)
    except FileNotFoundError as exc:
        if required:
            raise GitMetadataValidationError("GIT_METADATA_TARGET_MISSING") from exc
        return
    if _is_link_or_reparse(info):
        raise GitMetadataValidationError("GIT_METADATA_UNSAFE")
    if not stat.S_ISDIR(info.st_mode):
        raise GitMetadataValidationError("GIT_METADATA_TARGET_NOT_DIRECTORY")


def _validate_regular_file_identity(
    path: Path,
    *,
    boundary: Path,
    required: bool,
) -> None:
    canonical = _canonical_active_path(path, boundary=boundary)
    try:
        info = os.lstat(canonical)
    except FileNotFoundError as exc:
        if required:
            raise GitMetadataValidationError("GIT_METADATA_TARGET_MISSING") from exc
        return
    if _is_link_or_reparse(info) or not stat.S_ISREG(info.st_mode):
        raise GitMetadataValidationError("GIT_METADATA_UNSAFE")


def _validate_regular_file(
    path: Path,
    *,
    boundary: Path,
    maximum: int,
    required: bool,
) -> None:
    if not path.exists() and not required:
        return
    _read_regular_file(path, boundary=boundary, maximum=maximum)


def _read_regular_file(path: Path, *, boundary: Path, maximum: int) -> bytes:
    canonical = _canonical_active_path(path, boundary=boundary)
    try:
        expected = os.lstat(canonical)
    except FileNotFoundError as exc:
        raise GitMetadataValidationError("GIT_METADATA_TARGET_MISSING") from exc
    if _is_link_or_reparse(expected) or not stat.S_ISREG(expected.st_mode):
        raise GitMetadataValidationError("GIT_METADATA_UNSAFE")
    if expected.st_size > maximum:
        raise GitMetadataValidationError("GIT_METADATA_TOO_LARGE")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(canonical, flags)
    try:
        opened = os.fstat(descriptor)
        if _identity(expected) != _identity(opened) or not stat.S_ISREG(opened.st_mode):
            raise GitMetadataValidationError("GIT_METADATA_UNSAFE")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if _identity(opened) != _identity(after) or opened.st_size != after.st_size:
            raise GitMetadataValidationError("GIT_METADATA_UNSAFE")
    finally:
        os.close(descriptor)
    if len(data) > maximum:
        raise GitMetadataValidationError("GIT_METADATA_TOO_LARGE")
    return data


def _identity(info: os.stat_result) -> tuple[int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode)


def _is_link_or_reparse(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & _REPARSE_FLAG
    )


__all__ = [
    "GitMetadataGraph",
    "GitMetadataValidationError",
    "validate_git_metadata_graph",
]
