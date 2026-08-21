from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from kis_mcp.commissioning_runtime.state import (
    CommissioningStateError,
    CommissioningStateStore,
    ExecutionResult,
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


def test_execution_state_is_resumable_and_terminal_replay_is_idempotent(tmp_path: Path) -> None:
    store = CommissioningStateStore(tmp_path, retention=4)
    now = datetime(2026, 8, 21, 16, 0, tzinfo=UTC)
    key = "commission:nielpieterse0/kis-mcp:" + "a" * 40 + ":work-management"

    initial = store.begin_execution(key, "f" * 64, now)
    assert initial.attempt == 1
    assert initial.phase == "initialized"
    assert initial.result is ExecutionResult.PENDING

    proof = store.update_execution(
        initial,
        phase="proof_persisted",
        result=ExecutionResult.PENDING,
        receipt_id="post-merge-commissioning:" + "b" * 64,
        updated_at=now + timedelta(seconds=1),
    )
    resumed = store.begin_execution(key, "f" * 64, now + timedelta(seconds=2))
    assert resumed == proof

    passed = store.update_execution(
        resumed,
        phase="terminal",
        result=ExecutionResult.PASSED,
        receipt_id=resumed.receipt_id,
        updated_at=now + timedelta(seconds=3),
    )
    replay = store.begin_execution(key, "f" * 64, now + timedelta(minutes=1), retry=True)
    assert replay == passed


def test_failed_or_blocked_execution_requires_explicit_retry(tmp_path: Path) -> None:
    store = CommissioningStateStore(tmp_path, retention=4)
    now = datetime(2026, 8, 21, 16, 0, tzinfo=UTC)
    key = "commission:nielpieterse0/kis-mcp:" + "c" * 40 + ":gateway-runtime"
    state = store.begin_execution(key, "d" * 64, now)
    blocked = store.update_execution(
        state,
        phase="terminal",
        result=ExecutionResult.BLOCKED,
        receipt_id="post-merge-commissioning:" + "e" * 64,
        updated_at=now + timedelta(seconds=1),
    )

    assert store.begin_execution(key, "d" * 64, now + timedelta(seconds=2)) == blocked
    retried = store.begin_execution(
        key, "d" * 64, now + timedelta(seconds=3), retry=True
    )
    assert retried.attempt == 2
    assert retried.phase == "initialized"
    assert retried.result is ExecutionResult.PENDING
    assert retried.receipt_id is None


def test_execution_contract_fingerprint_cannot_drift(tmp_path: Path) -> None:
    store = CommissioningStateStore(tmp_path, retention=4)
    now = datetime(2026, 8, 21, 16, 0, tzinfo=UTC)
    key = "commission:nielpieterse0/kis-mcp:" + "f" * 40 + ":provider-runtime"
    store.begin_execution(key, "1" * 64, now)

    with pytest.raises(CommissioningStateError, match="execution_contract_mismatch"):
        store.begin_execution(key, "2" * 64, now + timedelta(seconds=1))
