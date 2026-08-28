from __future__ import annotations

import hashlib
import json
import msvcrt
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import BinaryIO

from .contract import SPEC_BY_CLASS, StateOwnershipClass

_IDEMPOTENCY_SCHEMA_VERSION = 2
_IDEMPOTENCY_STATE_KEY = "state-cleanup-idempotency"


class StateCleanupIdempotencyStore:
    """Own durable replay coordination for stale-state cleanup."""

    def __init__(self, *, state_root: Path) -> None:
        spec = SPEC_BY_CLASS[StateOwnershipClass.GLOBAL_AUTHORITY]
        relative = spec.namespace_template.format(state_key=_IDEMPOTENCY_STATE_KEY)
        self.root = state_root.joinpath(*PureWindowsPath(relative).parts)

    def binding_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def has_binding(self, key: str) -> bool:
        return self.binding_path(key).exists()

    def lock_path(self, key: str) -> Path:
        return self.binding_path(key).with_suffix(".lock")

    def acquire_lock(self, key: str) -> BinaryIO:
        self.root.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path(key).open("a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return handle
        except OSError as exc:
            handle.close()
            raise ValueError("idempotency operation is already reserved") from exc

    @staticmethod
    def release_lock(handle: BinaryIO) -> None:
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            handle.close()

    def reserve(
        self,
        key: str,
        target_key: str,
        operation_id: str,
    ) -> tuple[bool, dict[str, object]]:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.binding_path(key)
        payload = {
            "schema_version": _IDEMPOTENCY_SCHEMA_VERSION,
            "target": target_key,
            "quarantine_operation_id": operation_id,
            "reserved_at": datetime.now(UTC).isoformat(),
            "result": None,
        }
        try:
            self._write(path, payload, replace=False)
            return True, payload
        except FileExistsError:
            return False, self.read(key)

    def read(self, key: str) -> dict[str, object]:
        path = self.binding_path(key)
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("idempotency binding is unreadable") from exc
        if not isinstance(existing, dict) or existing.get("schema_version") != _IDEMPOTENCY_SCHEMA_VERSION:
            raise ValueError("idempotency binding is unsupported")
        return existing

    def complete(self, key: str, target_key: str, result: Mapping[str, object]) -> None:
        operation_id = result.get("quarantine_operation_id")
        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("idempotency result is missing quarantine operation identity")
        payload = {
            "schema_version": _IDEMPOTENCY_SCHEMA_VERSION,
            "target": target_key,
            "quarantine_operation_id": operation_id,
            "reserved_at": datetime.now(UTC).isoformat(),
            "result": dict(result),
        }
        self._write(self.binding_path(key), payload)

    def rewrite_reservation(self, key: str, payload: Mapping[str, object]) -> None:
        self._write(self.binding_path(key), payload)

    def release(self, key: str) -> None:
        try:
            self.binding_path(key).unlink()
        except FileNotFoundError:
            pass

    def _write(
        self,
        path: Path,
        payload: Mapping[str, object],
        *,
        replace: bool = True,
    ) -> None:
        temp_path = path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(dict(payload), sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._replace_write_through(temp_path, path, replace=replace)

    @staticmethod
    def _replace_write_through(source: Path, destination: Path, *, replace: bool = True) -> None:
        if os.name != "nt":
            if replace:
                os.replace(source, destination)
            else:
                os.link(source, destination)
                source.unlink()
            return
        import ctypes

        move_file_ex = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
        move_file_ex.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        move_file_ex.restype = ctypes.c_int
        flags = 0x8 | (0x1 if replace else 0)
        if move_file_ex(str(source), str(destination), flags):
            return
        error = ctypes.get_last_error()
        if not replace and error in {80, 183}:
            raise FileExistsError(error, "idempotency binding already exists", str(destination))
        raise OSError(error, "write-through file replacement failed", str(destination))


class StateCleanupAdmissionGuard:
    """Share the repository change-admission lock during stale source cleanup."""

    def __init__(
        self,
        *,
        state_root: Path,
        project_roots: Mapping[str, Path],
        fallback_project_root: Path | None = None,
    ) -> None:
        self.state_root = state_root
        self.project_roots = {str(key): Path(value) for key, value in project_roots.items()}
        self.fallback_project_root = fallback_project_root
        self._held: set[str] = set()

    def _lock_path(self, project_id: str) -> Path:
        root = self.project_roots.get(project_id)
        if root is None and self.fallback_project_root is not None:
            root = self.fallback_project_root / project_id
        if root is None:
            raise ValueError("cleanup project is not registered")
        repository_key = hashlib.sha256(str(root.resolve()).casefold().encode("utf-8")).hexdigest()[:24]
        return self.state_root / "change-governance" / f"{repository_key}.lock"

    @contextmanager
    def hold(self, project_id: str) -> Iterator[None]:
        path = self._lock_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as stream:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            self._held.add(project_id)
            try:
                yield
            finally:
                self._held.discard(project_id)
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)

    def is_held(self, project_id: str) -> bool:
        return project_id in self._held


__all__ = ["StateCleanupAdmissionGuard", "StateCleanupIdempotencyStore"]
