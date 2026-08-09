from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.evidence import (
    EvidenceConflictError,
    EvidenceCorruptionError,
    EvidenceStore,
    EvidenceWriteDisposition,
)


def _store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(tmp_path, max_file_bytes=1024, max_total_bytes=8192)


def test_generation_is_atomic_versioned_and_hash_verified(tmp_path: Path) -> None:
    store = _store(tmp_path)
    result = store.write_generation(
        "discover/projects/demo",
        metadata={"project_id": "demo", "source_fingerprint": "abc"},
        artifacts={"code-atlas.json": b'{"modules":[]}\n'},
    )

    assert result.disposition is EvidenceWriteDisposition.CREATED
    current = store.read_current_generation("discover/projects/demo")
    assert current.generation_id == result.generation_id
    assert current.metadata["project_id"] == "demo"
    assert current.artifacts["code-atlas.json"] == b'{"modules":[]}\n'


def test_identical_generation_reuses_existing_content(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.write_generation(
        "discover/projects/demo",
        metadata={"project_id": "demo", "source_fingerprint": "same"},
        artifacts={"symbols.json": b"[]\n"},
    )
    second = store.write_generation(
        "discover/projects/demo",
        metadata={"project_id": "demo", "source_fingerprint": "same"},
        artifacts={"symbols.json": b"[]\n"},
        expected_current_generation=first.generation_id,
    )

    assert second.generation_id == first.generation_id
    assert second.disposition is EvidenceWriteDisposition.UNCHANGED


def test_expected_generation_conflict_does_not_publish(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.write_generation(
        "discover/projects/demo",
        metadata={"source_fingerprint": "one"},
        artifacts={"graph.json": b"[]\n"},
    )

    with pytest.raises(EvidenceConflictError):
        store.write_generation(
            "discover/projects/demo",
            metadata={"source_fingerprint": "two"},
            artifacts={"graph.json": b"[1]\n"},
            expected_current_generation="0" * 64,
        )

    assert store.read_current_generation("discover/projects/demo").generation_id == first.generation_id


def test_corrupt_artifact_is_detected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    result = store.write_generation(
        "discover/projects/demo",
        metadata={"source_fingerprint": "one"},
        artifacts={"graph.json": b"[]\n"},
    )
    artifact = (
        tmp_path
        / "discover"
        / "projects"
        / "demo"
        / "generations"
        / result.generation_id
        / "graph.json"
    )
    artifact.write_bytes(b"corrupt\n")

    with pytest.raises(EvidenceCorruptionError, match="sha256"):
        store.read_current_generation("discover/projects/demo")


def test_superseded_generation_remains_recoverable(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.write_generation(
        "discover/projects/demo",
        metadata={"source_fingerprint": "one"},
        artifacts={"graph.json": b"[]\n"},
    )
    second = store.write_generation(
        "discover/projects/demo",
        metadata={"source_fingerprint": "two"},
        artifacts={"graph.json": b"[1]\n"},
        expected_current_generation=first.generation_id,
    )

    assert second.generation_id != first.generation_id
    assert store.read_generation("discover/projects/demo", first.generation_id).metadata["source_fingerprint"] == "one"
    assert store.read_current_generation("discover/projects/demo").generation_id == second.generation_id


def test_generation_rejects_unsafe_paths_and_budget_overflow(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path, max_file_bytes=4, max_total_bytes=6)
    with pytest.raises(ValueError, match="artifact path"):
        store.write_generation("discover/demo", metadata={}, artifacts={"../escape": b"x"})
    with pytest.raises(ValueError, match="max_file_bytes"):
        store.write_generation("discover/demo", metadata={}, artifacts={"large.bin": b"12345"})
    with pytest.raises(ValueError, match="max_total_bytes"):
        store.write_generation(
            "discover/demo",
            metadata={},
            artifacts={"one": b"1234", "two": b"5678"},
        )
