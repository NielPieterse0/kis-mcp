from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    operation_id: str
    original_path: str
    payload_path: str
    item_type: str
    quarantined_at: str
    restored_at: str | None = None


class QuarantineError(RuntimeError):
    pass


class QuarantineService:
    def __init__(self, *, project_boundary: str, quarantine_root: str) -> None:
        self.project_boundary = Path(project_boundary).resolve(strict=True)
        self.quarantine_root = Path(quarantine_root).absolute()
        self._require_entry_within_boundary(self.quarantine_root)

    def quarantine(self, path: str) -> QuarantineRecord:
        candidate = Path(path).expanduser()
        source = (
            candidate if candidate.is_absolute() else self.project_boundary / candidate
        ).absolute()
        if not source.exists() and not source.is_symlink():
            raise QuarantineError(f"Quarantine target does not exist: {source}")
        self._require_entry_within_boundary(source)
        if self._same_path(source, self.project_boundary):
            raise QuarantineError("The project boundary itself cannot be quarantined")
        if self._entry_within(source, self.quarantine_root):
            raise QuarantineError("An existing quarantine payload cannot be quarantined again")

        operation_id = self._new_operation_id()
        operation_root = self.quarantine_root / operation_id
        payload_root = operation_root / "payload"
        payload_path = payload_root / source.name
        metadata_path = operation_root / "metadata.json"

        payload_root.mkdir(parents=True, exist_ok=False)
        try:
            shutil.move(str(source), str(payload_path))
            record = QuarantineRecord(
                operation_id=operation_id,
                original_path=str(source),
                payload_path=str(payload_path),
                item_type="directory" if payload_path.is_dir() else "file",
                quarantined_at=datetime.now(UTC).isoformat(),
            )
            self._write_metadata(metadata_path, record)
            return record
        except Exception as exc:
            if self._entry_exists(payload_path) and not self._entry_exists(source):
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(payload_path), str(source))
            raise QuarantineError(f"Unable to quarantine {source}: {exc}") from exc

    def list_records(self, *, limit: int = 50) -> list[QuarantineRecord]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        if not self.quarantine_root.exists():
            return []

        records: list[QuarantineRecord] = []
        for metadata_path in sorted(
            self.quarantine_root.glob("*/metadata.json"),
            key=lambda item: item.stat().st_mtime_ns,
            reverse=True,
        ):
            try:
                record = self._read_metadata(metadata_path)
                self._validate_record(record, metadata_path.parent)
                records.append(record)
            except (OSError, ValueError, json.JSONDecodeError, QuarantineError):
                continue
            if len(records) >= limit:
                break
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

        original.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(payload), str(original))
            restored = QuarantineRecord(
                operation_id=record.operation_id,
                original_path=record.original_path,
                payload_path=record.payload_path,
                item_type=record.item_type,
                quarantined_at=record.quarantined_at,
                restored_at=datetime.now(UTC).isoformat(),
            )
            self._write_metadata(metadata_path, restored)
            return restored
        except Exception as exc:
            if self._entry_exists(original) and not self._entry_exists(payload):
                payload.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(original), str(payload))
            raise QuarantineError(
                f"Unable to restore quarantine operation {operation_id}: {exc}"
            ) from exc

    def _validate_record(self, record: QuarantineRecord, operation_root: Path) -> None:
        self._validate_operation_id(record.operation_id)
        if record.operation_id != operation_root.name:
            raise QuarantineError("Quarantine metadata operation ID does not match its directory")

        original = Path(record.original_path).absolute()
        payload = Path(record.payload_path).absolute()
        expected_payload = operation_root / "payload" / original.name
        self._require_entry_within_boundary(original)
        self._require_entry_within_boundary(payload)
        if self._entry_within(original, self.quarantine_root):
            raise QuarantineError("Quarantine metadata original path is inside quarantine")
        if not self._same_path(payload, expected_payload):
            raise QuarantineError("Quarantine metadata payload path is outside its operation")
        if record.item_type not in {"file", "directory"}:
            raise QuarantineError("Quarantine metadata item_type is invalid")

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

    @staticmethod
    def _same_path(left: Path, right: Path) -> bool:
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
            os.path.abspath(right)
        )

    @staticmethod
    def _entry_exists(path: Path) -> bool:
        return path.exists() or path.is_symlink()

    @staticmethod
    def _new_operation_id() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        return f"{timestamp}-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _validate_operation_id(operation_id: str) -> None:
        if re.fullmatch(r"\d{8}T\d{12}Z-[0-9a-f]{12}", operation_id) is None:
            raise QuarantineError("Invalid quarantine operation ID")

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
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Quarantine metadata must be an object")
        return QuarantineRecord(
            operation_id=str(raw["operation_id"]),
            original_path=str(raw["original_path"]),
            payload_path=str(raw["payload_path"]),
            item_type=str(raw["item_type"]),
            quarantined_at=str(raw["quarantined_at"]),
            restored_at=(
                None if raw.get("restored_at") is None else str(raw["restored_at"])
            ),
        )
