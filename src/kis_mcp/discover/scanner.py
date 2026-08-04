from __future__ import annotations

import ctypes
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .contracts import ProjectIdentity
from .read_authority import ReadAuthority
from .settings import DiscoverSettings

_REPARSE_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


@dataclass(frozen=True, slots=True)
class ScannedFile:
    label: str
    size: int
    suffix: str
    category: str


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    project: ProjectIdentity
    files: tuple[ScannedFile, ...]
    directories: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    total_bytes: int
    visited_entries: int
    truncated: bool
    truncation_reasons: tuple[str, ...]


class RepositoryScanner:
    def __init__(self, authority: ReadAuthority, settings: DiscoverSettings) -> None:
        self.authority = authority
        self.settings = settings
        self._excluded_segments = {
            segment.casefold() for segment in settings.excluded_segments
        }
        self._allowed_filenames = set(settings.allowed_filenames)

    def snapshot(self, project_path: str) -> RepositorySnapshot:
        project = self.authority.resolve_project(project_path)
        root = Path(project.canonical_path)
        files: list[ScannedFile] = []
        directories: list[str] = []
        excluded: list[str] = []
        reasons: set[str] = set()
        total_bytes = 0
        visited_entries = 0
        stop = False
        deadline = time.monotonic() + self.settings.limits.traversal_timeout_seconds

        def collect_entries(directory: Path) -> tuple[list[os.DirEntry[str]], bool]:
            remaining = self.settings.limits.max_visited_entries - visited_entries
            collected: list[os.DirEntry[str]] = []
            stop_after_batch = False
            try:
                with os.scandir(directory) as iterator:
                    for entry in iterator:
                        if time.monotonic() > deadline:
                            reasons.add("traversal_timeout")
                            stop_after_batch = True
                            break
                        if len(collected) >= remaining:
                            reasons.add("max_visited_entries")
                            stop_after_batch = True
                            break
                        collected.append(entry)
            except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
                reasons.add("filesystem_changed")
                return [], False
            collected.sort(key=lambda entry: entry.name.casefold())
            return collected, stop_after_batch

        def visit(directory: Path, depth: int) -> None:
            nonlocal total_bytes, visited_entries, stop
            if stop:
                return
            entries, stop_after_batch = collect_entries(directory)

            for entry in entries:
                visited_entries += 1
                candidate = Path(entry.path)
                label = candidate.relative_to(root).as_posix()
                if entry.name.casefold() in self._excluded_segments:
                    excluded.append(label)
                    continue
                try:
                    info = entry.stat(follow_symlinks=False)
                except (FileNotFoundError, PermissionError, OSError):
                    reasons.add("filesystem_changed")
                    continue

                if self._is_link_or_reparse(info):
                    excluded.append(label)
                    reasons.add(
                        "unsafe_directory"
                        if entry.is_dir(follow_symlinks=False)
                        else "unsafe_file"
                    )
                    continue

                if entry.is_dir(follow_symlinks=False):
                    if depth >= self.settings.limits.max_depth:
                        reasons.add("max_depth")
                        continue
                    if len(directories) >= self.settings.limits.max_directories:
                        reasons.add("max_directories")
                        continue
                    directories.append(label)
                    if not stop_after_batch:
                        visit(candidate, depth + 1)
                    continue

                if not entry.is_file(follow_symlinks=False):
                    excluded.append(label)
                    reasons.add("unsafe_file")
                    continue
                if self.settings.reject_hard_links and self._link_count(candidate, info) > 1:
                    excluded.append(label)
                    reasons.add("unsafe_file")
                    continue

                suffix = candidate.suffix.casefold()
                if (
                    suffix not in self.settings.allowed_extensions
                    and entry.name not in self._allowed_filenames
                ):
                    continue
                if info.st_size > self.settings.limits.max_file_bytes:
                    reasons.add("max_file_bytes")
                    continue
                if len(files) >= self.settings.limits.max_files:
                    reasons.add("max_files")
                    stop = True
                    return
                if total_bytes + info.st_size > self.settings.limits.max_total_bytes:
                    reasons.add("max_total_bytes")
                    continue

                files.append(
                    ScannedFile(
                        label=label,
                        size=info.st_size,
                        suffix=suffix,
                        category=self._category(label),
                    )
                )
                total_bytes += info.st_size

            if stop_after_batch:
                stop = True

        visit(root, 0)
        files.sort(key=lambda item: item.label.casefold())
        directories.sort(key=str.casefold)
        excluded.sort(key=str.casefold)
        return RepositorySnapshot(
            project=project,
            files=tuple(files),
            directories=tuple(directories),
            excluded_paths=tuple(excluded),
            total_bytes=total_bytes,
            visited_entries=visited_entries,
            truncated=bool(reasons),
            truncation_reasons=tuple(sorted(reasons)),
        )

    @staticmethod
    def _category(label: str) -> str:
        path = PurePosixPath(label)
        parts = tuple(part.casefold() for part in path.parts)
        name = parts[-1]
        if (
            "test" in parts
            or "tests" in parts
            or name.startswith("test_")
            or name.endswith("_test.py")
        ):
            return "test"
        if any(part in {"docs", "doc", "documentation"} for part in parts):
            return "documentation"
        if name.endswith(".md"):
            return "documentation"
        if any(part in {"config", "configs", ".github"} for part in parts):
            return "configuration"
        return "source"

    @staticmethod
    def _is_link_or_reparse(info: os.stat_result) -> bool:
        return stat.S_ISLNK(info.st_mode) or bool(
            getattr(info, "st_file_attributes", 0) & _REPARSE_FLAG
        )

    @staticmethod
    def _link_count(path: Path, info: os.stat_result) -> int:
        if info.st_nlink > 1 or os.name != "nt":
            return int(info.st_nlink)
        return _windows_link_count(path) or int(info.st_nlink)


def _windows_link_count(path: Path) -> int | None:
    if os.name != "nt":
        return None

    class ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("file_attributes", ctypes.c_ulong),
            ("creation_time_low", ctypes.c_ulong),
            ("creation_time_high", ctypes.c_ulong),
            ("last_access_time_low", ctypes.c_ulong),
            ("last_access_time_high", ctypes.c_ulong),
            ("last_write_time_low", ctypes.c_ulong),
            ("last_write_time_high", ctypes.c_ulong),
            ("volume_serial_number", ctypes.c_ulong),
            ("file_size_high", ctypes.c_ulong),
            ("file_size_low", ctypes.c_ulong),
            ("number_of_links", ctypes.c_ulong),
            ("file_index_high", ctypes.c_ulong),
            ("file_index_low", ctypes.c_ulong),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    get_information = kernel32.GetFileInformationByHandle
    get_information.argtypes = [ctypes.c_void_p, ctypes.POINTER(ByHandleFileInformation)]
    get_information.restype = ctypes.c_int
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int

    handle = create_file(
        str(path),
        0,
        0x00000001 | 0x00000002 | 0x00000004,
        None,
        3,
        0x02000000,
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle in (None, invalid_handle):
        return None
    try:
        information = ByHandleFileInformation()
        if not get_information(handle, ctypes.byref(information)):
            return None
        return int(information.number_of_links)
    finally:
        close_handle(handle)


__all__ = ["RepositoryScanner", "RepositorySnapshot", "ScannedFile"]
