from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from kis_mcp.housekeeping import (
    HousekeepingRunConfig,
    HousekeepingTrigger,
    RunMode,
    RunnerKind,
    TriggerKind,
    run_backlog_readiness,
    run_work_management_reconciliation,
)
from kis_mcp.housekeeping.operations import OperationInvoker

from .settings import HousekeepingRuntimeSettings, HousekeepingTargetSettings
from .state import (
    HousekeepingStateStore,
    derive_apply_idempotency_key,
    plan_fingerprint,
)


class ReceiptLike(Protocol):
    def to_json_dict(self) -> dict[str, Any]: ...


RunnerExecutor = Callable[
    [OperationInvoker, HousekeepingRunConfig, HousekeepingTrigger],
    Awaitable[ReceiptLike],
]
Clock = Callable[[], datetime]
Sleep = Callable[[float], Awaitable[None]]


class HousekeepingApplyError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def execute_housekeeping_runner(
    invoker: OperationInvoker,
    config: HousekeepingRunConfig,
    trigger: HousekeepingTrigger,
) -> ReceiptLike:
    if trigger.runner is RunnerKind.WORK_MANAGEMENT_RECONCILIATION:
        return await run_work_management_reconciliation(invoker, config, trigger)
    if trigger.runner is RunnerKind.BACKLOG_READINESS:
        return await run_backlog_readiness(invoker, config, trigger)
    raise ValueError(f"unsupported housekeeping runner: {trigger.runner}")


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def _parse_iso(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise HousekeepingApplyError(f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HousekeepingApplyError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise HousekeepingApplyError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _run_config(target: HousekeepingTargetSettings) -> HousekeepingRunConfig:
    return HousekeepingRunConfig(
        project_id=target.project_id,
        repository=target.repository,
        repository_root=Path(target.repository_root),
        item_limit=target.item_limit,
        max_findings=target.max_findings,
        max_mutations=target.max_mutations,
        max_external_reads=target.max_external_reads,
    )


def _receipt_is_applicable(receipt: Mapping[str, Any]) -> None:
    if receipt.get("complete") is not True:
        raise HousekeepingApplyError("preview is incomplete")
    conflicts = receipt.get("conflicts")
    if not isinstance(conflicts, list) or conflicts:
        raise HousekeepingApplyError("preview has conflicts")
    actions = receipt.get("actions")
    if not isinstance(actions, list) or not actions:
        raise HousekeepingApplyError("preview has no actionable plan")
    if any(
        not isinstance(item, Mapping) or item.get("safe_to_apply") is not True
        for item in actions
    ):
        raise HousekeepingApplyError("preview contains an unsafe action")


class HousekeepingRuntimeService:
    def __init__(
        self,
        settings: HousekeepingRuntimeSettings,
        store: HousekeepingStateStore,
        *,
        invoker: OperationInvoker,
        executor: RunnerExecutor = execute_housekeeping_runner,
        clock: Clock = utc_now,
        sleep: Sleep = asyncio.sleep,
        current_instance: str = "kis-op",
    ) -> None:
        self.settings = settings
        self.store = store
        self.invoker = invoker
        self.executor = executor
        self.clock = clock
        self.sleep = sleep
        self.current_instance = current_instance
        self._tasks: dict[RunnerKind, asyncio.Task[None]] = {}
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def _base_status(self, target: HousekeepingTargetSettings) -> dict[str, Any]:
        previous = self.store.load_status(target.runner)
        return {
            "schema_version": 1,
            "runner": target.runner.value,
            "host_instance": self.settings.host_instance,
            "interval_seconds": target.interval_seconds,
            "initial_delay_seconds": target.initial_delay_seconds,
            "last_attempt_at": previous.get("last_attempt_at"),
            "last_success_at": previous.get("last_success_at"),
            "last_success_receipt_id": previous.get("last_success_receipt_id"),
            "last_failure_at": previous.get("last_failure_at"),
            "last_failure_receipt_id": previous.get("last_failure_receipt_id"),
            "next_due_at": previous.get("next_due_at"),
        }

    def _persist_success(
        self,
        target: HousekeepingTargetSettings,
        now: datetime,
        receipt_id: str,
    ) -> None:
        status = self._base_status(target)
        status.update(
            last_attempt_at=_iso(now),
            last_success_at=_iso(now),
            last_success_receipt_id=receipt_id,
        )
        self.store.persist_status(target.runner, status)

    def _persist_failure(
        self,
        target: HousekeepingTargetSettings,
        now: datetime,
        receipt_id: str,
    ) -> None:
        status = self._base_status(target)
        status.update(
            last_attempt_at=_iso(now),
            last_failure_at=_iso(now),
            last_failure_receipt_id=receipt_id,
        )
        self.store.persist_status(target.runner, status)

    def _persist_next_due(
        self,
        target: HousekeepingTargetSettings,
        due: datetime,
    ) -> None:
        status = self._base_status(target)
        status["next_due_at"] = _iso(due)
        self.store.persist_status(target.runner, status)

    async def run_scheduled_once(
        self,
        runner: RunnerKind,
        *,
        scheduled_for: datetime,
    ) -> dict[str, Any]:
        target = self.settings.target(runner)
        trigger = HousekeepingTrigger(
            runner=target.runner,
            mode=RunMode.PREVIEW,
            trigger_kind=TriggerKind.SCHEDULED,
            trigger_id=f"scheduled:{target.runner.value}:{_iso(scheduled_for)}",
            scheduled_for=_iso(scheduled_for),
        )
        now = self.clock()
        try:
            receipt = await self.executor(self.invoker, _run_config(target), trigger)
            payload = receipt.to_json_dict()
            reference = self.store.persist_receipt(
                target.runner, "preview", payload, now
            )
            if payload.get("complete") is True:
                self._persist_success(target, now, reference.receipt_id)
            else:
                self._persist_failure(target, now, reference.receipt_id)
            return {
                "complete": bool(payload.get("complete")),
                "receipt_id": reference.receipt_id,
                "receipt": payload,
            }
        except Exception as exc:
            failure = self.store.persist_failure(target.runner, type(exc).__name__, now)
            self._persist_failure(target, now, failure.receipt_id)
            return {
                "complete": False,
                "error_type": type(exc).__name__,
                "failure_receipt_id": failure.receipt_id,
            }

    def _freshness(self, target: HousekeepingTargetSettings) -> tuple[str, int | None]:
        if not self.settings.enabled or self.current_instance != self.settings.host_instance:
            return "disabled", None
        status = self.store.load_status(target.runner)
        last_success = status.get("last_success_at")
        last_failure = status.get("last_failure_at")
        if isinstance(last_failure, str) and (
            not isinstance(last_success, str) or last_failure >= last_success
        ):
            return "failed", None
        if not isinstance(last_success, str):
            return "never", None
        succeeded_at = _parse_iso(last_success, "last_success_at")
        age = max(0, int((self.clock() - succeeded_at).total_seconds()))
        if age > self.settings.freshness_stale_after_seconds:
            return "stale", age
        return "fresh", age

    def receipt(self, receipt_id: str) -> dict[str, Any]:
        return self.store.load_receipt(receipt_id)

    def status(self) -> dict[str, Any]:
        targets: list[dict[str, Any]] = []
        for target in self.settings.targets:
            persisted = self._base_status(target)
            freshness, age = self._freshness(target)
            persisted.update(
                freshness=freshness,
                age_seconds=age,
                scheduler_active=target.runner in self._tasks,
            )
            targets.append(persisted)
        return {
            "schema_version": 1,
            "enabled": self.settings.enabled,
            "host_instance": self.settings.host_instance,
            "current_instance": self.current_instance,
            "active": self.active,
            "targets": targets,
        }

    @staticmethod
    def _receipt_runner(receipt: Mapping[str, Any]) -> RunnerKind:
        trigger = receipt.get("trigger")
        if not isinstance(trigger, Mapping):
            raise HousekeepingApplyError("preview trigger is missing")
        raw_runner = trigger.get("runner")
        try:
            return RunnerKind(raw_runner)
        except (TypeError, ValueError) as exc:
            raise HousekeepingApplyError("preview runner is invalid") from exc

    @staticmethod
    def _validate_preview_identity(
        receipt: Mapping[str, Any], target: HousekeepingTargetSettings
    ) -> None:
        trigger = receipt.get("trigger")
        if not isinstance(trigger, Mapping):
            raise HousekeepingApplyError("preview trigger is missing")
        if trigger.get("mode") != RunMode.PREVIEW.value:
            raise HousekeepingApplyError("receipt trigger mode must be preview")
        if (
            receipt.get("project_id") != target.project_id
            or receipt.get("repository") != target.repository
        ):
            raise HousekeepingApplyError("preview target does not match configured target")

    def _validate_apply_age(self, receipt: Mapping[str, Any]) -> None:
        trigger = receipt.get("trigger")
        if not isinstance(trigger, Mapping):
            raise HousekeepingApplyError("preview trigger is missing")
        occurred_at = _parse_iso(trigger.get("scheduled_for"), "preview scheduled_for")
        age = (self.clock() - occurred_at).total_seconds()
        if age < 0 or age > self.settings.apply_max_age_seconds:
            raise HousekeepingApplyError("preview is stale")

    async def apply_receipt(self, receipt_id: str) -> dict[str, Any]:
        if self.current_instance != self.settings.host_instance:
            raise HousekeepingApplyError("apply is available only on kis-op")
        stored = self.store.load_receipt(receipt_id)
        _receipt_is_applicable(stored)
        runner = self._receipt_runner(stored)
        target = self.settings.target(runner)
        self._validate_preview_identity(stored, target)
        self._validate_apply_age(stored)
        fingerprint = plan_fingerprint(stored)
        preflight_trigger = HousekeepingTrigger(
            runner=runner,
            mode=RunMode.PREVIEW,
            trigger_kind=TriggerKind.MANUAL,
            trigger_id=f"apply-preflight:{fingerprint[:16]}",
        )
        try:
            preflight = await self.executor(
                self.invoker, _run_config(target), preflight_trigger
            )
        except Exception as exc:
            now = self.clock()
            failure = self.store.persist_failure(runner, type(exc).__name__, now)
            raise HousekeepingApplyError(
                f"apply preflight failed: {failure.receipt_id}"
            ) from exc
        current = preflight.to_json_dict()
        _receipt_is_applicable(current)
        if plan_fingerprint(current) != fingerprint:
            raise HousekeepingApplyError("actionable plan changed since preview")

        key = derive_apply_idempotency_key(stored)
        apply_trigger = HousekeepingTrigger(
            runner=runner,
            mode=RunMode.APPLY,
            trigger_kind=TriggerKind.MANUAL,
            trigger_id=f"apply:{fingerprint[:16]}",
            idempotency_key=key,
        )
        try:
            applied = await self.executor(self.invoker, _run_config(target), apply_trigger)
            payload = applied.to_json_dict()
        except Exception as exc:
            now = self.clock()
            failure = self.store.persist_failure(runner, type(exc).__name__, now)
            raise HousekeepingApplyError(
                f"apply execution failed: {failure.receipt_id}"
            ) from exc
        reference = self.store.persist_receipt(
            runner, "apply", payload, self.clock()
        )
        return {
            "complete": bool(payload.get("complete")),
            "receipt_id": reference.receipt_id,
            "idempotency_key": key,
            "receipt": payload,
        }

    def _resume_due(self, target: HousekeepingTargetSettings) -> datetime:
        now = self.clock()
        persisted = self.store.load_status(target.runner).get("next_due_at")
        if isinstance(persisted, str):
            try:
                due = _parse_iso(persisted, "next_due_at")
            except HousekeepingApplyError:
                due = now + timedelta(seconds=target.initial_delay_seconds)
        else:
            due = now + timedelta(seconds=target.initial_delay_seconds)
        while due < now:
            due += timedelta(seconds=target.interval_seconds)
        return due

    async def _run_loop(self, target: HousekeepingTargetSettings) -> None:
        due = self._resume_due(target)
        self._persist_next_due(target, due)
        while True:
            delay = max(0.0, (due - self.clock()).total_seconds())
            await self.sleep(delay)
            await self.run_scheduled_once(target.runner, scheduled_for=due)
            due = due + timedelta(seconds=target.interval_seconds)
            now = self.clock()
            while due <= now:
                due = due + timedelta(seconds=target.interval_seconds)
            self._persist_next_due(target, due)

    async def start(self) -> bool:
        if (
            not self.settings.enabled
            or self.current_instance != self.settings.host_instance
            or self._active
        ):
            return False
        self._active = True
        for target in self.settings.targets:
            self._tasks[target.runner] = asyncio.create_task(
                self._run_loop(target),
                name=f"kis-housekeeping-{target.runner.value}",
            )
        return True

    async def stop(self) -> None:
        tasks = tuple(self._tasks.values())
        self._tasks.clear()
        self._active = False
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


__all__ = [
    "HousekeepingApplyError",
    "HousekeepingRuntimeService",
    "RunnerExecutor",
    "execute_housekeeping_runner",
]
