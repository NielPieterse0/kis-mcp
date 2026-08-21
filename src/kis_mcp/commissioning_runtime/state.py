from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_CHECKPOINT_KEYS = frozenset(
    {"schema_version", "repository", "initialized_at", "checkpoint_at"}
)


class CommissioningStateError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class CheckpointState:
    repository: str
    initialized_at: datetime
    checkpoint_at: datetime


@dataclass(frozen=True, slots=True)
class ReceiptReference:
    receipt_id: str
    path: str
    sha256: str


class ExecutionResult(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ExecutionState:
    commissioning_key: str
    contract_fingerprint: str
    attempt: int
    phase: str
    result: ExecutionResult
    receipt_id: str | None
    updated_at: datetime


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise CommissioningStateError("timestamp_invalid", "timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _parse_iso(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise CommissioningStateError("checkpoint_invalid", f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CommissioningStateError("checkpoint_invalid", f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise CommissioningStateError("checkpoint_invalid", f"{label} must be timezone-aware")
    return parsed.astimezone(UTC)


def _repository_key(repository: str) -> str:
    if not isinstance(repository, str) or _REPOSITORY.fullmatch(repository.strip()) is None:
        raise CommissioningStateError("repository_invalid", "repository must be owner/name")
    return hashlib.sha256(repository.strip().casefold().encode("utf-8")).hexdigest()[:24]


def _execution_key(commissioning_key: str) -> str:
    if not isinstance(commissioning_key, str) or not commissioning_key.startswith("commission:"):
        raise CommissioningStateError("execution_key_invalid", "commissioning key is invalid")
    if len(commissioning_key) > 512:
        raise CommissioningStateError("execution_key_invalid", "commissioning key is too long")
    return hashlib.sha256(commissioning_key.encode("utf-8")).hexdigest()


class CommissioningStateStore:
    def __init__(self, root: Path, *, retention: int) -> None:
        if retention <= 0:
            raise ValueError("retention must be positive")
        self.root = root
        self.retention = retention

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_bytes(_canonical(dict(payload)) + b"\n")
        os.replace(temporary, path)

    def checkpoint_path(self, repository: str) -> Path:
        return self.root / "checkpoints" / f"{_repository_key(repository)}.json"

    def execution_path(self, commissioning_key: str) -> Path:
        return self.root / "executions" / f"{_execution_key(commissioning_key)}.json"

    @staticmethod
    def _execution_payload(state: ExecutionState) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "commissioning_key": state.commissioning_key,
            "contract_fingerprint": state.contract_fingerprint,
            "attempt": state.attempt,
            "phase": state.phase,
            "result": state.result.value,
            "receipt_id": state.receipt_id,
            "updated_at": _iso(state.updated_at),
        }

    def _checkpoint_payload(
        self, repository: str, initialized_at: datetime, checkpoint_at: datetime
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "repository": repository,
            "initialized_at": _iso(initialized_at),
            "checkpoint_at": _iso(checkpoint_at),
        }

    def load_execution_state(self, commissioning_key: str) -> ExecutionState | None:
        path = self.execution_path(commissioning_key)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as exc:
            raise CommissioningStateError("execution_state_invalid", "execution state is not valid JSON") from exc
        expected = {
            "schema_version", "commissioning_key", "contract_fingerprint", "attempt",
            "phase", "result", "receipt_id", "updated_at",
        }
        if not isinstance(value, Mapping) or set(value) != expected or value.get("schema_version") != 1:
            raise CommissioningStateError("execution_state_invalid", "execution state shape is invalid")
        if value.get("commissioning_key") != commissioning_key:
            raise CommissioningStateError("execution_state_invalid", "commissioning key mismatches execution path")
        fingerprint = value.get("contract_fingerprint")
        attempt = value.get("attempt")
        phase = value.get("phase")
        receipt_id = value.get("receipt_id")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise CommissioningStateError("execution_state_invalid", "contract fingerprint is invalid")
        if type(attempt) is not int or attempt <= 0 or not isinstance(phase, str) or not phase:
            raise CommissioningStateError("execution_state_invalid", "execution attempt or phase is invalid")
        if receipt_id is not None and not isinstance(receipt_id, str):
            raise CommissioningStateError("execution_state_invalid", "receipt id is invalid")
        try:
            result = ExecutionResult(str(value.get("result")))
            updated_at = datetime.fromisoformat(str(value.get("updated_at"))).astimezone(UTC)
        except (ValueError, TypeError) as exc:
            raise CommissioningStateError("execution_state_invalid", "execution result/timestamp is invalid") from exc
        return ExecutionState(commissioning_key, fingerprint, attempt, phase, result, receipt_id, updated_at)

    def begin_execution(
        self,
        commissioning_key: str,
        contract_fingerprint: str,
        now: datetime,
        *,
        retry: bool = False,
    ) -> ExecutionState:
        if len(contract_fingerprint) != 64 or any(char not in "0123456789abcdef" for char in contract_fingerprint):
            raise CommissioningStateError("execution_contract_invalid", "contract fingerprint must be lowercase sha256")
        existing = self.load_execution_state(commissioning_key)
        if existing is not None:
            if existing.contract_fingerprint != contract_fingerprint:
                raise CommissioningStateError("execution_contract_mismatch", "frozen commissioning contract changed")
            if existing.phase == "terminal" and existing.result is ExecutionResult.PASSED:
                return existing
            if existing.phase == "terminal" and existing.result in {ExecutionResult.FAILED, ExecutionResult.BLOCKED}:
                if not retry:
                    return existing
                state = ExecutionState(
                    commissioning_key, contract_fingerprint, existing.attempt + 1,
                    "initialized", ExecutionResult.PENDING, None, now.astimezone(UTC),
                )
                self._write_json(self.execution_path(commissioning_key), self._execution_payload(state))
                return state
            return existing
        state = ExecutionState(
            commissioning_key, contract_fingerprint, 1,
            "initialized", ExecutionResult.PENDING, None, now.astimezone(UTC),
        )
        self._write_json(self.execution_path(commissioning_key), self._execution_payload(state))
        return state

    def update_execution(
        self,
        state: ExecutionState,
        *,
        phase: str,
        result: ExecutionResult,
        receipt_id: str | None,
        updated_at: datetime,
    ) -> ExecutionState:
        current = self.load_execution_state(state.commissioning_key)
        if current != state:
            raise CommissioningStateError("execution_state_conflict", "execution state changed before update")
        if not isinstance(phase, str) or not phase.strip():
            raise CommissioningStateError("execution_state_invalid", "phase must be non-empty")
        updated = ExecutionState(
            state.commissioning_key, state.contract_fingerprint, state.attempt,
            phase.strip(), result, receipt_id, updated_at.astimezone(UTC),
        )
        self._write_json(self.execution_path(state.commissioning_key), self._execution_payload(updated))
        return updated

    def load_checkpoint_state(self, repository: str) -> CheckpointState | None:
        path = self.checkpoint_path(repository)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as exc:
            raise CommissioningStateError("checkpoint_invalid", "checkpoint is not valid JSON") from exc
        if not isinstance(value, Mapping) or set(value) != _CHECKPOINT_KEYS:
            raise CommissioningStateError("checkpoint_invalid", "checkpoint shape is invalid")
        if value.get("schema_version") != 1:
            raise CommissioningStateError("checkpoint_invalid", "checkpoint schema_version must be 1")
        if str(value.get("repository", "")).casefold() != repository.casefold():
            raise CommissioningStateError("checkpoint_invalid", "checkpoint repository identity mismatches")
        return CheckpointState(
            repository=repository,
            initialized_at=_parse_iso(value.get("initialized_at"), "initialized_at"),
            checkpoint_at=_parse_iso(value.get("checkpoint_at"), "checkpoint_at"),
        )

    def load_checkpoint(self, repository: str) -> datetime | None:
        state = self.load_checkpoint_state(repository)
        return None if state is None else state.checkpoint_at

    def initialize_checkpoint(
        self, repository: str, now: datetime
    ) -> tuple[datetime, bool]:
        existing = self.load_checkpoint(repository)
        if existing is not None:
            return existing, False
        payload = self._checkpoint_payload(repository, now, now)
        self._write_json(self.checkpoint_path(repository), payload)
        return now.astimezone(UTC), True

    def advance_checkpoint(self, repository: str, checkpoint_at: datetime) -> datetime:
        state = self.load_checkpoint_state(repository)
        if state is None:
            raise CommissioningStateError(
                "checkpoint_invalid", "cannot advance unavailable checkpoint"
            )
        selected = checkpoint_at.astimezone(UTC)
        if selected < state.checkpoint_at:
            raise CommissioningStateError("checkpoint_invalid", "checkpoint cannot move backwards")
        self._write_json(
            self.checkpoint_path(repository),
            self._checkpoint_payload(repository, state.initialized_at, selected),
        )
        return selected

    def recover_checkpoint(self, repository: str, now: datetime) -> datetime:
        path = self.checkpoint_path(repository)
        if path.exists():
            stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            retained = path.with_name(f"{path.stem}.corrupt.{stamp}.json")
            path.replace(retained)
            corrupt = sorted(path.parent.glob(f"{path.stem}.corrupt.*.json"))
            for stale in corrupt[: max(0, len(corrupt) - self.retention)]:
                stale.unlink(missing_ok=True)
        payload = self._checkpoint_payload(repository, now, now)
        self._write_json(path, payload)
        return now.astimezone(UTC)

    def _trim_receipts(self) -> None:
        files = sorted((self.root / "receipts").glob("*.json"))
        for path in files[: max(0, len(files) - self.retention)]:
            path.unlink(missing_ok=True)

    def persist_receipt(
        self, payload: Mapping[str, Any], occurred_at: datetime
    ) -> ReceiptReference:
        digest = hashlib.sha256(_canonical(dict(payload))).hexdigest()
        directory = self.root / "receipts"
        matches = sorted(directory.glob(f"*_{digest}.json"))
        if matches:
            return ReceiptReference(
                receipt_id=f"post-merge-commissioning:{digest}",
                path=str(matches[-1]),
                sha256=digest,
            )
        directory.mkdir(parents=True, exist_ok=True)
        stamp = occurred_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        path = directory / f"{stamp}_{digest}.json"
        self._write_json(path, dict(payload))
        self._trim_receipts()
        return ReceiptReference(
            receipt_id=f"post-merge-commissioning:{digest}",
            path=str(path),
            sha256=digest,
        )

    def load_receipt(self, receipt_id: str) -> dict[str, Any]:
        prefix = "post-merge-commissioning:"
        if not isinstance(receipt_id, str) or not receipt_id.startswith(prefix):
            raise ValueError("receipt_id is invalid")
        digest = receipt_id.removeprefix(prefix)
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("receipt_id digest is invalid")
        matches = list((self.root / "receipts").glob(f"*_{digest}.json"))
        if len(matches) != 1:
            raise KeyError(receipt_id)
        value = json.loads(matches[0].read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise CommissioningStateError("receipt_invalid", "receipt must be an object")
        return value

    def latest_receipt(self, repository: str) -> tuple[str, dict[str, Any]] | None:
        prefix = "post-merge-commissioning:"
        files = sorted((self.root / "receipts").glob("*.json"), reverse=True)
        for path in files:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise CommissioningStateError(
                    "receipt_invalid", "persisted receipt is not valid JSON"
                ) from exc
            if not isinstance(value, dict):
                raise CommissioningStateError("receipt_invalid", "receipt must be an object")
            if str(value.get("repository", "")).casefold() != repository.casefold():
                continue
            digest = path.stem.rsplit("_", 1)[-1]
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise CommissioningStateError("receipt_invalid", "receipt filename is invalid")
            return prefix + digest, value
        return None


__all__ = [
    "CheckpointState",
    "CommissioningStateError",
    "CommissioningStateStore",
    "ExecutionResult",
    "ExecutionState",
    "ReceiptReference",
]
