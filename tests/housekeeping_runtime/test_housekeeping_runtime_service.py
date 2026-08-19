from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kis_mcp.housekeeping import HousekeepingTrigger, RunMode, RunnerKind, TriggerKind
from kis_mcp.housekeeping_runtime.service import (
    HousekeepingApplyError,
    HousekeepingRuntimeService,
)
from kis_mcp.housekeeping_runtime.settings import (
    HousekeepingRuntimeSettings,
    HousekeepingTargetSettings,
)
from kis_mcp.housekeeping_runtime.state import HousekeepingStateStore


class DummyReceipt:
    def __init__(self, trigger: HousekeepingTrigger, *, action: str = "ready") -> None:
        self.trigger = trigger
        self.action = action

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "trigger": self.trigger.to_json_dict(),
            "project_id": "kis-mcp",
            "repository": "NielPieterse0/kis-mcp",
            "complete": True,
            "conflicts": [],
            "findings": [],
            "actions": [
                {
                    "action_id": "a-1",
                    "operation": "project_management_transition_work",
                    "arguments": {"status": self.action, "number": 1},
                    "rationale": "ready",
                    "safe_to_apply": True,
                }
            ],
            "applied_receipts": [],
            "metrics": {},
            "selection": None,
        }


def _settings() -> HousekeepingRuntimeSettings:
    return HousekeepingRuntimeSettings(
        schema_version=1,
        enabled=True,
        host_instance="kis-op",
        state_namespace="housekeeping",
        receipt_retention=20,
        freshness_stale_after_seconds=300,
        apply_max_age_seconds=120,
        scheduled_mode="preview",
        targets=(
            HousekeepingTargetSettings(
                runner=RunnerKind.BACKLOG_READINESS,
                project_id="kis-mcp",
                repository="NielPieterse0/kis-mcp",
                repository_root="C:\\Projects\\kis-mcp",
                interval_seconds=300,
                initial_delay_seconds=0,
                item_limit=1000,
                max_findings=200,
                max_mutations=20,
                max_external_reads=100,
            ),
        ),
    )


class RecordingExecutor:
    def __init__(self) -> None:
        self.triggers: list[HousekeepingTrigger] = []
        self.next_action = "ready"
        self.fail = False

    async def __call__(self, _invoker, _config, trigger: HousekeepingTrigger):
        self.triggers.append(trigger)
        if self.fail:
            raise RuntimeError("provider details must not be persisted")
        return DummyReceipt(trigger, action=self.next_action)


def test_scheduled_run_is_preview_only_and_persists_fresh_status(tmp_path: Path) -> None:
    now = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)
    executor = RecordingExecutor()
    store = HousekeepingStateStore(tmp_path, retention=20)
    service = HousekeepingRuntimeService(
        _settings(), store, invoker=object(), executor=executor, clock=lambda: now
    )

    result = asyncio.run(
        service.run_scheduled_once(RunnerKind.BACKLOG_READINESS, scheduled_for=now)
    )

    assert result["complete"] is True
    assert executor.triggers[-1].mode is RunMode.PREVIEW
    assert executor.triggers[-1].trigger_kind is TriggerKind.SCHEDULED
    status = service.status()["targets"][0]
    assert status["freshness"] == "fresh"
    assert status["last_success_receipt_id"]


def test_runner_failure_is_persisted_without_provider_detail(tmp_path: Path) -> None:
    now = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)
    executor = RecordingExecutor()
    executor.fail = True
    store = HousekeepingStateStore(tmp_path, retention=20)
    service = HousekeepingRuntimeService(
        _settings(), store, invoker=object(), executor=executor, clock=lambda: now
    )

    result = asyncio.run(
        service.run_scheduled_once(RunnerKind.BACKLOG_READINESS, scheduled_for=now)
    )
    assert result["complete"] is False
    assert result["error_type"] == "RuntimeError"
    failure = store.load_receipt(result["failure_receipt_id"])
    assert "provider details" not in str(failure)
    assert service.status()["targets"][0]["freshness"] == "failed"


def test_status_becomes_stale_after_freshness_threshold(tmp_path: Path) -> None:
    now = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)
    current = [now]
    service = HousekeepingRuntimeService(
        _settings(),
        HousekeepingStateStore(tmp_path, retention=20),
        invoker=object(),
        executor=RecordingExecutor(),
        clock=lambda: current[0],
    )
    asyncio.run(
        service.run_scheduled_once(RunnerKind.BACKLOG_READINESS, scheduled_for=now)
    )
    current[0] = now + timedelta(seconds=301)

    assert service.status()["targets"][0]["freshness"] == "stale"


def test_apply_requires_fresh_unchanged_preview_and_uses_stable_key(tmp_path: Path) -> None:
    now = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)
    executor = RecordingExecutor()
    service = HousekeepingRuntimeService(
        _settings(),
        HousekeepingStateStore(tmp_path, retention=20),
        invoker=object(),
        executor=executor,
        clock=lambda: now,
    )
    preview = asyncio.run(
        service.run_scheduled_once(RunnerKind.BACKLOG_READINESS, scheduled_for=now)
    )
    receipt_id = preview["receipt_id"]

    applied = asyncio.run(service.apply_receipt(receipt_id))
    first_key = executor.triggers[-1].idempotency_key
    retried = asyncio.run(service.apply_receipt(receipt_id))

    assert applied["complete"] is True
    assert retried["complete"] is True
    assert executor.triggers[-1].mode is RunMode.APPLY
    assert executor.triggers[-1].idempotency_key == first_key
    assert first_key and first_key.startswith("housekeeping:backlog_readiness:")


def test_apply_rejects_changed_or_stale_preview(tmp_path: Path) -> None:
    now = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)
    current = [now]
    executor = RecordingExecutor()
    service = HousekeepingRuntimeService(
        _settings(),
        HousekeepingStateStore(tmp_path, retention=20),
        invoker=object(),
        executor=executor,
        clock=lambda: current[0],
    )
    preview = asyncio.run(
        service.run_scheduled_once(RunnerKind.BACKLOG_READINESS, scheduled_for=now)
    )
    executor.next_action = "blocked"
    with pytest.raises(HousekeepingApplyError, match="changed since preview"):
        asyncio.run(service.apply_receipt(preview["receipt_id"]))

    executor.next_action = "ready"
    current[0] = now + timedelta(seconds=121)
    with pytest.raises(HousekeepingApplyError, match="stale"):
        asyncio.run(service.apply_receipt(preview["receipt_id"]))


def test_apply_is_rejected_outside_kis_op(tmp_path: Path) -> None:
    now = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)
    executor = RecordingExecutor()
    store = HousekeepingStateStore(tmp_path, retention=20)
    op = HousekeepingRuntimeService(
        _settings(), store, invoker=object(), executor=executor, clock=lambda: now
    )
    preview = asyncio.run(
        op.run_scheduled_once(RunnerKind.BACKLOG_READINESS, scheduled_for=now)
    )
    dev = HousekeepingRuntimeService(
        _settings(),
        store,
        invoker=object(),
        executor=executor,
        clock=lambda: now,
        current_instance="kis-dev",
    )

    with pytest.raises(HousekeepingApplyError, match="only on kis-op"):
        asyncio.run(dev.apply_receipt(preview["receipt_id"]))


def test_apply_rejects_non_preview_or_mismatched_target_receipt(tmp_path: Path) -> None:
    now = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)
    store = HousekeepingStateStore(tmp_path, retention=20)
    service = HousekeepingRuntimeService(
        _settings(), store, invoker=object(), executor=RecordingExecutor(), clock=lambda: now
    )
    preview = asyncio.run(
        service.run_scheduled_once(RunnerKind.BACKLOG_READINESS, scheduled_for=now)
    )
    payload = store.load_receipt(preview["receipt_id"])

    wrong_target = dict(payload)
    wrong_target["project_id"] = "other-project"
    wrong_ref = store.persist_receipt(
        RunnerKind.BACKLOG_READINESS, "preview", wrong_target, now
    )
    with pytest.raises(HousekeepingApplyError, match="target does not match"):
        asyncio.run(service.apply_receipt(wrong_ref.receipt_id))

    wrong_mode = dict(payload)
    wrong_mode["trigger"] = dict(payload["trigger"])
    wrong_mode["trigger"]["mode"] = "apply"
    mode_ref = store.persist_receipt(
        RunnerKind.BACKLOG_READINESS, "preview", wrong_mode, now
    )
    with pytest.raises(HousekeepingApplyError, match="must be preview"):
        asyncio.run(service.apply_receipt(mode_ref.receipt_id))
