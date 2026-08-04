from __future__ import annotations

import hashlib
import ntpath
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .contracts import ProjectIdentity
from .errors import DiscoverError
from .settings import DiscoverSettings

_REPARSE_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


@dataclass(frozen=True, slots=True)
class PathInspection:
    label: str
    kind: str
    size: int


@dataclass(frozen=True, slots=True)
class TextRead:
    label: str
    content: str
    encoding: str
    truncated: bool


def is_within_boundary(boundary: Path, candidate: Path) -> bool:
    """Return true only when candidate is the boundary or a real descendant."""
    normalized_boundary = ntpath.normcase(ntpath.abspath(str(boundary)))
    normalized_candidate = ntpath.normcase(ntpath.abspath(str(candidate)))
    try:
        common = ntpath.commonpath((normalized_boundary, normalized_candidate))
    except ValueError:
        return False
    return common == normalized_boundary


class ReadAuthority:
    def __init__(self, boundary: Path, settings: DiscoverSettings) -> None:
        self.boundary = boundary
        self.settings = settings

    def resolve_project(self, value: str) -> ProjectIdentity:
        if not isinstance(value, str) or not value.strip():
            raise self._error(
                "DISCOVER_PATH_INVALID",
                "Project path must be a non-empty string.",
                "No project path was supplied.",
                field="path",
            )
        if "\x00" in value:
            raise self._error(
                "DISCOVER_PATH_INVALID",
                "Project path may not contain a NUL character.",
                "NUL characters cannot identify a filesystem path.",
                field="path",
            )

        candidate = Path(value)
        if not is_within_boundary(self.boundary, candidate):
            raise self._error(
                "DISCOVER_PATH_OUTSIDE_ROOT",
                "The project path is outside the configured read boundary.",
                f"Canonical path is not beneath {self.boundary}.",
                field="path",
            )
        try:
            self._assert_no_link_chain(candidate)
            canonical = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise self._error(
                "DISCOVER_PATH_NOT_FOUND",
                "The project path does not exist.",
                "The requested local directory could not be resolved.",
                field="path",
            ) from exc
        if not is_within_boundary(self.boundary, canonical):
            raise self._error(
                "DISCOVER_PATH_OUTSIDE_ROOT",
                "The project path is outside the configured read boundary.",
                f"Canonical path is not beneath {self.boundary}.",
                field="path",
            )
        if not canonical.is_dir():
            raise self._error(
                "DISCOVER_PATH_NOT_DIRECTORY",
                "The project path must identify a directory.",
                "The resolved project path is not a directory.",
                field="path",
            )
        self._assert_no_link_chain(canonical)
        digest = hashlib.sha256(str(canonical).casefold().encode("utf-8")).hexdigest()[:20]
        return ProjectIdentity(
            project_id=f"local:{digest}",
            canonical_path=str(canonical),
            repository_root=str(canonical),
            git_root=None,
            remote_identity=None,
        )

    def inspect(self, value: str) -> PathInspection:
        identity = self.resolve_project(value)
        root = Path(identity.canonical_path)
        info = root.stat(follow_symlinks=False)
        return PathInspection(label=".", kind="directory", size=info.st_size)

    def read_relative_text(
        self,
        project_path: str,
        label: str,
        *,
        max_bytes: int,
    ) -> TextRead:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise self._error(
                "DISCOVER_LIMIT_INVALID",
                "Read limit must be a positive integer.",
                "The requested byte limit is not valid.",
                field="max_bytes",
            )
        parts = self._relative_parts(label)
        identity = self.resolve_project(project_path)
        root = Path(identity.canonical_path)
        target = root.joinpath(*parts)
        try:
            self._assert_no_link_chain(target)
            before = os.lstat(target)
        except FileNotFoundError as exc:
            raise self._error(
                "DISCOVER_FILE_NOT_FOUND",
                "The requested project file does not exist.",
                f"No file exists at {label}.",
                field="path",
            ) from exc

        limit = min(max_bytes, self.settings.limits.max_file_bytes)
        self._validate_regular_file(before, label, limit)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(target, flags)
        except OSError as exc:
            raise self._error(
                "DISCOVER_FILE_UNSAFE",
                "The requested project file could not be opened safely.",
                f"Safe open failed for {label}.",
                field="path",
            ) from exc
        try:
            opened = os.fstat(descriptor)
            self._validate_regular_file(opened, label, limit)
            if self._identity(before) != self._identity(opened):
                raise self._error(
                    "DISCOVER_FILE_CHANGED",
                    "The requested project file changed during validation.",
                    f"Filesystem identity changed for {label}.",
                    field="path",
                    retryable=True,
                )
            data = self._read_bounded(descriptor, limit)
            after = os.fstat(descriptor)
            if self._identity(opened) != self._identity(after) or opened.st_size != after.st_size:
                raise self._error(
                    "DISCOVER_FILE_CHANGED",
                    "The requested project file changed while being read.",
                    f"Filesystem identity or size changed for {label}.",
                    field="path",
                    retryable=True,
                )
        finally:
            os.close(descriptor)

        for encoding in self.settings.text_encodings:
            try:
                content = data.decode(encoding)
            except UnicodeDecodeError:
                continue
            return TextRead(
                label=PurePosixPath(*parts).as_posix(),
                content=content.replace("\r\n", "\n").replace("\r", "\n"),
                encoding=encoding,
                truncated=False,
            )
        raise self._error(
            "DISCOVER_FILE_DECODE_FAILED",
            "The requested project file is not decodable with configured encodings.",
            f"Configured encodings could not decode {label}.",
            field="path",
        )

    def _relative_parts(self, label: str) -> tuple[str, ...]:
        if not isinstance(label, str) or not label or "\x00" in label:
            raise self._relative_error()
        if "\\" in label or label.startswith("/") or ":" in label or "//" in label:
            raise self._relative_error()
        parts = tuple(label.split("/"))
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise self._relative_error()
        return parts

    def _relative_error(self) -> DiscoverError:
        return self._error(
            "DISCOVER_RELATIVE_PATH_INVALID",
            "Project file labels must be unambiguous repository-relative paths.",
            "Absolute paths, traversal, empty components, and alternate separators are not accepted.",
            field="path",
        )

    def _assert_no_link_chain(self, path: Path) -> None:
        absolute = path.absolute()
        current = Path(absolute.anchor)
        for part in absolute.parts[1:]:
            current = current / part
            try:
                info = os.lstat(current)
            except FileNotFoundError:
                raise
            if self._is_link_or_reparse(info):
                raise self._error(
                    "DISCOVER_PATH_UNSAFE",
                    "Project paths may not traverse a link or reparse point.",
                    f"Unsafe filesystem component encountered at {current}.",
                    field="path",
                )

    def _validate_regular_file(
        self,
        info: os.stat_result,
        label: str,
        maximum: int,
    ) -> None:
        if self._is_link_or_reparse(info) or not stat.S_ISREG(info.st_mode):
            raise self._error(
                "DISCOVER_FILE_UNSAFE",
                "The requested project path is not a safe regular file.",
                f"Unsupported filesystem object at {label}.",
                field="path",
            )
        if self.settings.reject_hard_links and info.st_nlink > 1:
            raise self._error(
                "DISCOVER_FILE_UNSAFE",
                "Hard-linked project files are not accepted by current Discover settings.",
                f"Hard-linked filesystem object at {label}.",
                field="path",
            )
        if info.st_size > maximum:
            raise self._error(
                "DISCOVER_FILE_TOO_LARGE",
                "The requested project file exceeds the configured size limit.",
                f"File size for {label} exceeds {maximum} bytes.",
                field="path",
            )

    @staticmethod
    def _read_bounded(descriptor: int, maximum: int) -> bytes:
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > maximum:
            raise DiscoverError(
                code="DISCOVER_FILE_TOO_LARGE",
                message="The requested project file exceeds the configured size limit.",
                reason=f"The file exceeded {maximum} bytes while being read.",
                field="path",
            )
        return data

    @staticmethod
    def _identity(info: os.stat_result) -> tuple[int, int, int]:
        return (info.st_dev, info.st_ino, info.st_mode)

    @staticmethod
    def _is_link_or_reparse(info: os.stat_result) -> bool:
        return stat.S_ISLNK(info.st_mode) or bool(
            getattr(info, "st_file_attributes", 0) & _REPARSE_FLAG
        )

    @staticmethod
    def _error(
        code: str,
        message: str,
        reason: str,
        *,
        field: str | None = None,
        retryable: bool = False,
    ) -> DiscoverError:
        return DiscoverError(
            code=code,
            message=message,
            reason=reason,
            field=field,
            corrective_actions=(),
            retryable=retryable,
        )


__all__ = ["PathInspection", "ReadAuthority", "TextRead", "is_within_boundary"]
