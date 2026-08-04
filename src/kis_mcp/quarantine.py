from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import shutil
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .quarantine_integrity import payload_sha256, sign_metadata, verify_metadata


QUARANTINE_SCHEMA_VERSION = 2
_INTEGRITY_KEY_NAME = ".metadata-integrity.key"
_INTEGRITY_KEY_BYTES = 32
_METADATA_FIELDS = frozenset(
    {
        "schema_version",
        "operation_id",
        "original_path",
        "original_relative_path",
        "payload_path",
        "item_type",
        "payload_digest",
        "quarantined_at",
        "restored_at",
        "integrity_digest",
    }
)
_HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
_OPERATION_ID_PATTERN = re.compile(r"\d{8}T\d{12}Z-[0-9a-f]{12}")


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    schema_version: int
    operation_id: str
    original_path: str
    original_relative_path: str
    payload_path: str
    item_type: str
    payload_digest: str
    quarantined_at: str
    restored_at: str | None
    integrity_digest: str


class QuarantineError(RuntimeError):
    pass


class QuarantineService:
    def __init__(self, *, project_boundary: str, quarantine_root: str) -> None:
        self.project_boundary = Path(project_boundary).resolve(strict=True)
        self.quarantine_root = Path(quarantine_root).absolute()
        self._require_entry_within_boundary(self.quarantine_root)
        self._integrity_key_path = self.quarantine_root / _INTEGRITY_KEY_NAME

    def quarantine(self, path: str) -> QuarantineRecord:
        source = self._prepare_source(path)
        return self._quarantine_source(source)

    def quarantine_many(self, paths: Sequence[str]) -> list[QuarantineRecord]:
        sources = [self._prepare_source(path) for path in paths]
        self._validate_batch_sources(sources)

        completed: list[QuarantineRecord] = []
        try:
            for source in sources:
                completed.append(self._quarantine_source(source))
            return completed
        except QuarantineError as exc:
            residual_ids: list[str] = []
            rollback_errors: list[str] = []
            for record in reversed(completed):
                try:
                    self._rollback_record(record)
                except QuarantineError as rollback_exc:
                    residual_ids.append(record.operation_id)
                    rollback_errors.append(str(rollback_exc))

            if residual_ids:
                residual = ", ".join(residual_ids)
                detail = "; ".join(rollback_errors)
                raise QuarantineError(
                    "Unable to quarantine batch: "
                    f"{exc}; rollback incomplete; residual operation IDs: {residual}. "
                    f"Recovery details: {detail}"
                ) from exc
            raise QuarantineError(f"Unable to quarantine batch: {exc}") from exc

    def list_records(self, *, limit: int = 50) -> list[QuarantineRecord]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        if not self.quarantine_root.exists():
            return []

        records: list[QuarantineRecord] = []
        invalid: list[str] = []
        operation_entries = sorted(
            (
                path
                for path in self.quarantine_root.iterdir()
                if _OPERATION_ID_PATTERN.fullmatch(path.name) is not None
            ),
            key=lambda item: item.name,
            reverse=True,
        )
        for operation_root in operation_entries:
            metadata_path = operation_root / "metadata.json"
            if not operation_root.is_dir() or operation_root.is_symlink():
                invalid.append(operation_root.name)
                continue
            if not metadata_path.is_file():
                invalid.append(operation_root.name)
                continue
            try:
                record = self._read_metadata(metadata_path)
                self._validate_record(record, operation_root)
                if len(records) < limit:
                    records.append(record)
            except (OSError, ValueError, json.JSONDecodeError, QuarantineError):
                invalid.append(operation_root.name)

        if invalid:
            affected = ", ".join(invalid[:10])
            suffix = "" if len(invalid) <= 10 else f" and {len(invalid) - 10} more"
            raise QuarantineError(
                f"Corrupt quarantine metadata for operation(s): {affected}{suffix}"
            )
        return records

    def restore(self, operation_id: str) -> QuarantineRecord:
        self._validate_operation_id(operation_id)
        operation_root = self.quarantine_root / operation_id
        metadata_path = operation_root / "metadata.json"
        record = self._read_metadata(metadata_path)
        self._validate_record(record, operation_root)

        payload = Path(record.payload_path).absolute()
        original = Path(record.original_path).absolute()
        if record.restored_at is not None:
            raise QuarantineError(f"Quarantine operation {operation_id} is already restored")
        if self._entry_exists(original):
            raise QuarantineError(f"Restore would overwrite existing path: {original}")
        if not self._entry_exists(payload):
            raise QuarantineError(f"Quarantine payload is missing: {payload}")

        try:
            actual_payload_digest = payload_sha256(payload)
        except (OSError, ValueError) as exc:
            raise QuarantineError(
                f"Quarantine payload integrity check failed: {operation_id}: {exc}"
            ) from exc
        if not hmac.compare_digest(actual_payload_digest, record.payload_digest):
            raise QuarantineError(
                f"Quarantine payload integrity check failed: {operation_id}"
            )

        original.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(payload), str(original))
            restored = replace(record, restored_at=datetime.now(UTC).isoformat())
            restored = self._sign_record(restored)
            self._write_metadata(metadata_path, restored)
            return restored
        except Exception as exc:
            rollback_error: Exception | None = None
            if self._entry_exists(original) and not self._entry_exists(payload):
                try:
                    payload.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(original), str(payload))
                except Exception as rollback_exc:
                    rollback_error = rollback_exc
            if rollback_error is not None:
                raise QuarantineError(
                    "Unable to restore quarantine operation "
                    f"{operation_id}: {exc}; rollback incomplete: {rollback_error}"
                ) from exc
            raise QuarantineError(
                f"Unable to restore quarantine operation {operation_id}: {exc}"
            ) from exc

    def _quarantine_source(self, source: Path) -> QuarantineRecord:
        self._load_integrity_key(create=True)
        operation_id = self._new_operation_id()
        operation_root = self.quarantine_root / operation_id
        payload_root = operation_root / "payload"
        payload_path = payload_root / source.name
        metadata_path = operation_root / "metadata.json"

        payload_root.mkdir(parents=True, exist_ok=False)
        rollback_error: Exception | None = None
        try:
            shutil.move(str(source), str(payload_path))
            unsigned = QuarantineRecord(
                schema_version=QUARANTINE_SCHEMA_VERSION,
                operation_id=operation_id,
                original_path=str(source),
                original_relative_path=self._canonical_original_relative(source),
                payload_path=str(payload_path),
                item_type=self._item_type(payload_path),
                payload_digest=payload_sha256(payload_path),
                quarantined_at=datetime.now(UTC).isoformat(),
                restored_at=None,
                integrity_digest="",
            )
            record = self._sign_record(unsigned)
            self._write_metadata(metadata_path, record)
            return record
        except Exception as exc:
            if self._entry_exists(payload_path) and not self._entry_exists(source):
                try:
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(payload_path), str(source))
                except Exception as rollback_exc:
                    rollback_error = rollback_exc
            if rollback_error is None:
                try:
                    self._remove_operation_residue(operation_root)
                except Exception as cleanup_exc:
                    rollback_error = cleanup_exc
            if rollback_error is not None:
                raise QuarantineError(
                    f"Unable to quarantine {source}: {exc}; rollback incomplete; "
                    f"residual operation ID: {operation_id}; recovery details: "
                    f"{rollback_error}"
                ) from exc
            raise QuarantineError(f"Unable to quarantine {source}: {exc}") from exc

    def _prepare_source(self, path: str) -> Path:
        candidate = Path(path).expanduser()
        source = (
            candidate if candidate.is_absolute() else self.project_boundary / candidate
        ).absolute()
        if not self._entry_exists(source):
            raise QuarantineError(f"Quarantine target does not exist: {source}")
        self._require_entry_within_boundary(source)
        if self._same_path(source, self.project_boundary):
            raise QuarantineError("The project boundary itself cannot be quarantined")
        if self._entry_within(source, self.quarantine_root):
            raise QuarantineError("An existing quarantine payload cannot be quarantined again")
        return source

    def _validate_batch_sources(self, sources: Sequence[Path]) -> None:
        normalized: dict[str, Path] = {}
        for source in sources:
            key = os.path.normcase(os.path.abspath(source))
            if key in normalized:
                raise QuarantineError(f"Quarantine batch contains duplicate target: {source}")
            normalized[key] = source

        ordered = list(normalized.values())
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                if self._entry_contains(left, right) or self._entry_contains(right, left):
                    raise QuarantineError(
                        f"Quarantine batch targets overlap: {left} and {right}"
                    )

    def _rollback_record(self, record: QuarantineRecord) -> None:
        operation_root = self.quarantine_root / record.operation_id
        payload = Path(record.payload_path).absolute()
        original = Path(record.original_path).absolute()
        if self._entry_exists(original):
            raise QuarantineError(f"Rollback would overwrite existing path: {original}")
        if not self._entry_exists(payload):
            raise QuarantineError(f"Rollback payload is missing: {payload}")

        original.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(payload), str(original))
            self._remove_operation_residue(operation_root)
        except Exception as exc:
            raise QuarantineError(
                f"Unable to roll back quarantine operation {record.operation_id}: {exc}"
            ) from exc

    def _remove_operation_residue(self, operation_root: Path) -> None:
        metadata_path = operation_root / "metadata.json"
        temp_path = metadata_path.with_suffix(".json.tmp")
        for path in (temp_path, metadata_path):
            if path.exists():
                path.unlink()

        payload_root = operation_root / "payload"
        if payload_root.exists():
            payload_root.rmdir()
        if operation_root.exists():
            operation_root.rmdir()

    def _validate_record(self, record: QuarantineRecord, operation_root: Path) -> None:
        if record.schema_version != QUARANTINE_SCHEMA_VERSION:
            raise QuarantineError(
                "Quarantine metadata schema is unsupported or unsigned"
            )
        self._validate_operation_id(record.operation_id)
        if record.operation_id != operation_root.name:
            raise QuarantineError("Quarantine metadata operation ID does not match its directory")

        original = Path(record.original_path).absolute()
        payload = Path(record.payload_path).absolute()
        expected_relative = self._canonical_original_relative(original)
        expected_original = (self.project_boundary / record.original_relative_path).absolute()
        expected_payload = operation_root / "payload" / original.name
        self._require_entry_within_boundary(original)
        self._require_entry_within_boundary(payload)
        if self._entry_within(original, self.quarantine_root):
            raise QuarantineError("Quarantine metadata original path is inside quarantine")
        if record.original_relative_path != expected_relative:
            raise QuarantineError("Quarantine metadata original path is not canonical")
        if not self._same_path(original, expected_original):
            raise QuarantineError("Quarantine metadata original path binding is invalid")
        if not self._same_path(payload, expected_payload):
            raise QuarantineError("Quarantine metadata payload path is outside its operation")
        if record.item_type not in {"file", "directory", "symlink"}:
            raise QuarantineError("Quarantine metadata item_type is invalid")
        if _HEX_SHA256.fullmatch(record.payload_digest) is None:
            raise QuarantineError("Quarantine metadata payload digest is invalid")
        if _HEX_SHA256.fullmatch(record.integrity_digest) is None:
            raise QuarantineError("Quarantine metadata integrity digest is invalid")
        self._validate_timestamp(record.quarantined_at, "quarantined_at")
        if record.restored_at is not None:
            self._validate_timestamp(record.restored_at, "restored_at")

        key = self._load_integrity_key(create=False)
        if not verify_metadata(key, self._record_fields(record), record.integrity_digest):
            raise QuarantineError("Quarantine metadata integrity check failed")

    def _sign_record(self, record: QuarantineRecord) -> QuarantineRecord:
        key = self._load_integrity_key(create=False)
        digest = sign_metadata(key, self._record_fields(record))
        return replace(record, integrity_digest=digest)

    @staticmethod
    def _record_fields(record: QuarantineRecord) -> dict[str, object]:
        return {
            "schema_version": record.schema_version,
            "operation_id": record.operation_id,
            "original_path": record.original_path,
            "original_relative_path": record.original_relative_path,
            "payload_path": record.payload_path,
            "item_type": record.item_type,
            "payload_digest": record.payload_digest,
            "quarantined_at": record.quarantined_at,
            "restored_at": record.restored_at,
        }

    def _load_integrity_key(self, *, create: bool) -> bytes:
        if create:
            self.quarantine_root.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            try:
                descriptor = os.open(self._integrity_key_path, flags, 0o600)
            except FileExistsError:
                pass
            else:
                try:
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(secrets.token_bytes(_INTEGRITY_KEY_BYTES))
                        handle.flush()
                        os.fsync(handle.fileno())
                except Exception:
                    try:
                        self._integrity_key_path.unlink()
                    except OSError:
                        pass
                    raise

        try:
            key = self._integrity_key_path.read_bytes()
        except OSError as exc:
            raise QuarantineError(
                f"Quarantine metadata integrity key is unavailable: {exc}"
            ) from exc
        if len(key) != _INTEGRITY_KEY_BYTES:
            raise QuarantineError("Quarantine metadata integrity key is invalid")
        return key

    def _canonical_original_relative(self, path: Path) -> str:
        self._require_entry_within_boundary(path)
        relative = os.path.relpath(
            os.path.abspath(path),
            os.path.abspath(self.project_boundary),
        )
        if relative == os.curdir or relative.startswith(os.pardir + os.sep):
            raise QuarantineError("Quarantine metadata original path is not a descendant")
        return os.path.normpath(relative)

    def _require_entry_within_boundary(self, path: Path) -> None:
        if not self._entry_within(path, self.project_boundary):
            raise QuarantineError(
                f"Path is outside the approved project boundary: {path}"
            )

    @classmethod
    def _entry_within(cls, path: Path, boundary: Path) -> bool:
        candidate = path.parent.resolve(strict=False) / path.name
        resolved_boundary = boundary.resolve(strict=False)
        try:
            return os.path.commonpath(
                [os.path.normcase(str(candidate)), os.path.normcase(str(resolved_boundary))]
            ) == os.path.normcase(str(resolved_boundary))
        except ValueError:
            return False

    @classmethod
    def _entry_contains(cls, parent: Path, child: Path) -> bool:
        if cls._same_path(parent, child):
            return False
        try:
            return os.path.commonpath(
                [
                    os.path.normcase(os.path.abspath(parent)),
                    os.path.normcase(os.path.abspath(child)),
                ]
            ) == os.path.normcase(os.path.abspath(parent))
        except ValueError:
            return False

    @staticmethod
    def _same_path(left: Path, right: Path) -> bool:
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
            os.path.abspath(right)
        )

    @staticmethod
    def _entry_exists(path: Path) -> bool:
        return path.exists() or path.is_symlink()

    @staticmethod
    def _item_type(path: Path) -> str:
        if path.is_symlink():
            return "symlink"
        if path.is_dir():
            return "directory"
        if path.is_file():
            return "file"
        raise QuarantineError(f"Unsupported quarantine payload type: {path}")

    @staticmethod
    def _new_operation_id() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        return f"{timestamp}-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _validate_operation_id(operation_id: str) -> None:
        if _OPERATION_ID_PATTERN.fullmatch(operation_id) is None:
            raise QuarantineError("Invalid quarantine operation ID")

    @staticmethod
    def _validate_timestamp(value: str, field: str) -> None:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise QuarantineError(f"Quarantine metadata {field} is invalid") from exc
        if parsed.tzinfo is None:
            raise QuarantineError(f"Quarantine metadata {field} must include a timezone")

    @staticmethod
    def _write_metadata(path: Path, record: QuarantineRecord) -> None:
        temp_path = path.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps(asdict(record), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(path)

    @staticmethod
    def _read_metadata(path: Path) -> QuarantineRecord:
        try:
            raw: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise QuarantineError(f"Quarantine metadata is unreadable: {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise QuarantineError("Quarantine metadata must be an object")
        if set(raw) != _METADATA_FIELDS:
            raise QuarantineError("Quarantine metadata fields are invalid or unsigned")

        string_fields = (
            "operation_id",
            "original_path",
            "original_relative_path",
            "payload_path",
            "item_type",
            "payload_digest",
            "quarantined_at",
            "integrity_digest",
        )
        if type(raw["schema_version"]) is not int:
            raise QuarantineError("Quarantine metadata schema_version is invalid")
        for field in string_fields:
            if type(raw[field]) is not str:
                raise QuarantineError(f"Quarantine metadata {field} is invalid")
        if raw["restored_at"] is not None and type(raw["restored_at"]) is not str:
            raise QuarantineError("Quarantine metadata restored_at is invalid")

        return QuarantineRecord(
            schema_version=raw["schema_version"],
            operation_id=raw["operation_id"],
            original_path=raw["original_path"],
            original_relative_path=raw["original_relative_path"],
            payload_path=raw["payload_path"],
            item_type=raw["item_type"],
            payload_digest=raw["payload_digest"],
            quarantined_at=raw["quarantined_at"],
            restored_at=raw["restored_at"],
            integrity_digest=raw["integrity_digest"],
        )
