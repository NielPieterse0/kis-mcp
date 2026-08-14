from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from kis_mcp.evidence import (
    EvidenceConflictError,
    EvidenceCorruptionError,
    EvidenceStore,
)

from .contracts import ProjectDefinition

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OPERATION_NAME = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
_SCHEMA_VERSION = 1
_STATE_ARTIFACT = "state.json"
_MAX_OPERATIONS = 128


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_hash(value: str, label: str) -> str:
    normalized = str(value).strip().casefold()
    if _SHA256.fullmatch(normalized) is None:
        raise ValueError(f"{label} must be a SHA-256 value")
    return normalized


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _normalized_windows_path(value: str) -> str:
    return str(PureWindowsPath(_required_text(value, "path"))).casefold()


@dataclass(frozen=True, slots=True)
class RecoveryIdentity:
    project_id: str
    registered_root: str
    worktree_root: str
    git_revision: str
    git_status: str
    source_fingerprint: str
    settings_fingerprint: str
    provider_fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "project_id", _required_text(self.project_id, "project_id")
        )
        object.__setattr__(
            self, "registered_root", _normalized_windows_path(self.registered_root)
        )
        object.__setattr__(
            self, "worktree_root", _normalized_windows_path(self.worktree_root)
        )
        object.__setattr__(
            self, "git_revision", _required_text(self.git_revision, "git_revision")
        )
        object.__setattr__(
            self, "git_status", _required_text(self.git_status, "git_status")
        )
        object.__setattr__(
            self,
            "source_fingerprint",
            _require_hash(self.source_fingerprint, "source_fingerprint"),
        )
        object.__setattr__(
            self,
            "settings_fingerprint",
            _require_hash(self.settings_fingerprint, "settings_fingerprint"),
        )
        object.__setattr__(
            self,
            "provider_fingerprint",
            _require_hash(self.provider_fingerprint, "provider_fingerprint"),
        )

    @classmethod
    def for_project(
        cls,
        project: ProjectDefinition,
        *,
        worktree_root: str,
        git_revision: str,
        git_status: str,
        source_fingerprint: str,
        settings_fingerprint: str,
        provider_fingerprint: str,
    ) -> RecoveryIdentity:
        return cls(
            project_id=project.project_id,
            registered_root=_normalized_windows_path(project.local_root),
            worktree_root=_normalized_windows_path(worktree_root),
            git_revision=_required_text(git_revision, "git_revision"),
            git_status=_required_text(git_status, "git_status"),
            source_fingerprint=_require_hash(source_fingerprint, "source_fingerprint"),
            settings_fingerprint=_require_hash(
                settings_fingerprint, "settings_fingerprint"
            ),
            provider_fingerprint=_require_hash(
                provider_fingerprint, "provider_fingerprint"
            ),
        )

    @property
    def worktree_fingerprint(self) -> str:
        return _digest_text(self.worktree_root)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(_canonical_json(self.to_json_dict())).hexdigest()

    def to_json_dict(self) -> dict[str, str | int]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "project_id": self.project_id,
            "registered_root": self.registered_root,
            "worktree_root": self.worktree_root,
            "worktree_fingerprint": self.worktree_fingerprint,
            "git_revision": self.git_revision,
            "git_status": self.git_status,
            "source_fingerprint": self.source_fingerprint,
            "settings_fingerprint": self.settings_fingerprint,
            "provider_fingerprint": self.provider_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class RecoverySnapshot:
    status: str
    namespace: str
    generation_id: str | None = None
    central_generation_id: str | None = None
    recovered_pointer: str | None = None
    operation_name: str | None = None
    operation_state: str | None = None
    request_fingerprint: str | None = None
    result_fingerprint: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "status": self.status,
            "namespace": self.namespace,
            "generation_id": self.generation_id,
            "central_generation_id": self.central_generation_id,
            "recovered_pointer": self.recovered_pointer,
            "operation_name": self.operation_name,
            "operation_state": self.operation_state,
            "request_fingerprint": self.request_fingerprint,
            "result_fingerprint": self.result_fingerprint,
        }


class ProjectRecoveryCapsule:
    """Disposable repo-local checkpoint layer backed by immutable EvidenceStore generations."""

    def __init__(
        self,
        project: ProjectDefinition,
        *,
        max_file_bytes: int = 65_536,
        max_total_bytes: int = 262_144,
    ) -> None:
        self.project = project
        self._registered_root = Path(project.local_root).absolute()
        self._capsule_path = self._registered_root / ".temp" / "kis"
        self.root = self._verified_root()
        self._store = EvidenceStore(
            self.root,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
        )

    @staticmethod
    def _namespace(identity: RecoveryIdentity) -> str:
        return f"sessions/{identity.worktree_fingerprint[:24]}"

    def _verified_root(self) -> Path:
        resolved = self._capsule_path.resolve(strict=False)
        try:
            resolved.relative_to(self._registered_root)
        except ValueError as exc:
            raise EvidenceConflictError(
                "recovery capsule path escapes the registered project root"
            ) from exc
        return resolved

    def _ensure_local_ignore(self) -> None:
        if self._verified_root() != self.root:
            raise EvidenceConflictError(
                "recovery capsule path changed after initialization"
            )
        self.root.mkdir(parents=True, exist_ok=True)
        marker = self.root / ".gitignore"
        try:
            descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        except FileExistsError:
            try:
                lines = marker.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError) as exc:
                raise EvidenceConflictError(
                    "recovery capsule .gitignore cannot be verified"
                ) from exc
            if "*" not in {line.strip() for line in lines}:
                raise EvidenceConflictError(
                    "recovery capsule .gitignore must contain a '*' ignore rule"
                )
            return
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(b"*\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _validate_identity(self, identity: RecoveryIdentity) -> None:
        if identity.project_id != self.project.project_id:
            raise ValueError(
                "recovery identity project_id does not match registered project"
            )
        if identity.registered_root != _normalized_windows_path(
            self.project.local_root
        ):
            raise ValueError(
                "recovery identity registered_root does not match registered project"
            )

    @staticmethod
    def _empty_state(central_generation_id: str | None = None) -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "central_generation_id": central_generation_id,
            "next_sequence": 1,
            "operations": {},
        }

    @staticmethod
    def _validate_state(value: Any) -> dict[str, Any]:
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != _SCHEMA_VERSION
        ):
            raise EvidenceCorruptionError("recovery capsule state schema is corrupt")
        central = value.get("central_generation_id")
        if central is not None:
            _require_hash(str(central), "central_generation_id")
        next_sequence = value.get("next_sequence")
        if (
            isinstance(next_sequence, bool)
            or not isinstance(next_sequence, int)
            or next_sequence < 1
        ):
            raise EvidenceCorruptionError("recovery capsule sequence is corrupt")
        operations = value.get("operations")
        if not isinstance(operations, dict) or len(operations) > _MAX_OPERATIONS:
            raise EvidenceCorruptionError("recovery capsule operations are corrupt")
        for key, operation in operations.items():
            if _SHA256.fullmatch(str(key)) is None or not isinstance(operation, dict):
                raise EvidenceCorruptionError(
                    "recovery capsule operation entry is corrupt"
                )
            name = str(operation.get("operation_name", ""))
            request = str(operation.get("request_fingerprint", ""))
            state = operation.get("state")
            sequence = operation.get("sequence")
            result = operation.get("result_fingerprint")
            if (
                _OPERATION_NAME.fullmatch(name) is None
                or _SHA256.fullmatch(request) is None
            ):
                raise EvidenceCorruptionError(
                    "recovery capsule operation identity is corrupt"
                )
            if (
                isinstance(sequence, bool)
                or not isinstance(sequence, int)
                or sequence < 1
            ):
                raise EvidenceCorruptionError(
                    "recovery capsule operation sequence is corrupt"
                )
            if state not in {"started", "completed"}:
                raise EvidenceCorruptionError(
                    "recovery capsule operation state is corrupt"
                )
            if state == "started" and result is not None:
                raise EvidenceCorruptionError("started recovery operation has a result")
            if state == "completed" and _SHA256.fullmatch(str(result)) is None:
                raise EvidenceCorruptionError(
                    "completed recovery operation result is corrupt"
                )
        return value

    def _load(
        self, identity: RecoveryIdentity
    ) -> tuple[RecoverySnapshot, dict[str, Any]]:
        self._validate_identity(identity)
        namespace = self._namespace(identity)
        try:
            generation = self._store.read_current_generation(namespace)
        except FileNotFoundError:
            return RecoverySnapshot(
                status="missing", namespace=namespace
            ), self._empty_state()
        except EvidenceCorruptionError:
            recovered = self._store.retain_corrupt_current_pointer(namespace)
            return (
                RecoverySnapshot(
                    status="corrupt",
                    namespace=namespace,
                    recovered_pointer=recovered,
                ),
                self._empty_state(),
            )

        if generation.metadata.get("identity_fingerprint") != identity.fingerprint:
            return (
                RecoverySnapshot(
                    status="stale",
                    namespace=namespace,
                    generation_id=generation.generation_id,
                ),
                self._empty_state(),
            )
        try:
            state = self._validate_state(
                json.loads(generation.artifacts[_STATE_ARTIFACT])
            )
        except (
            KeyError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
            EvidenceCorruptionError,
        ):
            recovered = self._store.retain_corrupt_current_pointer(namespace)
            return (
                RecoverySnapshot(
                    status="corrupt", namespace=namespace, recovered_pointer=recovered
                ),
                self._empty_state(),
            )

        return (
            RecoverySnapshot(
                status="current",
                namespace=namespace,
                generation_id=generation.generation_id,
                central_generation_id=state.get("central_generation_id"),
            ),
            state,
        )

    def inspect(self, identity: RecoveryIdentity) -> RecoverySnapshot:
        snapshot, _state = self._load(identity)
        return snapshot

    def _publish(
        self,
        identity: RecoveryIdentity,
        state: dict[str, Any],
        *,
        expected_generation: str | None,
    ) -> RecoverySnapshot:
        namespace = self._namespace(identity)
        self._ensure_local_ignore()
        written = self._store.write_generation(
            namespace,
            metadata={
                "schema_version": _SCHEMA_VERSION,
                "kind": "project-recovery-capsule",
                "identity": identity.to_json_dict(),
                "identity_fingerprint": identity.fingerprint,
            },
            artifacts={_STATE_ARTIFACT: _canonical_json(state)},
            expected_current_generation=expected_generation,
        )
        return RecoverySnapshot(
            status="current",
            namespace=namespace,
            generation_id=written.generation_id,
            central_generation_id=state.get("central_generation_id"),
        )

    def publish_discover_hint(
        self,
        identity: RecoveryIdentity,
        *,
        central_generation_id: str,
    ) -> RecoverySnapshot:
        central_generation_id = _require_hash(
            central_generation_id, "central_generation_id"
        )
        observed, state = self._load(identity)
        state = dict(state)
        state["central_generation_id"] = central_generation_id
        expected = (
            observed.generation_id if observed.status in {"current", "stale"} else None
        )
        return self._publish(identity, state, expected_generation=expected)

    @staticmethod
    def _operation_key(idempotency_key: str) -> str:
        raw = _required_text(idempotency_key, "idempotency_key")
        if len(raw) > 512:
            raise ValueError("idempotency_key must be at most 512 characters")
        return _digest_text(raw)

    @staticmethod
    def _operation_name(operation_name: str) -> str:
        normalized = _required_text(operation_name, "operation_name").casefold()
        if _OPERATION_NAME.fullmatch(normalized) is None:
            raise ValueError("operation_name contains unsupported characters")
        return normalized

    @staticmethod
    def _make_operation_room(operations: dict[str, Any]) -> dict[str, Any]:
        bounded = dict(operations)
        if len(bounded) < _MAX_OPERATIONS:
            return bounded
        completed = sorted(
            (
                (int(operation["sequence"]), key)
                for key, operation in bounded.items()
                if operation.get("state") == "completed"
            ),
            key=lambda item: item[0],
        )
        for _sequence, key in completed:
            bounded.pop(key, None)
            if len(bounded) < _MAX_OPERATIONS:
                return bounded
        raise EvidenceConflictError(
            "recovery operation journal is full of incomplete checkpoints"
        )

    @staticmethod
    def _operation_snapshot(
        base: RecoverySnapshot,
        operation: dict[str, Any],
    ) -> RecoverySnapshot:
        return RecoverySnapshot(
            status=base.status,
            namespace=base.namespace,
            generation_id=base.generation_id,
            central_generation_id=base.central_generation_id,
            recovered_pointer=base.recovered_pointer,
            operation_name=str(operation["operation_name"]),
            operation_state=str(operation["state"]),
            request_fingerprint=str(operation["request_fingerprint"]),
            result_fingerprint=operation.get("result_fingerprint"),
        )

    def begin_operation(
        self,
        identity: RecoveryIdentity,
        *,
        operation_name: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> RecoverySnapshot:
        operation_name = self._operation_name(operation_name)
        operation_key = self._operation_key(idempotency_key)
        request_fingerprint = _require_hash(request_fingerprint, "request_fingerprint")
        observed, state = self._load(identity)
        operations = dict(state.get("operations", {}))
        existing = operations.get(operation_key)
        if existing is not None:
            if (
                existing.get("operation_name") != operation_name
                or existing.get("request_fingerprint") != request_fingerprint
            ):
                raise EvidenceConflictError(
                    "idempotency key already identifies a different recovery operation"
                )
            return self._operation_snapshot(observed, existing)

        operations = self._make_operation_room(operations)
        sequence = int(state.get("next_sequence", 1))
        operation = {
            "operation_name": operation_name,
            "request_fingerprint": request_fingerprint,
            "state": "started",
            "sequence": sequence,
            "result_fingerprint": None,
        }
        operations[operation_key] = operation
        state = dict(state)
        state["next_sequence"] = sequence + 1
        state["operations"] = operations
        expected = (
            observed.generation_id if observed.status in {"current", "stale"} else None
        )
        published = self._publish(identity, state, expected_generation=expected)
        return self._operation_snapshot(published, operation)

    def complete_operation(
        self,
        identity: RecoveryIdentity,
        *,
        operation_name: str,
        idempotency_key: str,
        request_fingerprint: str,
        result_fingerprint: str,
    ) -> RecoverySnapshot:
        operation_name = self._operation_name(operation_name)
        operation_key = self._operation_key(idempotency_key)
        request_fingerprint = _require_hash(request_fingerprint, "request_fingerprint")
        result_fingerprint = _require_hash(result_fingerprint, "result_fingerprint")
        observed, state = self._load(identity)
        if observed.status not in {"current", "stale"}:
            raise EvidenceConflictError(
                "cannot complete an operation without a started checkpoint"
            )
        operations = dict(state.get("operations", {}))
        existing = operations.get(operation_key)
        if existing is None:
            raise EvidenceConflictError(
                "cannot complete an operation without a started checkpoint"
            )
        if (
            existing.get("operation_name") != operation_name
            or existing.get("request_fingerprint") != request_fingerprint
        ):
            raise EvidenceConflictError(
                "idempotency key already identifies a different recovery operation"
            )
        if existing.get("state") == "completed":
            if existing.get("result_fingerprint") != result_fingerprint:
                raise EvidenceConflictError(
                    "completed recovery operation result conflicts"
                )
            return self._operation_snapshot(observed, existing)

        completed = {
            **existing,
            "state": "completed",
            "result_fingerprint": result_fingerprint,
        }
        operations[operation_key] = completed
        state = dict(state)
        state["operations"] = operations
        expected = observed.generation_id
        published = self._publish(identity, state, expected_generation=expected)
        return self._operation_snapshot(published, completed)


__all__ = [
    "ProjectRecoveryCapsule",
    "RecoveryIdentity",
    "RecoverySnapshot",
]
