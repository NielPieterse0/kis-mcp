from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class PayloadHashLimits:
    max_entries: int = 100_000
    max_bytes: int = 10 * 1024 * 1024 * 1024
    max_depth: int = 256
    max_duration_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_entries < 1:
            raise ValueError("max_entries must be positive")
        if self.max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative")
        if self.max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive")


DEFAULT_PAYLOAD_HASH_LIMITS = PayloadHashLimits()


class PayloadHashLimitError(ValueError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        entries: int,
        bytes_read: int,
        depth: int,
        elapsed_seconds: float,
    ) -> None:
        super().__init__(
            f"{code}: {message} "
            f"(entries={entries}, bytes={bytes_read}, depth={depth}, "
            f"elapsed_seconds={elapsed_seconds:.6f})"
        )
        self.code = code
        self.entries = entries
        self.bytes_read = bytes_read
        self.depth = depth
        self.elapsed_seconds = elapsed_seconds


def metadata_bytes(fields: Mapping[str, object]) -> bytes:
    """Return the canonical byte representation used for metadata authentication."""

    return json.dumps(
        dict(fields),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sign_metadata(key: bytes, fields: Mapping[str, object]) -> str:
    """Return an HMAC-SHA-256 digest for the complete metadata field set."""

    return hmac.new(key, metadata_bytes(fields), hashlib.sha256).hexdigest()


def verify_metadata(
    key: bytes,
    fields: Mapping[str, object],
    digest: str,
) -> bool:
    """Verify metadata using constant-time digest comparison."""

    expected = sign_metadata(key, fields)
    return hmac.compare_digest(expected, digest)


def payload_sha256(
    path: Path,
    *,
    limits: PayloadHashLimits = DEFAULT_PAYLOAD_HASH_LIMITS,
    clock: Callable[[], float] = time.monotonic,
) -> str:
    """Hash one payload with bounded iterative traversal and no link following."""

    hasher = hashlib.sha256()
    started = clock()
    discovered_entries = 1
    bytes_read = 0
    deepest = 0
    stack: list[tuple[Path, str, int]] = [(path, ".", 0)]

    while stack:
        elapsed = _elapsed(clock, started)
        _check_duration(
            limits,
            elapsed=elapsed,
            entries=discovered_entries,
            bytes_read=bytes_read,
            depth=deepest,
        )
        current, relative, depth = stack.pop()
        deepest = max(deepest, depth)
        if depth > limits.max_depth:
            raise _limit_error(
                code="QUARANTINE_INTEGRITY_DEPTH_LIMIT",
                message="Quarantine payload depth exceeded the configured limit.",
                entries=discovered_entries,
                bytes_read=bytes_read,
                depth=depth,
                elapsed=elapsed,
            )

        metadata = os.lstat(current)
        mode = metadata.st_mode

        if stat.S_ISLNK(mode) or _is_reparse_point(metadata):
            _update_token(hasher, b"link", relative.encode("utf-8"))
            target = os.readlink(current).encode("utf-8")
            bytes_read += len(target)
            _check_bytes(
                limits,
                entries=discovered_entries,
                bytes_read=bytes_read,
                depth=depth,
                elapsed=_elapsed(clock, started),
            )
            _update_token(hasher, b"target", target)
            continue

        if stat.S_ISREG(mode):
            _update_token(hasher, b"file", relative.encode("utf-8"))
            with current.open("rb") as handle:
                while chunk := handle.read(_CHUNK_SIZE):
                    bytes_read += len(chunk)
                    elapsed = _elapsed(clock, started)
                    _check_duration(
                        limits,
                        elapsed=elapsed,
                        entries=discovered_entries,
                        bytes_read=bytes_read,
                        depth=depth,
                    )
                    _check_bytes(
                        limits,
                        entries=discovered_entries,
                        bytes_read=bytes_read,
                        depth=depth,
                        elapsed=elapsed,
                    )
                    _update_token(hasher, b"chunk", chunk)
            continue

        if stat.S_ISDIR(mode):
            _update_token(hasher, b"directory", relative.encode("utf-8"))
            children: list[tuple[str, str]] = []
            with os.scandir(current) as scanner:
                for entry in scanner:
                    elapsed = _elapsed(clock, started)
                    _check_duration(
                        limits,
                        elapsed=elapsed,
                        entries=discovered_entries,
                        bytes_read=bytes_read,
                        depth=depth,
                    )
                    discovered_entries += 1
                    child_depth = depth + 1
                    if discovered_entries > limits.max_entries:
                        raise _limit_error(
                            code="QUARANTINE_INTEGRITY_ENTRY_LIMIT",
                            message="Quarantine payload entries exceeded the configured limit.",
                            entries=discovered_entries,
                            bytes_read=bytes_read,
                            depth=child_depth,
                            elapsed=elapsed,
                        )
                    if child_depth > limits.max_depth:
                        raise _limit_error(
                            code="QUARANTINE_INTEGRITY_DEPTH_LIMIT",
                            message="Quarantine payload depth exceeded the configured limit.",
                            entries=discovered_entries,
                            bytes_read=bytes_read,
                            depth=child_depth,
                            elapsed=elapsed,
                        )
                    children.append((entry.name, entry.path))
            children.sort(key=lambda item: item[0])
            for name, child_path in reversed(children):
                child_relative = name if relative == "." else f"{relative}/{name}"
                stack.append((Path(child_path), child_relative, depth + 1))
            continue

        raise ValueError(f"Unsupported quarantine payload type: {current}")

    return hasher.hexdigest()


def _elapsed(clock: Callable[[], float], started: float) -> float:
    return max(0.0, clock() - started)


def _check_duration(
    limits: PayloadHashLimits,
    *,
    elapsed: float,
    entries: int,
    bytes_read: int,
    depth: int,
) -> None:
    if elapsed > limits.max_duration_seconds:
        raise _limit_error(
            code="QUARANTINE_INTEGRITY_DURATION_LIMIT",
            message="Quarantine payload hashing exceeded the configured duration.",
            entries=entries,
            bytes_read=bytes_read,
            depth=depth,
            elapsed=elapsed,
        )


def _check_bytes(
    limits: PayloadHashLimits,
    *,
    entries: int,
    bytes_read: int,
    depth: int,
    elapsed: float,
) -> None:
    if bytes_read > limits.max_bytes:
        raise _limit_error(
            code="QUARANTINE_INTEGRITY_BYTE_LIMIT",
            message="Quarantine payload bytes exceeded the configured limit.",
            entries=entries,
            bytes_read=bytes_read,
            depth=depth,
            elapsed=elapsed,
        )


def _limit_error(
    *,
    code: str,
    message: str,
    entries: int,
    bytes_read: int,
    depth: int,
    elapsed: float,
) -> PayloadHashLimitError:
    return PayloadHashLimitError(
        code=code,
        message=message,
        entries=entries,
        bytes_read=bytes_read,
        depth=depth,
        elapsed_seconds=elapsed,
    )


def _update_token(hasher: Any, label: bytes, payload: bytes) -> None:
    hasher.update(len(label).to_bytes(4, byteorder="big"))
    hasher.update(label)
    hasher.update(len(payload).to_bytes(8, byteorder="big"))
    hasher.update(payload)


def _is_reparse_point(metadata: os.stat_result) -> bool:
    attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(attribute and file_attributes & attribute)


__all__ = [
    "DEFAULT_PAYLOAD_HASH_LIMITS",
    "PayloadHashLimitError",
    "PayloadHashLimits",
    "metadata_bytes",
    "payload_sha256",
    "sign_metadata",
    "verify_metadata",
]
