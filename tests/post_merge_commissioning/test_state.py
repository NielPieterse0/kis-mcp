from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from kis_mcp.commissioning_runtime.state import (
    CommissioningStateError,
    CommissioningStateStore,
)


def test_checkpoint_initialization_is_atomic_and_non_backfill(tmp_path: Path) -> None:
    store = CommissioningStateStore(tmp_path, retention=2)
    now = datetime(2026, 8, 21, 15, 0, tzinfo=UTC)

    checkpoint, created = store.initialize_checkpoint("NielPieterse0/kis-mcp", now)
    repeated, repeated_created = store.initialize_checkpoint(
        "NielPieterse0/kis-mcp", now + timedelta(hours=1)
    )

    assert created is True
    assert repeated_created is False
    assert checkpoint == repeated == now
    assert not list(tmp_path.rglob("*.tmp"))


def test_corrupt_checkpoint_fails_closed_and_is_recoverable(tmp_path: Path) -> None:
    store = CommissioningStateStore(tmp_path, retention=2)
    repository = "NielPieterse0/kis-mcp"
    path = store.checkpoint_path(repository)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(CommissioningStateError, match="checkpoint_invalid"):
        store.load_checkpoint(repository)

    recovered = store.recover_checkpoint(
        repository, datetime(2026, 8, 21, 15, 5, tzinfo=UTC)
    )
    assert recovered.isoformat() == "2026-08-21T15:05:00+00:00"
    assert list(path.parent.glob(path.stem + ".corrupt.*.json"))


def test_receipts_are_deduplicated_bounded_and_loadable(tmp_path: Path) -> None:
    store = CommissioningStateStore(tmp_path, retention=2)
    now = datetime(2026, 8, 21, 15, 0, tzinfo=UTC)
    refs = []
    for index in range(3):
        refs.append(
            store.persist_receipt(
                {
                    "schema_version": 1,
                    "kind": "run",
                    "occurred_at": (now + timedelta(seconds=index)).isoformat(),
                    "complete": True,
                    "candidate_count": index,
                    "outcomes": [],
                },
                now + timedelta(seconds=index),
            )
        )

    assert len(list((tmp_path / "receipts").glob("*.json"))) == 2
    assert store.load_receipt(refs[-1].receipt_id)["candidate_count"] == 2

    duplicate = store.persist_receipt(
        store.load_receipt(refs[-1].receipt_id), now + timedelta(minutes=1)
    )
    assert duplicate.receipt_id == refs[-1].receipt_id


def test_checkpoint_payload_rejects_unknown_or_unbounded_shape(tmp_path: Path) -> None:
    store = CommissioningStateStore(tmp_path, retention=2)
    repository = "NielPieterse0/kis-mcp"
    path = store.checkpoint_path(repository)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "initialized_at": "2026-08-21T15:00:00+00:00",
                "checkpoint_at": "2026-08-21T15:00:00+00:00",
                "unexpected": "x",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CommissioningStateError, match="checkpoint_invalid"):
        store.load_checkpoint(repository)
