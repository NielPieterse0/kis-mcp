from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from .settings import ResultBudgetSettings

_GRANT_ID = re.compile(r"^[0-9a-f]{64}$")
_RESULT_URI_TEMPLATE = "kis-result:///{grant_id}"


@dataclass(frozen=True, slots=True)
class StoredResult:
    grant_id: str
    payload_sha256: str
    origin_operation: str
    uri: str
    byte_count: int
    expires_at: int


class ResultResourceStore:
    """Persist bounded dispatcher results behind opaque per-dispatch read grants."""

    def __init__(
        self,
        root: Path,
        settings: ResultBudgetSettings,
        *,
        quarantine_expired: Callable[[str], Any] | None = None,
    ) -> None:
        self.root = Path(root) / "capability-results"
        self.settings = settings
        self._quarantine_expired = quarantine_expired
        self._lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def serialize(value: Any) -> bytes:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")

    def put(self, operation: str, value: Any) -> StoredResult | None:
        payload = self.serialize(value)
        if len(payload) > self.settings.resource_max_bytes:
            return None
        payload_sha256 = hashlib.sha256(payload).hexdigest()
        now = int(time.time())
        expires_at = now + self.settings.resource_ttl_seconds
        with self._lock:
            self._quarantine_expired_entries(now)
            if self._entry_count() >= self.settings.resource_max_entries:
                return None
            grant_id = self._new_grant_id()
            envelope = self.serialize(
                {
                    "schema_version": 1,
                    "grant_id": grant_id,
                    "origin_operation": operation,
                    "payload_sha256": payload_sha256,
                    "created_at": now,
                    "expires_at": expires_at,
                    "payload": value,
                }
            )
            path = self.root / f"{grant_id}.json"
            with path.open("xb") as handle:
                handle.write(envelope)
        return StoredResult(
            grant_id=grant_id,
            payload_sha256=payload_sha256,
            origin_operation=operation,
            uri=f"kis-result:///{grant_id}",
            byte_count=len(payload),
            expires_at=expires_at,
        )

    def read(self, grant_id: str) -> bytes:
        if _GRANT_ID.fullmatch(grant_id) is None:
            raise RuntimeError("RESULT_RESOURCE_ID_INVALID")
        with self._lock:
            path = self.root / f"{grant_id}.json"
            if not path.is_file():
                raise RuntimeError("RESULT_RESOURCE_EXPIRED_OR_UNKNOWN")
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise RuntimeError("RESULT_RESOURCE_CORRUPT") from exc
            if (
                not isinstance(envelope, dict)
                or envelope.get("schema_version") != 1
                or envelope.get("grant_id") != grant_id
                or not isinstance(envelope.get("origin_operation"), str)
                or "payload" not in envelope
            ):
                raise RuntimeError("RESULT_RESOURCE_CORRUPT")
            expires_at = envelope.get("expires_at")
            if type(expires_at) is not int or int(time.time()) > expires_at:
                raise RuntimeError("RESULT_RESOURCE_EXPIRED_OR_UNKNOWN")
            payload = self.serialize(envelope.get("payload"))
            payload_sha256 = envelope.get("payload_sha256")
            if not isinstance(payload_sha256, str):
                raise TypeError("RESULT_RESOURCE_CORRUPT")
            if len(payload) > self.settings.resource_max_bytes:
                raise RuntimeError("RESULT_RESOURCE_CORRUPT")
            if hashlib.sha256(payload).hexdigest() != payload_sha256:
                raise RuntimeError("RESULT_RESOURCE_CORRUPT")
            return payload

    def _new_grant_id(self) -> str:
        while True:
            candidate = secrets.token_hex(32)
            if not (self.root / f"{candidate}.json").exists():
                return candidate

    def _entry_count(self) -> int:
        return sum(1 for path in self.root.glob("*.json") if path.is_file())

    def _quarantine_expired_entries(self, now: int) -> None:
        if self._quarantine_expired is None:
            return
        for path in tuple(self.root.glob("*.json")):
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
                expires_at = envelope.get("expires_at") if isinstance(envelope, dict) else None
                if type(expires_at) is int and now > expires_at:
                    self._quarantine_expired(str(path))
            except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError):
                continue


def register_result_resources(server: FastMCP, store: ResultResourceStore) -> None:
    @server.resource(
        _RESULT_URI_TEMPLATE,
        name="KIS oversized result",
        description=(
            "Exact JSON evidence offloaded from one authorized capability-dispatch result. "
            "The opaque per-dispatch grant is retained for a bounded configured TTL."
        ),
        mime_type="application/json",
    )
    def oversized_result_resource(grant_id: str) -> str:
        return store.read(grant_id).decode("utf-8")


__all__ = [
    "ResultResourceStore",
    "StoredResult",
    "register_result_resources",
]
