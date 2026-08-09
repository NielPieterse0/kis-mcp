from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from .contracts import (
    EvidenceConflictError,
    EvidenceCorruptionError,
    EvidenceGeneration,
    EvidenceWriteDisposition,
    FileWriteResult,
    GenerationWriteResult,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_NAME = "manifest.json"
_CURRENT_NAME = "current.json"


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _safe_relative(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    normalized = value.strip().replace("\\", "/").strip("/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{label} must be a normalized relative path")
    if any(":" in part or "\x00" in part for part in path.parts):
        raise ValueError(f"{label} contains an invalid path segment")
    return path.as_posix()


def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    try:
        normalized = json.loads(_canonical_json(dict(value)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON-compatible") from exc
    if not isinstance(normalized, dict):
        raise ValueError(f"{label} must be a JSON object")
    return normalized


class EvidenceStore:
    """Bounded atomic evidence persistence with immutable recoverable generations."""

    def __init__(
        self,
        root: Path,
        *,
        max_file_bytes: int = 1_048_576,
        max_total_bytes: int = 4_194_304,
        replace_fn: Callable[[str | bytes | Path, str | bytes | Path], None] | None = None,
    ) -> None:
        if isinstance(max_file_bytes, bool) or max_file_bytes <= 0:
            raise ValueError("max_file_bytes must be a positive integer")
        if isinstance(max_total_bytes, bool) or max_total_bytes <= 0:
            raise ValueError("max_total_bytes must be a positive integer")
        if max_total_bytes < max_file_bytes:
            raise ValueError("max_total_bytes must be at least max_file_bytes")
        self.root = root.resolve()
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self._replace_fn = replace_fn or os.replace

    def _target(self, relative_path: str, *, label: str = "evidence path") -> Path:
        relative = _safe_relative(relative_path, label)
        target = (self.root / Path(*PurePosixPath(relative).parts)).resolve(strict=False)
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"{label} escapes evidence root") from exc
        return target

    @staticmethod
    def _payload(content: str | bytes) -> bytes:
        if isinstance(content, str):
            return content.encode("utf-8")
        if isinstance(content, bytes):
            return content
        raise ValueError("evidence content must be text or bytes")

    def write_bytes(
        self,
        relative_path: str,
        content: str | bytes,
        *,
        expected_sha256: str | None = None,
    ) -> FileWriteResult:
        payload = self._payload(content)
        if len(payload) > self.max_file_bytes:
            raise ValueError("evidence content exceeds max_file_bytes")
        target = self._target(relative_path)
        new_hash = _digest(payload)
        previous_hash = None
        disposition = EvidenceWriteDisposition.CREATED
        if target.is_file():
            previous = target.read_bytes()
            previous_hash = _digest(previous)
            if previous_hash == new_hash:
                return FileWriteResult(relative_path, EvidenceWriteDisposition.UNCHANGED, new_hash, previous_hash)
            if expected_sha256 != previous_hash:
                return FileWriteResult(relative_path, EvidenceWriteDisposition.CONFLICT, new_hash, previous_hash)
            disposition = EvidenceWriteDisposition.UPDATED
        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_replace(target, payload)
        return FileWriteResult(relative_path, disposition, new_hash, previous_hash)

    def read_bytes(self, relative_path: str, *, expected_sha256: str | None = None) -> bytes:
        target = self._target(relative_path)
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        payload = target.read_bytes()
        if len(payload) > self.max_file_bytes:
            raise EvidenceCorruptionError("stored evidence exceeds max_file_bytes")
        actual = _digest(payload)
        if expected_sha256 is not None and actual != expected_sha256:
            raise EvidenceCorruptionError("stored evidence sha256 does not match manifest")
        return payload

    def _atomic_replace(self, target: Path, payload: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self._replace_fn(temporary_name, target)
        except Exception:
            # The staged file is intentionally retained as recovery evidence.
            raise

    def _namespace_root(self, namespace: str) -> Path:
        return self._target(namespace, label="evidence namespace")

    def _current(self, namespace: str) -> tuple[str | None, str | None]:
        current = self._namespace_root(namespace) / _CURRENT_NAME
        if not current.is_file():
            return None, None
        try:
            value = json.loads(current.read_text(encoding="utf-8"))
            generation_id = str(value["generation_id"])
            manifest_sha256 = str(value["manifest_sha256"])
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise EvidenceCorruptionError("current generation pointer is corrupt") from exc
        if _SHA256.fullmatch(generation_id) is None or _SHA256.fullmatch(manifest_sha256) is None:
            raise EvidenceCorruptionError("current generation pointer contains invalid hashes")
        return generation_id, manifest_sha256

    def write_generation(
        self,
        namespace: str,
        *,
        metadata: Mapping[str, Any],
        artifacts: Mapping[str, str | bytes],
        expected_current_generation: str | None = None,
    ) -> GenerationWriteResult:
        if not artifacts:
            raise ValueError("artifacts must not be empty")
        normalized_metadata = _json_object(metadata, "generation metadata")
        normalized_artifacts: dict[str, bytes] = {}
        artifact_manifest: list[dict[str, Any]] = []
        for raw_path, raw_content in sorted(artifacts.items()):
            path = _safe_relative(raw_path, "artifact path")
            payload = self._payload(raw_content)
            if len(payload) > self.max_file_bytes:
                raise ValueError("evidence content exceeds max_file_bytes")
            normalized_artifacts[path] = payload
            artifact_manifest.append(
                {"path": path, "sha256": _digest(payload), "size_bytes": len(payload)}
            )
        if sum(len(item) for item in normalized_artifacts.values()) > self.max_total_bytes:
            raise ValueError("evidence generation exceeds max_total_bytes")

        identity = {
            "schema_version": 1,
            "metadata": normalized_metadata,
            "artifacts": artifact_manifest,
        }
        generation_id = _digest(_canonical_json(identity))
        manifest = {**identity, "generation_id": generation_id}
        manifest_bytes = _canonical_json(manifest)
        manifest_sha256 = _digest(manifest_bytes)
        previous_id, _previous_manifest_hash = self._current(namespace)
        if expected_current_generation is not None and previous_id != expected_current_generation:
            raise EvidenceConflictError("current evidence generation changed before publication")

        if previous_id == generation_id:
            current = self.read_generation(namespace, generation_id)
            if current.manifest_sha256 != manifest_sha256:
                raise EvidenceCorruptionError("existing generation manifest hash changed")
            return GenerationWriteResult(
                generation_id=generation_id,
                disposition=EvidenceWriteDisposition.UNCHANGED,
                previous_generation_id=previous_id,
                manifest_sha256=manifest_sha256,
            )

        namespace_root = self._namespace_root(namespace)
        generation_root = namespace_root / "generations" / generation_id
        if generation_root.exists():
            existing = self.read_generation(namespace, generation_id)
            if existing.manifest_sha256 != manifest_sha256:
                raise EvidenceCorruptionError("generation identity collides with different manifest")
        else:
            staging_root = namespace_root / ".staging" / f"{generation_id}-{uuid.uuid4().hex}"
            staging_root.mkdir(parents=True, exist_ok=False)
            for path, payload in normalized_artifacts.items():
                target = staging_root / Path(*PurePosixPath(path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
            (staging_root / _MANIFEST_NAME).write_bytes(manifest_bytes)
            generation_root.parent.mkdir(parents=True, exist_ok=True)
            self._replace_fn(staging_root, generation_root)

        pointer = _canonical_json(
            {"generation_id": generation_id, "manifest_sha256": manifest_sha256}
        )
        namespace_root.mkdir(parents=True, exist_ok=True)
        self._atomic_replace(namespace_root / _CURRENT_NAME, pointer)
        return GenerationWriteResult(
            generation_id=generation_id,
            disposition=(
                EvidenceWriteDisposition.CREATED
                if previous_id is None
                else EvidenceWriteDisposition.UPDATED
            ),
            previous_generation_id=previous_id,
            manifest_sha256=manifest_sha256,
        )

    def read_generation(self, namespace: str, generation_id: str) -> EvidenceGeneration:
        if _SHA256.fullmatch(generation_id) is None:
            raise ValueError("generation_id must be a SHA-256 value")
        generation_root = self._namespace_root(namespace) / "generations" / generation_id
        manifest_path = generation_root / _MANIFEST_NAME
        if not manifest_path.is_file():
            raise FileNotFoundError(generation_id)
        manifest_bytes = manifest_path.read_bytes()
        manifest_sha256 = _digest(manifest_bytes)
        try:
            manifest = json.loads(manifest_bytes)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise EvidenceCorruptionError("generation manifest is corrupt") from exc
        if not isinstance(manifest, dict) or manifest.get("generation_id") != generation_id:
            raise EvidenceCorruptionError("generation manifest identity is corrupt")
        metadata = manifest.get("metadata")
        entries = manifest.get("artifacts")
        if not isinstance(metadata, dict) or not isinstance(entries, list):
            raise EvidenceCorruptionError("generation manifest shape is corrupt")
        artifacts: dict[str, bytes] = {}
        total = 0
        for entry in entries:
            if not isinstance(entry, dict):
                raise EvidenceCorruptionError("artifact manifest entry is corrupt")
            try:
                path = _safe_relative(str(entry["path"]), "artifact path")
                expected_hash = str(entry["sha256"])
                expected_size = int(entry["size_bytes"])
            except (KeyError, TypeError, ValueError) as exc:
                raise EvidenceCorruptionError("artifact manifest entry is corrupt") from exc
            if _SHA256.fullmatch(expected_hash) is None:
                raise EvidenceCorruptionError("artifact manifest sha256 is invalid")
            target = generation_root / Path(*PurePosixPath(path).parts)
            if not target.is_file():
                raise EvidenceCorruptionError(f"artifact is missing: {path}")
            payload = target.read_bytes()
            if len(payload) != expected_size or _digest(payload) != expected_hash:
                raise EvidenceCorruptionError(f"artifact sha256 or size mismatch: {path}")
            total += len(payload)
            artifacts[path] = payload
        if total > self.max_total_bytes:
            raise EvidenceCorruptionError("stored generation exceeds max_total_bytes")
        identity = {
            "schema_version": manifest.get("schema_version"),
            "metadata": metadata,
            "artifacts": entries,
        }
        if _digest(_canonical_json(identity)) != generation_id:
            raise EvidenceCorruptionError("generation manifest fingerprint is corrupt")
        return EvidenceGeneration(
            generation_id=generation_id,
            metadata=metadata,
            artifacts=artifacts,
            manifest_sha256=manifest_sha256,
        )

    def read_current_generation(self, namespace: str) -> EvidenceGeneration:
        generation_id, expected_manifest_hash = self._current(namespace)
        if generation_id is None or expected_manifest_hash is None:
            raise FileNotFoundError(f"No current evidence generation for {namespace}")
        generation = self.read_generation(namespace, generation_id)
        if generation.manifest_sha256 != expected_manifest_hash:
            raise EvidenceCorruptionError("current manifest sha256 does not match generation")
        return generation

    def retain_corrupt_current_pointer(self, namespace: str) -> str | None:
        namespace_root = self._namespace_root(namespace)
        current = namespace_root / _CURRENT_NAME
        if not current.is_file():
            return None
        recovery = namespace_root / "recovery"
        recovery.mkdir(parents=True, exist_ok=True)
        destination = recovery / f"current-{uuid.uuid4().hex}.json"
        self._replace_fn(current, destination)
        return destination.relative_to(self.root).as_posix()


__all__ = ["EvidenceStore"]
