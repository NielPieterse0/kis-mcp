from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from kis_mcp.housekeeping import RunnerKind
from kis_mcp.housekeeping_runtime.provider import normalized_runtime_instance
from kis_mcp.housekeeping_runtime.service import HousekeepingRuntimeService
from kis_mcp.housekeeping_runtime.settings import (
    HousekeepingRuntimeSettings,
    HousekeepingTargetSettings,
)
from kis_mcp.housekeeping_runtime.state import HousekeepingStateStore


async def _noop_executor(_invoker, _config, trigger):
    class Receipt:
        def to_json_dict(self):
            return {
                "schema_version": 1,
                "trigger": trigger.to_json_dict(),
                "project_id": "kis-mcp",
                "repository": "NielPieterse0/kis-mcp",
                "complete": True,
                "conflicts": [],
                "findings": [],
                "actions": [],
                "applied_receipts": [],
                "metrics": {},
                "selection": None,
            }

    return Receipt()


def _settings() -> HousekeepingRuntimeSettings:
    target = HousekeepingTargetSettings(
        runner=RunnerKind.BACKLOG_READINESS,
        project_id="kis-mcp",
        repository="NielPieterse0/kis-mcp",
        repository_root="C:\\Projects\\kis-mcp",
        interval_seconds=300,
        initial_delay_seconds=300,
        item_limit=100,
        max_findings=20,
        max_mutations=10,
        max_external_reads=20,
    )
    return HousekeepingRuntimeSettings(
        enabled=True,
        host_instance="kis-op",
        state_namespace="housekeeping",
        receipt_retention=10,
        freshness_stale_after_seconds=900,
        apply_max_age_seconds=300,
        scheduled_mode="preview",
        targets=(target,),
    )


def test_runtime_instance_normalization_matches_remote_runtime() -> None:
    assert normalized_runtime_instance({"KIS_MCP_RUNTIME_INSTANCE": "operation"}) == "kis-op"
    assert normalized_runtime_instance({"KIS_MCP_RUNTIME_INSTANCE": "development"}) == "kis-dev"
    assert normalized_runtime_instance({"KIS_MCP_RUNTIME_INSTANCE": "kis-op"}) == "kis-op"
    assert normalized_runtime_instance({}) == "stdio"


def test_scheduler_starts_only_on_kis_op(tmp_path: Path) -> None:
    async def scenario() -> tuple[bool, bool, bool]:
        dev = HousekeepingRuntimeService(
            _settings(),
            HousekeepingStateStore(tmp_path / "dev", retention=10),
            invoker=object(),
            executor=_noop_executor,
            current_instance="kis-dev",
        )
        op = HousekeepingRuntimeService(
            _settings(),
            HousekeepingStateStore(tmp_path / "op", retention=10),
            invoker=object(),
            executor=_noop_executor,
            current_instance="kis-op",
        )
        dev_started = await dev.start()
        op_started = await op.start()
        active = op.status()["targets"][0]["scheduler_active"]
        await op.stop()
        return dev_started, op_started, active

    assert asyncio.run(scenario()) == (False, True, True)


def test_scheduler_restart_preserves_persisted_cadence(tmp_path: Path) -> None:
    async def scenario() -> str | None:
        now = datetime(2026, 8, 18, 20, 2, tzinfo=timezone.utc)
        store = HousekeepingStateStore(tmp_path, retention=10)
        store.persist_status(
            RunnerKind.BACKLOG_READINESS,
            {
                "runner": RunnerKind.BACKLOG_READINESS.value,
                "next_due_at": datetime(2026, 8, 18, 20, 5, tzinfo=timezone.utc).isoformat(),
            },
        )
        service = HousekeepingRuntimeService(
            _settings(),
            store,
            invoker=object(),
            executor=_noop_executor,
            clock=lambda: now,
            current_instance="kis-op",
        )
        await service.start()
        await asyncio.sleep(0)
        next_due = service.status()["targets"][0]["next_due_at"]
        await service.stop()
        return next_due

    assert asyncio.run(scenario()) == "2026-08-18T20:05:00+00:00"


def test_scheduler_restart_skips_missed_intervals_without_resetting_anchor(tmp_path: Path) -> None:
    async def scenario() -> str | None:
        now = datetime(2026, 8, 18, 20, 2, tzinfo=timezone.utc)
        store = HousekeepingStateStore(tmp_path, retention=10)
        store.persist_status(
            RunnerKind.BACKLOG_READINESS,
            {
                "runner": RunnerKind.BACKLOG_READINESS.value,
                "next_due_at": datetime(2026, 8, 18, 19, 55, tzinfo=timezone.utc).isoformat(),
            },
        )
        service = HousekeepingRuntimeService(
            _settings(), store, invoker=object(), executor=_noop_executor, clock=lambda: now
        )
        await service.start()
        await asyncio.sleep(0)
        next_due = service.status()["targets"][0]["next_due_at"]
        await service.stop()
        return next_due

    assert asyncio.run(scenario()) == "2026-08-18T20:05:00+00:00"
