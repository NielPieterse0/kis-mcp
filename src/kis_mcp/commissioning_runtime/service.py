from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from kis_mcp.commissioning.settings import (
    PostMergeCommissioningSettings,
    PostMergeTargetSettings,
)

from .state import CommissioningStateError, CommissioningStateStore


class CommissioningOperationInvoker(Protocol):
    async def external(self, operation: str, arguments: dict[str, Any]) -> Any: ...
    async def read(self, operation: str, arguments: dict[str, Any]) -> Any: ...
    async def change(self, operation: str, arguments: dict[str, Any]) -> Any: ...


CandidateProcessor = Callable[
    [str, int, CommissioningOperationInvoker], Awaitable[dict[str, Any]]
]
Clock = Callable[[], datetime]
Sleep = Callable[[float], Awaitable[None]]


class CommissioningBudgetError(RuntimeError):
    def __init__(self, budget_type: str) -> None:
        self.budget_type = budget_type
        self.code = f"{budget_type}_budget_exceeded"
        super().__init__(f"{budget_type.replace('_', ' ')} budget exceeded")


class _MutationBudget:
    def __init__(self, maximum: int) -> None:
        self.maximum = maximum
        self.used = 0

    def consume(self) -> None:
        self.used += 1
        if self.used > self.maximum:
            raise CommissioningBudgetError("mutation")


_MUTATING_OPERATIONS = frozenset({"github_issue_write"})


def utc_now() -> datetime:
    return datetime.now(UTC)


class BudgetedInvoker:
    def __init__(
        self,
        inner: CommissioningOperationInvoker,
        *,
        max_external_reads: int,
        max_mutations: int,
        mutation_budget: _MutationBudget | None = None,
    ) -> None:
        self.inner = inner
        self.max_external_reads = max_external_reads
        self.max_mutations = max_mutations
        self.external_reads = 0
        self._mutation_budget = mutation_budget or _MutationBudget(max_mutations)

    @property
    def mutations(self) -> int:
        return self._mutation_budget.used

    def _consume_read(self) -> None:
        self.external_reads += 1
        if self.external_reads > self.max_external_reads:
            raise CommissioningBudgetError("external_read")

    async def external(self, operation: str, arguments: dict[str, Any]) -> Any:
        if operation in _MUTATING_OPERATIONS:
            self._mutation_budget.consume()
        else:
            self._consume_read()
        return await self.inner.external(operation, arguments)

    async def read(self, operation: str, arguments: dict[str, Any]) -> Any:
        self._consume_read()
        return await self.inner.read(operation, arguments)

    async def change(self, operation: str, arguments: dict[str, Any]) -> Any:
        self._mutation_budget.consume()
        return await self.inner.change(operation, arguments)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_provider_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{label} must be an ISO timestamp")
    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed.astimezone(UTC)


def _items(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Mapping):
        raise TypeError("pull request search result must be an object")
    if value.get("incomplete_results") is not False:
        raise RuntimeError("candidate search is incomplete")
    raw = value.get("items")
    if not isinstance(raw, list):
        raise TypeError("pull request search result items must be an array")
    if any(not isinstance(item, Mapping) for item in raw):
        raise TypeError("pull request search items must be objects")
    total_count = value.get("total_count")
    if type(total_count) is not int or total_count < 0:
        raise TypeError("pull request search total_count is invalid")
    if total_count != len(raw):
        raise RuntimeError("candidate search exceeds the bounded single-page result")
    return tuple(raw)


def _candidate_numbers(
    value: Any,
    limit: int,
    *,
    minimum_closed_at: datetime | None = None,
) -> tuple[int, ...]:
    items = _items(value)
    if len(items) > limit:
        raise RuntimeError("candidate result exceeds configured bound")
    numbers: list[int] = []
    selected: list[int] = []
    for item in items:
        number = item.get("number")
        if type(number) is not int or number <= 0:
            raise TypeError("candidate pull request number is invalid")
        numbers.append(number)
        if minimum_closed_at is not None:
            closed_at = _parse_provider_time(item.get("closed_at"), "candidate closed_at")
            if closed_at < minimum_closed_at:
                continue
        selected.append(number)
    if len(set(numbers)) != len(numbers):
        raise RuntimeError("candidate search contains duplicate pull requests")
    return tuple(sorted(selected, reverse=True))


def _repository_parts(repository: str) -> tuple[str, str]:
    owner, separator, repo = repository.partition("/")
    if separator != "/" or not owner or not repo:
        raise ValueError("repository must be owner/name")
    return owner, repo


class CommissioningRuntimeService:
    def __init__(
        self,
        settings: PostMergeCommissioningSettings,
        store: CommissioningStateStore,
        *,
        invoker: CommissioningOperationInvoker,
        processor: CandidateProcessor,
        clock: Clock = utc_now,
        sleep: Sleep = asyncio.sleep,
        current_instance: str = "kis-op",
    ) -> None:
        self.settings = settings
        self.store = store
        self.invoker = invoker
        self.processor = processor
        self.clock = clock
        self.sleep = sleep
        self.current_instance = current_instance
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def _target(self, repository: str) -> PostMergeTargetSettings:
        for target in self.settings.targets:
            if target.repository.casefold() == repository.casefold():
                return target
        raise KeyError(repository)
    def _receipt_payload(
        self,
        *,
        repository: str,
        occurred_at: datetime,
        complete: bool,
        initialized: bool,
        candidate_count: int,
        outcomes: list[dict[str, Any]],
        error_type: str | None = None,
        recovered_corrupt_checkpoint: bool = False,
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "run",
            "repository": repository,
            "occurred_at": _iso(occurred_at),
            "complete": complete,
            "initialized": initialized,
            "candidate_count": candidate_count,
            "outcomes": outcomes,
            "error_type": error_type,
            "recovered_corrupt_checkpoint": recovered_corrupt_checkpoint,
        }

    def _result(self, payload: dict[str, Any], receipt_id: str) -> dict[str, Any]:
        result = dict(payload)
        result["receipt_id"] = receipt_id
        return result
    async def run_scheduled_once(
        self,
        repository: str,
        *,
        scheduled_for: datetime,
    ) -> dict[str, Any]:
        target = self._target(repository)
        now = self.clock()
        try:
            _checkpoint, created = self.store.initialize_checkpoint(repository, now)
        except CommissioningStateError as exc:
            if exc.code != "checkpoint_invalid":
                raise
            self.store.recover_checkpoint(repository, now)
            payload = self._receipt_payload(
                repository=repository,
                occurred_at=now,
                complete=False,
                initialized=False,
                candidate_count=0,
                outcomes=[],
                error_type=type(exc).__name__,
                recovered_corrupt_checkpoint=True,
            )
            ref = self.store.persist_receipt(payload, now)
            return self._result(payload, ref.receipt_id)
        if created:
            payload = self._receipt_payload(
                repository=repository,
                occurred_at=now,
                complete=True,
                initialized=True,
                candidate_count=0,
                outcomes=[],
            )
            ref = self.store.persist_receipt(payload, now)
            return self._result(payload, ref.receipt_id)
        state = self.store.load_checkpoint_state(repository)
        if state is None:
            raise RuntimeError("initialized checkpoint disappeared before scan")
        first_scan = state.checkpoint_at == state.initialized_at
        mutation_budget = _MutationBudget(self.settings.max_mutations)
        discovery_invoker = BudgetedInvoker(
            self.invoker,
            max_external_reads=self.settings.max_external_reads,
            max_mutations=self.settings.max_mutations,
            mutation_budget=mutation_budget,
        )
        owner, repo = _repository_parts(repository)
        since = state.checkpoint_at - timedelta(seconds=self.settings.overlap_seconds)
        query = (
            f"repo:{repository} is:merged base:{target.default_branch} "
            f"updated:>={_iso(since)}"
        )
        outcomes: list[dict[str, Any]] = []
        candidate_count = 0
        try:
            discovered = await discovery_invoker.external(
                "github_search_pull_requests",
                {
                    "owner": owner,
                    "repo": repo,
                    "query": query,
                    "order": "asc",
                    "sort": "updated",
                    "perPage": self.settings.max_candidates,
                    "fields": ["number", "state", "updated_at", "closed_at"],
                },
            )
            candidates = _candidate_numbers(
                discovered,
                self.settings.max_candidates,
                minimum_closed_at=state.initialized_at if first_scan else None,
            )
            candidate_count = len(candidates)
            candidate_error_types: set[str] = set()
            for pull_number in candidates:
                candidate_invoker = BudgetedInvoker(
                    self.invoker,
                    max_external_reads=self.settings.max_external_reads,
                    max_mutations=self.settings.max_mutations,
                    mutation_budget=mutation_budget,
                )
                try:
                    outcome = await self.processor(repository, pull_number, candidate_invoker)
                    if not isinstance(outcome, dict):
                        raise TypeError("candidate processor result must be an object")
                    outcomes.append(outcome)
                except CommissioningBudgetError as exc:
                    if exc.budget_type != "external_read":
                        raise
                    candidate_error_types.add(type(exc).__name__)
                    outcomes.append(
                        {
                            "pull_number": pull_number,
                            "classification": "unresolved_candidate",
                            "error_type": type(exc).__name__,
                            "error_code": exc.code,
                        }
                    )
                except (RuntimeError, TypeError, ValueError, KeyError) as exc:
                    candidate_error_types.add(type(exc).__name__)
                    failure = {
                        "pull_number": pull_number,
                        "classification": "unresolved_candidate",
                        "error_type": type(exc).__name__,
                    }
                    error_code = getattr(exc, "code", None)
                    if isinstance(error_code, str) and error_code:
                        failure["error_code"] = error_code
                    outcomes.append(failure)
            if candidate_error_types:
                error_type = (
                    next(iter(candidate_error_types))
                    if len(candidate_error_types) == 1
                    else "MultipleCandidateErrors"
                )
                payload = self._receipt_payload(
                    repository=repository,
                    occurred_at=now,
                    complete=False,
                    initialized=False,
                    candidate_count=candidate_count,
                    outcomes=outcomes,
                    error_type=error_type,
                )
                ref = self.store.persist_receipt(payload, now)
                return self._result(payload, ref.receipt_id)
        except (RuntimeError, TypeError, ValueError, KeyError) as exc:
            payload = self._receipt_payload(
                repository=repository,
                occurred_at=now,
                complete=False,
                initialized=False,
                candidate_count=candidate_count,
                outcomes=outcomes,
                error_type=type(exc).__name__,
            )
            ref = self.store.persist_receipt(payload, now)
            return self._result(payload, ref.receipt_id)
        self.store.advance_checkpoint(repository, now)
        payload = self._receipt_payload(
            repository=repository,
            occurred_at=now,
            complete=True,
            initialized=False,
            candidate_count=candidate_count,
            outcomes=outcomes,
        )
        ref = self.store.persist_receipt(payload, now)
        return self._result(payload, ref.receipt_id)

    def receipt(self, receipt_id: str) -> dict[str, Any]:
        return self.store.load_receipt(receipt_id)

    def status(self) -> dict[str, Any]:
        targets: list[dict[str, Any]] = []
        now = self.clock()
        for target in self.settings.targets:
            try:
                state = self.store.load_checkpoint_state(target.repository)
                if state is None:
                    checkpoint_state = "never"
                    initialized_at = None
                    checkpoint_at = None
                    age_seconds = None
                    freshness = "never"
                    first_scan_pending = False
                else:
                    checkpoint_state = "ready"
                    initialized_at = _iso(state.initialized_at)
                    checkpoint_at = _iso(state.checkpoint_at)
                    first_scan_pending = state.initialized_at == state.checkpoint_at
                    age_seconds = max(
                        0,
                        int((now - state.checkpoint_at).total_seconds()),
                    )
                    freshness = (
                        "stale"
                        if age_seconds > self.settings.freshness_stale_after_seconds
                        else "fresh"
                    )
            except CommissioningStateError:
                checkpoint_state = "corrupt"
                initialized_at = None
                checkpoint_at = None
                age_seconds = None
                freshness = "corrupt"
                first_scan_pending = False
            try:
                latest = self.store.latest_receipt(target.repository)
                if latest is None:
                    last_receipt_id = None
                    last_receipt_complete = None
                    last_receipt_error_type = None
                    last_receipt_at = None
                else:
                    last_receipt_id, receipt = latest
                    last_receipt_complete = receipt.get("complete")
                    last_receipt_error_type = receipt.get("error_type")
                    last_receipt_at = receipt.get("occurred_at")
            except CommissioningStateError:
                last_receipt_id = None
                last_receipt_complete = None
                last_receipt_error_type = "CommissioningStateError"
                last_receipt_at = None
            targets.append(
                {
                    "project_id": target.project_id,
                    "repository": target.repository,
                    "default_branch": target.default_branch,
                    "checkpoint_state": checkpoint_state,
                    "initialized_at": initialized_at,
                    "checkpoint_at": checkpoint_at,
                    "freshness": freshness,
                    "age_seconds": age_seconds,
                    "first_scan_pending": first_scan_pending,
                    "last_receipt_id": last_receipt_id,
                    "last_receipt_complete": last_receipt_complete,
                    "last_receipt_error_type": last_receipt_error_type,
                    "last_receipt_at": last_receipt_at,
                    "scheduler_active": target.repository.casefold() in self._tasks,
                }
            )
        return {
            "schema_version": 1,
            "enabled": self.settings.enabled,
            "host_instance": self.settings.host_instance,
            "current_instance": self.current_instance,
            "active": self.active,
            "targets": targets,
        }

    async def _run_loop(self, target: PostMergeTargetSettings) -> None:
        due = self.clock() + timedelta(seconds=self.settings.initial_delay_seconds)
        while True:
            delay = max(0.0, (due - self.clock()).total_seconds())
            await self.sleep(delay)
            await self.run_scheduled_once(target.repository, scheduled_for=due)
            due += timedelta(seconds=self.settings.poll_interval_seconds)
            now = self.clock()
            while due <= now:
                due += timedelta(seconds=self.settings.poll_interval_seconds)

    async def start(self) -> bool:
        if (
            not self.settings.enabled
            or self.current_instance != self.settings.host_instance
            or self._active
        ):
            return False
        activation_at = self.clock()
        for target in self.settings.targets:
            try:
                self.store.initialize_checkpoint(target.repository, activation_at)
            except CommissioningStateError as exc:
                if exc.code != "checkpoint_invalid":
                    raise
                self.store.recover_checkpoint(target.repository, activation_at)
        self._active = True
        for target in self.settings.targets:
            self._tasks[target.repository.casefold()] = asyncio.create_task(
                self._run_loop(target),
                name=f"kis-post-merge-commissioning-{target.project_id}",
            )
        return True
    async def stop(self) -> None:
        tasks = tuple(self._tasks.values())
        current_loop = asyncio.get_running_loop()
        local_tasks: list[asyncio.Task[None]] = []
        foreign_waiters: list[asyncio.Future[None]] = []

        async def cancel_foreign(task: asyncio.Task[None]) -> None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

        for task in tasks:
            task_loop = task.get_loop()
            if task.done() or task_loop.is_closed():
                continue
            if task_loop is current_loop:
                task.cancel()
                local_tasks.append(task)
            elif task_loop.is_running():
                submitted = asyncio.run_coroutine_threadsafe(cancel_foreign(task), task_loop)
                foreign_waiters.append(asyncio.wrap_future(submitted))
            else:
                self._active = True
                raise RuntimeError(
                    "Commissioning scheduler shutdown cannot complete while a foreign task loop is stopped"
                )

        try:
            if local_tasks:
                await asyncio.gather(*local_tasks, return_exceptions=True)
            if foreign_waiters:
                await asyncio.wait_for(
                    asyncio.gather(*foreign_waiters),
                    timeout=5.0,
                )
        except Exception as exc:
            self._active = True
            raise RuntimeError("Commissioning scheduler shutdown did not complete") from exc

        self._tasks.clear()
        self._active = False


__all__ = [
    "BudgetedInvoker",
    "CandidateProcessor",
    "CommissioningBudgetError",
    "CommissioningOperationInvoker",
    "CommissioningRuntimeService",
]
