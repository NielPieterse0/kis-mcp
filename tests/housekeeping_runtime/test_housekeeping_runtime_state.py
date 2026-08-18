from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from kis_mcp.housekeeping import RunnerKind
from kis_mcp.housekeeping_runtime.state import (
    HousekeepingStateStore,
    derive_apply_idempotency_key,
    plan_fingerprint,
)


def _receipt(action_value: str = "ready") -> dict[str, object]:
    return {
        "schema_version": 1,
        "trigger": {
            "runner": "backlog_readiness",
            "mode": "preview",
            "trigger_kind": "scheduled",
            "trigger_id": "scheduled-1",
            "scheduled_for": "2026-08-18T20:00:00Z",
        },
        "project_id": "kis-mcp",
        "repository": "NielPieterse0/kis-mcp",
        "complete": True,
        "conflicts": [],
        "actions": [
            {
                "action_id": "a-1",
                "operation": "project_management_transition_work",
                "arguments": {"status": action_value, "number": 1},
                "rationale": "ready",
                "safe_to_apply": True,
            }
        ],
    }


def test_plan_fingerprint_and_apply_key_are_stable() -> None:
    receipt = _receipt()
    fingerprint = plan_fingerprint(receipt)
    reordered = dict(reversed(list(receipt.items())))

    assert plan_fingerprint(reordered) == fingerprint
    assert derive_apply_idempotency_key(receipt) == (
        f"housekeeping:backlog_readiness:{fingerprint}"
    )
    assert plan_fingerprint(_receipt("blocked")) != fingerprint


def test_receipt_store_is_atomic_loadable_and_bounded(tmp_path: Path) -> None:
    store = HousekeepingStateStore(tmp_path, retention=2)
    runner = RunnerKind.BACKLOG_READINESS
    now = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)

    refs = []
    for index in range(3):
        payload = _receipt(str(index))
        refs.append(
            store.persist_receipt(runner, "preview", payload, now + timedelta(seconds=index))
        )

    assert store.load_receipt(refs[-1].receipt_id) == _receipt("2")
    receipt_files = list((tmp_path / "receipts" / runner.value).glob("*.json"))
    assert len(receipt_files) == 2
    assert not list(tmp_path.rglob("*.tmp"))


def test_failure_and_status_persist_only_bounded_diagnostics(tmp_path: Path) -> None:
    store = HousekeepingStateStore(tmp_path, retention=5)
    runner = RunnerKind.WORK_MANAGEMENT_RECONCILIATION
    now = datetime(2026, 8, 18, 20, 5, tzinfo=timezone.utc)

    failure = store.persist_failure(runner, "RuntimeError", now)
    store.persist_status(
        runner,
        {
            "runner": runner.value,
            "last_attempt_at": now.isoformat(),
            "last_failure_receipt_id": failure.receipt_id,
        },
    )

    loaded_failure = store.load_receipt(failure.receipt_id)
    assert loaded_failure == {
        "schema_version": 1,
        "runner": runner.value,
        "kind": "failure",
        "occurred_at": now.isoformat(),
        "error_type": "RuntimeError",
    }
    assert store.load_status(runner)["last_failure_receipt_id"] == failure.receipt_id


def test_identical_receipt_payload_is_deduplicated(tmp_path: Path) -> None:
    store = HousekeepingStateStore(tmp_path, retention=5)
    runner = RunnerKind.BACKLOG_READINESS
    payload = _receipt()
    first = store.persist_receipt(
        runner,
        "preview",
        payload,
        datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc),
    )
    second = store.persist_receipt(
        runner,
        "preview",
        payload,
        datetime(2026, 8, 18, 20, 1, tzinfo=timezone.utc),
    )

    assert second.receipt_id == first.receipt_id
    assert second.path == first.path
    assert len(list((tmp_path / "receipts" / runner.value).glob("*.json"))) == 1
    assert store.load_receipt(first.receipt_id) == payload
