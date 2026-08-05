from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from .contracts import VaultEnvelope, VaultMetadata
from .errors import (
    VaultAlreadyInitializedError,
    VaultIntegrityError,
    VaultNotInitializedError,
)


_MAX_VAULT_BYTES = 16 * 1024 * 1024
_MAX_METADATA_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class VaultPaths:
    vault: Path
    metadata: Path
    backups: Path


class VaultStore:
    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path) or not root.is_absolute():
            raise ValueError("KIS_MCP_SECRET_ROOT_INVALID")
        self.root = root.resolve()
        self.paths = VaultPaths(
            vault=self.root / "vault.json",
            metadata=self.root / "metadata.json",
            backups=self.root / "backups",
        )

    @property
    def initialized(self) -> bool:
        return self.paths.vault.is_file() and self.paths.metadata.is_file()

    @property
    def state_incomplete(self) -> bool:
        return self.paths.vault.exists() != self.paths.metadata.exists()

    def initialize(self, envelope: VaultEnvelope, metadata: VaultMetadata) -> None:
        if self.paths.vault.exists() or self.paths.metadata.exists():
            raise VaultAlreadyInitializedError(
                "KIS_MCP_SECRET_VAULT_ALREADY_INITIALIZED"
            )
        self.root.mkdir(parents=True, exist_ok=True)
        self.paths.backups.mkdir(parents=True, exist_ok=True)
        self._atomic_write_json(self.paths.vault, envelope.to_dict())
        self._atomic_write_json(self.paths.metadata, metadata.to_dict())

    def load_envelope(self) -> VaultEnvelope:
        value = self._read_json(
            self.paths.vault,
            max_bytes=_MAX_VAULT_BYTES,
            missing_code="KIS_MCP_SECRET_VAULT_NOT_INITIALIZED",
        )
        try:
            return VaultEnvelope.from_dict(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise VaultIntegrityError(
                "KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED"
            ) from exc

    def load_metadata(self) -> VaultMetadata:
        value = self._read_json(
            self.paths.metadata,
            max_bytes=_MAX_METADATA_BYTES,
            missing_code="KIS_MCP_SECRET_VAULT_NOT_INITIALIZED",
        )
        try:
            return VaultMetadata.from_dict(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise VaultIntegrityError(
                "KIS_MCP_SECRET_METADATA_INTEGRITY_FAILED"
            ) from exc

    def replace(
        self,
        envelope: VaultEnvelope,
        metadata: VaultMetadata,
    ) -> Path:
        if not self.initialized:
            raise VaultNotInitializedError("KIS_MCP_SECRET_VAULT_NOT_INITIALIZED")
        self.paths.backups.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = self.paths.backups / (
            f"vault-generation-{metadata.generation - 1}-{timestamp}-{uuid4().hex}.json"
        )
        shutil.copy2(self.paths.vault, backup)
        self._sync_file(backup)
        self._atomic_write_json(self.paths.vault, envelope.to_dict())
        self._atomic_write_json(self.paths.metadata, metadata.to_dict())
        return backup

    def _read_json(
        self,
        path: Path,
        *,
        max_bytes: int,
        missing_code: str,
    ) -> Mapping[str, Any]:
        try:
            size = path.stat().st_size
            if size > max_bytes:
                raise VaultIntegrityError("KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED")
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise VaultNotInitializedError(missing_code) from exc
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VaultIntegrityError(
                "KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED"
            ) from exc
        if not isinstance(value, Mapping):
            raise VaultIntegrityError("KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED")
        return value

    def _atomic_write_json(self, path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("utf-8")
        temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            self._sync_directory(path.parent)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _sync_file(path: Path) -> None:
        try:
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        except OSError:
            pass

    @staticmethod
    def _sync_directory(path: Path) -> None:
        if os.name == "nt":
            return
        try:
            descriptor = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
