from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kis_mcp.housekeeping import RunnerKind


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def plan_fingerprint(receipt: Mapping[str, Any]) -> str:
    trigger = receipt.get("trigger")
    if not isinstance(trigger, Mapping):
        raise ValueError("receipt trigger must be an object")
    runner = trigger.get("runner")
    if not isinstance(runner, str) or not runner:
        raise ValueError("receipt trigger runner is required")
    actions = receipt.get("actions")
    if not isinstance(actions, list):
        raise ValueError("receipt actions must be an array")
    plan = {
        "runner": runner,
        "project_id": receipt.get("project_id"),
        "repository": receipt.get("repository"),
        "actions": [
            {
                "action_id": item.get("action_id"),
                "operation": item.get("operation"),
                "arguments": item.get("arguments"),
                "safe_to_apply": item.get("safe_to_apply"),
            }
            for item in actions
            if isinstance(item, Mapping)
        ],
    }
    return hashlib.sha256(_canonical(plan)).hexdigest()


def derive_apply_idempotency_key(receipt: Mapping[str, Any]) -> str:
    trigger = receipt.get("trigger")
    if not isinstance(trigger, Mapping) or not isinstance(trigger.get("runner"), str):
        raise ValueError("receipt trigger runner is required")
    fingerprint = plan_fingerprint(receipt)
    return f"housekeeping:{trigger['runner']}:{fingerprint}"


@dataclass(frozen=True, slots=True)
class ReceiptReference:
    receipt_id: str
    path: str
    sha256: str


class HousekeepingStateStore:
    def __init__(self, root: Path, *, retention: int) -> None:
        if retention <= 0:
            raise ValueError("retention must be positive")
        self.root = root
        self.retention = retention

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if value.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_bytes(_canonical(dict(payload)) + b"\n")
        os.replace(temporary, path)

    def _receipt_directory(self, runner: RunnerKind) -> Path:
        return self.root / "receipts" / runner.value

    def _trim(self, runner: RunnerKind) -> None:
        files = sorted(self._receipt_directory(runner).glob("*.json"))
        for path in files[: max(0, len(files) - self.retention)]:
            path.unlink(missing_ok=True)

    def persist_receipt(
        self,
        runner: RunnerKind,
        kind: str,
        payload: Mapping[str, Any],
        occurred_at: datetime,
    ) -> ReceiptReference:
        timestamp = self._timestamp(occurred_at)
        digest = hashlib.sha256(_canonical(dict(payload))).hexdigest()
        directory = self._receipt_directory(runner)
        existing = sorted(directory.glob(f"*_{digest}.json"))
        if existing:
            return ReceiptReference(
                receipt_id=f"{runner.value}:{digest}",
                path=str(existing[-1]),
                sha256=digest,
            )
        filename = f"{timestamp}_{kind}_{digest}.json"
        path = directory / filename
        self._write_json(path, dict(payload))
        self._trim(runner)
        return ReceiptReference(
            receipt_id=f"{runner.value}:{digest}",
            path=str(path),
            sha256=digest,
        )

    def persist_failure(
        self,
        runner: RunnerKind,
        error_type: str,
        occurred_at: datetime,
    ) -> ReceiptReference:
        payload = {
            "schema_version": 1,
            "runner": runner.value,
            "kind": "failure",
            "occurred_at": occurred_at.isoformat(),
            "error_type": error_type,
        }
        return self.persist_receipt(runner, "failure", payload, occurred_at)

    @staticmethod
    def _receipt_parts(receipt_id: str) -> tuple[RunnerKind, str]:
        try:
            runner_value, digest = receipt_id.split(":", 1)
            runner = RunnerKind(runner_value)
        except (ValueError, TypeError) as exc:
            raise ValueError("receipt_id is invalid") from exc
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("receipt_id digest is invalid")
        return runner, digest

    def load_receipt(self, receipt_id: str) -> dict[str, Any]:
        runner, digest = self._receipt_parts(receipt_id)
        matches = list(self._receipt_directory(runner).glob(f"*_{digest}.json"))
        if len(matches) != 1:
            raise KeyError(receipt_id)
        value = json.loads(matches[0].read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError("persisted housekeeping receipt is not an object")
        return value

    def persist_status(self, runner: RunnerKind, payload: Mapping[str, Any]) -> None:
        self._write_json(self.root / "status" / f"{runner.value}.json", dict(payload))

    def load_status(self, runner: RunnerKind) -> dict[str, Any]:
        path = self.root / "status" / f"{runner.value}.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        if not isinstance(value, dict):
            raise RuntimeError("persisted housekeeping status is not an object")
        return value


__all__ = [
    "HousekeepingStateStore",
    "ReceiptReference",
    "derive_apply_idempotency_key",
    "plan_fingerprint",
]
