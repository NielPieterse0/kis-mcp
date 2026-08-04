from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

from kis_mcp.config import load_runtime_config
from kis_mcp.quarantine import QuarantineError, QuarantineService


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_runtime_config(REPOSITORY_ROOT)


def _new_test_root() -> Path:
    root = Path(CONFIG.temp_root) / "tests" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    return root


def _new_test_file(
    name: str = "artifact.txt",
    *,
    root: Path | None = None,
    content: str = "test data\n",
) -> Path:
    target_root = root or _new_test_root()
    target_root.mkdir(parents=True, exist_ok=True)
    path = target_root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _service(root: Path | None = None) -> QuarantineService:
    quarantine_root = (root or _new_test_root()) / "quarantine"
    return QuarantineService(
        project_boundary=CONFIG.project_boundary,
        quarantine_root=str(quarantine_root),
    )


def _operation_directories(service: QuarantineService) -> set[str]:
    root = Path(service.quarantine_root)
    if not root.exists():
        return set()
    return {path.name for path in root.iterdir() if path.is_dir()}


def test_quarantine_and_restore_without_overwrite() -> None:
    root = _new_test_root()
    source = _new_test_file(root=root / "workspace")
    service = _service(root)

    record = service.quarantine(str(source))
    assert not source.exists()
    assert Path(record.payload_path).exists()

    restored = service.restore(record.operation_id)
    assert restored.restored_at is not None
    assert source.read_text(encoding="utf-8") == "test data\n"

    service.quarantine(str(source))


def test_relative_quarantine_path_resolves_from_project_boundary() -> None:
    root = _new_test_root()
    source = _new_test_file("relative.txt", root=root / "workspace")
    service = _service(root)
    relative = source.relative_to(Path(CONFIG.project_boundary))

    record = service.quarantine(str(relative))
    assert not source.exists()
    service.restore(record.operation_id)
    assert source.exists()
    service.quarantine(str(source))


def test_restore_refuses_to_overwrite_existing_path() -> None:
    root = _new_test_root()
    source = _new_test_file("collision.txt", root=root / "workspace")
    service = _service(root)
    record = service.quarantine(str(source))

    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("replacement\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match="overwrite"):
        service.restore(record.operation_id)

    service.quarantine(str(source))


def test_restore_rejects_tampered_payload_path() -> None:
    root = _new_test_root()
    source = _new_test_file("tampered.txt", root=root / "workspace")
    other = _new_test_file("other.txt", root=root / "other")
    service = _service(root)
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


def test_restore_rejects_tampered_original_path_with_same_basename() -> None:
    root = _new_test_root()
    source = _new_test_file("same.txt", root=root / "first")
    redirected = root / "second" / "same.txt"
    service = _service(root)
    record = service.quarantine(str(source))
    metadata_path = Path(record.payload_path).parents[1] / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["original_path"] = str(redirected)
    metadata["original_relative_path"] = str(
        redirected.relative_to(Path(CONFIG.project_boundary))
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match="metadata integrity"):
        service.restore(record.operation_id)

    assert not source.exists()
    assert not redirected.exists()
    assert Path(record.payload_path).exists()


def test_restore_rejects_payload_content_tamper() -> None:
    root = _new_test_root()
    source = _new_test_file("payload.txt", root=root / "workspace")
    service = _service(root)
    record = service.quarantine(str(source))
    payload = Path(record.payload_path)
    payload.write_text("changed\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match="payload integrity"):
        service.restore(record.operation_id)

    assert not source.exists()
    assert payload.read_text(encoding="utf-8") == "changed\n"


def test_restore_rejects_nested_directory_payload_tamper() -> None:
    root = _new_test_root()
    source = root / "workspace" / "tree"
    source.mkdir(parents=True)
    (source / "nested").mkdir()
    (source / "nested" / "value.txt").write_text("before\n", encoding="utf-8")
    service = _service(root)
    record = service.quarantine(str(source))
    payload = Path(record.payload_path)
    (payload / "nested" / "value.txt").write_text("after\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match="payload integrity"):
        service.restore(record.operation_id)

    assert not source.exists()
    assert payload.exists()


def test_restore_rejects_unsigned_legacy_metadata() -> None:
    root = _new_test_root()
    source = _new_test_file("legacy.txt", root=root / "workspace")
    service = _service(root)
    record = service.quarantine(str(source))
    metadata_path = Path(record.payload_path).parents[1] / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for field in (
        "schema_version",
        "original_relative_path",
        "payload_digest",
        "integrity_digest",
    ):
        metadata.pop(field, None)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match="unsigned|schema|fields"):
        service.restore(record.operation_id)

    assert Path(record.payload_path).exists()


def test_restore_rejects_unknown_metadata_fields() -> None:
    root = _new_test_root()
    source = _new_test_file("unknown-field.txt", root=root / "workspace")
    service = _service(root)
    record = service.quarantine(str(source))
    metadata_path = Path(record.payload_path).parents[1] / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["unexpected"] = "value"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match="fields"):
        service.restore(record.operation_id)

    assert Path(record.payload_path).exists()


def test_restore_rejects_corrupt_integrity_key() -> None:
    root = _new_test_root()
    source = _new_test_file("key.txt", root=root / "workspace")
    service = _service(root)
    record = service.quarantine(str(source))
    key_path = Path(service.quarantine_root) / ".metadata-integrity.key"
    key_path.write_bytes(b"x" * 32)

    with pytest.raises(QuarantineError, match="metadata integrity"):
        service.restore(record.operation_id)

    assert Path(record.payload_path).exists()


def test_list_records_reports_corrupt_metadata() -> None:
    root = _new_test_root()
    source = _new_test_file("list-corrupt.txt", root=root / "workspace")
    service = _service(root)
    record = service.quarantine(str(source))
    metadata_path = Path(record.payload_path).parents[1] / "metadata.json"
    metadata_path.write_text("{not-json\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match=record.operation_id):
        service.list_records()


def test_list_records_reports_corruption_beyond_return_limit() -> None:
    root = _new_test_root()
    service = _service(root)
    corrupt_source = _new_test_file("older.txt", root=root / "older")
    corrupt_record = service.quarantine(str(corrupt_source))
    corrupt_metadata = Path(corrupt_record.payload_path).parents[1] / "metadata.json"
    corrupt_metadata.write_text("{not-json\n", encoding="utf-8")

    valid_source = _new_test_file("newer.txt", root=root / "newer")
    service.quarantine(str(valid_source))

    with pytest.raises(QuarantineError, match=corrupt_record.operation_id):
        service.list_records(limit=1)


def test_list_records_reports_missing_metadata() -> None:
    root = _new_test_root()
    service = _service(root)
    operation_id = service._new_operation_id()
    operation_root = Path(service.quarantine_root) / operation_id
    (operation_root / "payload").mkdir(parents=True)

    with pytest.raises(QuarantineError, match=operation_id):
        service.list_records()


def test_restore_normalizes_malformed_metadata_error() -> None:
    root = _new_test_root()
    source = _new_test_file("malformed.txt", root=root / "workspace")
    service = _service(root)
    record = service.quarantine(str(source))
    metadata_path = Path(record.payload_path).parents[1] / "metadata.json"
    metadata_path.write_text("{not-json\n", encoding="utf-8")

    with pytest.raises(QuarantineError, match="metadata"):
        service.restore(record.operation_id)

    assert Path(record.payload_path).exists()


def test_restore_normalizes_payload_hash_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _new_test_root()
    source = _new_test_file("unreadable.txt", root=root / "workspace")
    service = _service(root)
    record = service.quarantine(str(source))

    def fail_hash(_path: Path) -> str:
        raise OSError("simulated payload read failure")

    monkeypatch.setattr("kis_mcp.quarantine.payload_sha256", fail_hash)

    with pytest.raises(QuarantineError, match="payload integrity"):
        service.restore(record.operation_id)

    assert Path(record.payload_path).exists()


def test_quarantine_many_rolls_back_completed_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _new_test_root()
    first = _new_test_file("first.txt", root=root / "workspace", content="first\n")
    second = _new_test_file("second.txt", root=root / "workspace", content="second\n")
    service = _service(root)
    before = _operation_directories(service)
    real_move = shutil.move
    calls = 0

    def fail_second_move(source: str, destination: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second move failure")
        return real_move(source, destination)

    monkeypatch.setattr("kis_mcp.quarantine.shutil.move", fail_second_move)

    with pytest.raises(QuarantineError, match="simulated second move failure"):
        service.quarantine_many([str(first), str(second)])

    assert first.read_text(encoding="utf-8") == "first\n"
    assert second.read_text(encoding="utf-8") == "second\n"
    assert _operation_directories(service) == before


def test_quarantine_many_rejects_duplicate_targets_before_mutation() -> None:
    root = _new_test_root()
    source = _new_test_file("duplicate.txt", root=root / "workspace")
    service = _service(root)

    with pytest.raises(QuarantineError, match="duplicate"):
        service.quarantine_many([str(source), str(source)])

    assert source.exists()
    assert _operation_directories(service) == set()


def test_quarantine_many_rejects_overlapping_targets_before_mutation() -> None:
    root = _new_test_root()
    parent = root / "workspace" / "parent"
    child = _new_test_file("child.txt", root=parent)
    service = _service(root)

    with pytest.raises(QuarantineError, match="overlap"):
        service.quarantine_many([str(parent), str(child)])

    assert parent.exists()
    assert child.exists()
    assert _operation_directories(service) == set()


def test_quarantine_many_reports_residual_operation_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _new_test_root()
    first = _new_test_file("first.txt", root=root / "workspace")
    second = _new_test_file("second.txt", root=root / "workspace")
    service = _service(root)
    real_move = shutil.move
    calls = 0

    def fail_forward_and_rollback(source: str, destination: str) -> str:
        nonlocal calls
        calls += 1
        if calls in {2, 3}:
            raise OSError(f"simulated move failure {calls}")
        return real_move(source, destination)

    monkeypatch.setattr("kis_mcp.quarantine.shutil.move", fail_forward_and_rollback)

    with pytest.raises(QuarantineError, match="residual operation IDs"):
        service.quarantine_many([str(first), str(second)])

    assert not first.exists()
    assert second.exists()
    assert len(_operation_directories(service)) == 1


def test_quarantine_failure_cleans_operation_residue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _new_test_root()
    source = _new_test_file("metadata-failure.txt", root=root / "workspace")
    service = _service(root)
    before = _operation_directories(service)

    def fail_metadata_write(_path: Path, _record: object) -> None:
        raise OSError("simulated metadata failure")

    monkeypatch.setattr(service, "_write_metadata", fail_metadata_write)

    with pytest.raises(QuarantineError, match="simulated metadata failure"):
        service.quarantine(str(source))

    assert source.exists()
    assert _operation_directories(service) == before
