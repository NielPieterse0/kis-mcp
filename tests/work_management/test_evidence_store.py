from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from kis_mcp.work_management import (
    EvidenceWriteDisposition,
    ReviewArtifactKind,
    ReviewEvidenceStore,
    create_review_evidence_manifest,
)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_writes_review_artifact_atomically_and_reads_it(tmp_path: Path) -> None:
    store = ReviewEvidenceStore(tmp_path, max_file_bytes=1024, max_total_bytes=4096)
    manifest = create_review_evidence_manifest("REV-100")

    result = store.write_artifact(
        manifest,
        ReviewArtifactKind.REPORT,
        "# Review\n\nComplete.\n",
    )

    assert result.disposition is EvidenceWriteDisposition.CREATED
    assert result.sha256 == digest(b"# Review\n\nComplete.\n")
    assert store.read_artifact(manifest, ReviewArtifactKind.REPORT) == b"# Review\n\nComplete.\n"
    assert result.path == ".work/reviews/REV-100/report.md"


def test_identical_replay_is_idempotent(tmp_path: Path) -> None:
    store = ReviewEvidenceStore(tmp_path)
    manifest = create_review_evidence_manifest("REV-101")
    first = store.write_artifact(manifest, ReviewArtifactKind.RESULT, b"{}\n")

    repeated = store.write_artifact(manifest, ReviewArtifactKind.RESULT, b"{}\n")

    assert first.disposition is EvidenceWriteDisposition.CREATED
    assert repeated.disposition is EvidenceWriteDisposition.UNCHANGED
    assert repeated.previous_sha256 == first.sha256


def test_conflicting_replay_does_not_overwrite_without_expected_hash(tmp_path: Path) -> None:
    store = ReviewEvidenceStore(tmp_path)
    manifest = create_review_evidence_manifest("REV-102")
    store.write_artifact(manifest, ReviewArtifactKind.COVERAGE, b'{"complete": false}\n')

    conflict = store.write_artifact(
        manifest,
        ReviewArtifactKind.COVERAGE,
        b'{"complete": true}\n',
    )

    assert conflict.disposition is EvidenceWriteDisposition.CONFLICT
    assert store.read_artifact(manifest, ReviewArtifactKind.COVERAGE) == b'{"complete": false}\n'


def test_expected_hash_allows_optimistic_update(tmp_path: Path) -> None:
    store = ReviewEvidenceStore(tmp_path)
    manifest = create_review_evidence_manifest("REV-103")
    original = b'{"status": "running"}\n'
    updated = b'{"status": "completed"}\n'
    created = store.write_artifact(manifest, ReviewArtifactKind.CLOSEOUT, original)

    result = store.write_artifact(
        manifest,
        ReviewArtifactKind.CLOSEOUT,
        updated,
        expected_sha256=created.sha256,
    )

    assert result.disposition is EvidenceWriteDisposition.UPDATED
    assert result.previous_sha256 == digest(original)
    assert store.read_artifact(manifest, ReviewArtifactKind.CLOSEOUT) == updated


def test_rejects_file_and_bundle_budget_overflow(tmp_path: Path) -> None:
    store = ReviewEvidenceStore(tmp_path, max_file_bytes=4, max_total_bytes=6)
    manifest = create_review_evidence_manifest("REV-104")

    with pytest.raises(ValueError, match="max_file_bytes"):
        store.write_artifact(manifest, ReviewArtifactKind.REPORT, b"12345")

    with pytest.raises(ValueError, match="max_total_bytes"):
        store.write_bundle(
            manifest,
            {
                ReviewArtifactKind.REQUEST: b"1234",
                ReviewArtifactKind.REPORT: b"5678",
            },
        )


def test_failed_replace_preserves_prior_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ReviewEvidenceStore(tmp_path)
    manifest = create_review_evidence_manifest("REV-105")
    created = store.write_artifact(manifest, ReviewArtifactKind.REPORT, b"before\n")

    def fail_replace(source: str | bytes | Path, destination: str | bytes | Path) -> None:
        del source, destination
        raise OSError("replace failed")

    monkeypatch.setattr("kis_mcp.work_management.evidence.os.replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        store.write_artifact(
            manifest,
            ReviewArtifactKind.REPORT,
            b"after\n",
            expected_sha256=created.sha256,
        )

    assert store.read_artifact(manifest, ReviewArtifactKind.REPORT) == b"before\n"


def test_bundle_preflight_reports_conflict_without_partial_writes(tmp_path: Path) -> None:
    store = ReviewEvidenceStore(tmp_path)
    manifest = create_review_evidence_manifest("REV-106")
    store.write_artifact(manifest, ReviewArtifactKind.REQUEST, b"old-request\n")

    results = store.write_bundle(
        manifest,
        {
            ReviewArtifactKind.REQUEST: b"new-request\n",
            ReviewArtifactKind.REPORT: b"new-report\n",
        },
    )

    assert results[ReviewArtifactKind.REQUEST].disposition is EvidenceWriteDisposition.CONFLICT
    assert results[ReviewArtifactKind.REPORT].disposition is EvidenceWriteDisposition.NOT_WRITTEN
    assert not (tmp_path / ".work" / "reviews" / "REV-106" / "report.md").exists()


def test_bundle_total_budget_is_checked_before_any_write(tmp_path: Path) -> None:
    store = ReviewEvidenceStore(tmp_path, max_file_bytes=4, max_total_bytes=6)
    manifest = create_review_evidence_manifest("REV-107")
    store.write_artifact(manifest, ReviewArtifactKind.REQUEST, b"1234")

    with pytest.raises(ValueError, match="max_total_bytes"):
        store.write_bundle(
            manifest,
            {
                ReviewArtifactKind.REPORT: b"56",
                ReviewArtifactKind.COVERAGE: b"78",
            },
        )

    review_root = tmp_path / ".work" / "reviews" / "REV-107"
    assert not (review_root / "report.md").exists()
    assert not (review_root / "coverage.json").exists()
