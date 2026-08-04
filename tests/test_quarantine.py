from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from kis_mcp.config import load_runtime_config
from kis_mcp.quarantine import QuarantineError, QuarantineService


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_runtime_config(REPOSITORY_ROOT)


def _new_test_file(name: str = "artifact.txt") -> Path:
    root = Path(CONFIG.temp_root) / "tests" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    path = root / name
    path.write_text("test data\n", encoding="utf-8")
    return path


def _service() -> QuarantineService:
    return QuarantineService(
        project_boundary=CONFIG.project_boundary,
        quarantine_root=CONFIG.quarantine_root,
    )


def test_quarantine_and_restore_without_overwrite() -> None:
    source = _new_test_file()
    service = _service()

    record = service.quarantine(str(source))
    assert not source.exists()
    assert Path(record.payload_path).exists()

    restored = service.restore(record.operation_id)
    assert restored.restored_at is not None
    assert source.read_text(encoding="utf-8") == "test data\n"

    service.quarantine(str(source))


def test_relative_quarantine_path_resolves_from_project_boundary() -> None:
    source = _new_test_file("relative.txt")
    service = _service()
    relative = source.relative_to(Path(CONFIG.project_boundary))

    record = service.quarantine(str(relative))
    assert not source.exists()
    service.restore(record.operation_id)
    assert source.exists()
    service.quarantine(str(source))


def test_restore_refuses_to_overwrite_existing_path() -> None:
    source = _new_test_file("collision.txt")
    service = _service()
    record = service.quarantine(str(source))

    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("replacement\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match="overwrite"):
        service.restore(record.operation_id)

    service.quarantine(str(source))


def test_restore_rejects_tampered_payload_path() -> None:
    source = _new_test_file("tampered.txt")
    other = _new_test_file("other.txt")
    service = _service()
    record = service.quarantine(str(source))
    metadata_path = Path(record.payload_path).parents[1] / "metadata.json"
    original_metadata = metadata_path.read_text(encoding="utf-8")
    metadata = json.loads(original_metadata)
    metadata["payload_path"] = str(other)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match="outside its operation"):
        service.restore(record.operation_id)

    metadata_path.write_text(original_metadata, encoding="utf-8")
    service.restore(record.operation_id)
    service.quarantine(str(source))
    service.quarantine(str(other))
