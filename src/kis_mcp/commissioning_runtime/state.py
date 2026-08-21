from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
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

    def _checkpoint_payload(
        self, repository: str, initialized_at: datetime, checkpoint_at: datetime
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "repository": repository,
            "initialized_at": _iso(initialized_at),
            "checkpoint_at": _iso(checkpoint_at),
        }

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
    "ReceiptReference",
]
