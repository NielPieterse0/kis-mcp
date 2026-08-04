from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_CHUNK_SIZE = 1024 * 1024


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


def payload_sha256(path: Path) -> str:
    """Hash one file, symlink, or directory tree without following symlinks."""

    hasher = hashlib.sha256()
    _hash_entry(hasher, path, relative=".")
    return hasher.hexdigest()


def _hash_entry(hasher: Any, path: Path, *, relative: str) -> None:
    metadata = os.lstat(path)
    mode = metadata.st_mode

    if stat.S_ISLNK(mode) or _is_reparse_point(metadata):
        _update_token(hasher, b"link", relative.encode("utf-8"))
        _update_token(hasher, b"target", os.readlink(path).encode("utf-8"))
        return

    if stat.S_ISREG(mode):
        _update_token(hasher, b"file", relative.encode("utf-8"))
        with path.open("rb") as handle:
            while chunk := handle.read(_CHUNK_SIZE):
                _update_token(hasher, b"chunk", chunk)
        return

    if stat.S_ISDIR(mode):
        _update_token(hasher, b"directory", relative.encode("utf-8"))
        with os.scandir(path) as scanner:
            entries = sorted(scanner, key=lambda entry: entry.name)
        for entry in entries:
            child_relative = (
                entry.name if relative == "." else f"{relative}/{entry.name}"
            )
            _hash_entry(hasher, Path(entry.path), relative=child_relative)
        return

    raise ValueError(f"Unsupported quarantine payload type: {path}")


def _update_token(hasher: Any, label: bytes, payload: bytes) -> None:
    hasher.update(len(label).to_bytes(4, byteorder="big"))
    hasher.update(label)
    hasher.update(len(payload).to_bytes(8, byteorder="big"))
    hasher.update(payload)


def _is_reparse_point(metadata: os.stat_result) -> bool:
    attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(attribute and file_attributes & attribute)
