from __future__ import annotations

import asyncio
import threading
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.commissioning.evidence import MergeEvidenceError
from kis_mcp.commissioning.settings import load_post_merge_commissioning_settings
from kis_mcp.commissioning_runtime.service import (
    BudgetedInvoker,
    CommissioningBudgetError,
    CommissioningRuntimeService,
)
from kis_mcp.commissioning_runtime.state import CommissioningStateStore

REPOSITORY = "NielPieterse0/kis-mcp"


class FakeInvoker:
    def __init__(self, responses: dict[str, list[Any]] | None = None) -> None:
        self.responses = {key: list(value) for key, value in (responses or {}).items()}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def external(self, operation: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((operation, dict(arguments)))
        queue = self.responses.get(operation)
        if not queue:
            raise AssertionError(f"unexpected operation: {operation}")
        return queue.pop(0)


class RecordingProcessor:
    def __init__(
        self,
        *,
        fail_on: int | None = None,
        blocked_on: int | None = None,
        extra_reads: int = 0,
    ) -> None:
        self.fail_on = fail_on
        self.blocked_on = blocked_on
        self.extra_reads = extra_reads
        self.calls: list[int] = []

    async def __call__(self, repository: str, pull_number: int, invoker: Any) -> dict[str, Any]:
        assert repository == REPOSITORY
        self.calls.append(pull_number)
        for _ in range(self.extra_reads):
            await invoker.external(
                "github_issue_read",
                {
                    "method": "get",
                    "owner": "NielPieterse0",
                    "repo": "kis-mcp",
                    "issue_number": 1,
                },
            )
        if self.fail_on == pull_number:
            raise RuntimeError("provider detail must not persist")
        if self.blocked_on == pull_number:
            return {
                "pull_number": pull_number,
                "classification": "blocked_evidence",
                "error_code": "scope_invalid",
                "commissioning_keys": [],
                "issue_numbers": [],
            }
        return {
            "pull_number": pull_number,
            "classification": "not_required",
            "merge_sha": str(pull_number).zfill(40),
            "commissioning_keys": [],
            "issue_numbers": [],
        }


class RetryableEvidenceProcessor(RecordingProcessor):
    def __init__(self, *, fail_on: int | None = None) -> None:
        super().__init__()
        self.fail_on = fail_on

    async def __call__(
        self, repository: str, pull_number: int, invoker: Any
    ) -> dict[str, Any]:
        assert repository == REPOSITORY
        self.calls.append(pull_number)
        if self.fail_on is None or self.fail_on == pull_number:
            raise MergeEvidenceError(
                "provider_evidence_invalid", "provider detail must not persist"
            )
        return {
            "pull_number": pull_number,
            "classification": "not_required",
            "merge_sha": str(pull_number).zfill(40),
            "commissioning_keys": [],
            "issue_numbers": [],
        }


class VariableReadProcessor(RecordingProcessor):
    def __init__(self, reads_by_pull: dict[int, int]) -> None:
        super().__init__()
        self.reads_by_pull = reads_by_pull

    async def __call__(
        self, repository: str, pull_number: int, invoker: Any
    ) -> dict[str, Any]:
        assert repository == REPOSITORY
        self.calls.append(pull_number)
        for _ in range(self.reads_by_pull.get(pull_number, 0)):
            await invoker.external(
                "github_issue_read",
                {
                    "method": "get",
                    "owner": "NielPieterse0",
                    "repo": "kis-mcp",
                    "issue_number": 1,
                },
            )
        return {
            "pull_number": pull_number,
            "classification": "not_required",
            "merge_sha": str(pull_number).zfill(40),
            "commissioning_keys": [],
            "issue_numbers": [],
        }


class MutatingProcessor(RecordingProcessor):
    async def __call__(
        self, repository: str, pull_number: int, invoker: Any
    ) -> dict[str, Any]:
        assert repository == REPOSITORY
        self.calls.append(pull_number)
        await invoker.external(
            "github_issue_write",
            {
                "method": "create",
                "owner": "NielPieterse0",
                "repo": "kis-mcp",
                "title": f"candidate-{pull_number}",
                "body": "bounded test mutation",
            },
        )
        return {
            "pull_number": pull_number,
            "classification": "not_required",
            "merge_sha": str(pull_number).zfill(40),
            "commissioning_keys": [],
            "issue_numbers": [],
        }


class MixedFailureProcessor(RecordingProcessor):
    async def __call__(
        self, repository: str, pull_number: int, invoker: Any
    ) -> dict[str, Any]:
        assert repository == REPOSITORY
        self.calls.append(pull_number)
        if pull_number == 565:
            raise MergeEvidenceError("provider_evidence_invalid", "hidden")
        if pull_number == 570:
            raise ValueError("hidden")
        return {
            "pull_number": pull_number,
            "classification": "not_required",
            "merge_sha": str(pull_number).zfill(40),
            "commissioning_keys": [],
            "issue_numbers": [],
        }


def _search(
    *numbers: int,
    total_count: int | None = None,
    incomplete: bool = False,
    closed_at: str = "2026-08-21T15:01:00Z",
) -> dict[str, Any]:
    return {
        "incomplete_results": incomplete,
        "items": [{"number": number, "closed_at": closed_at} for number in numbers],
        "total_count": len(numbers) if total_count is None else total_count,
    }


def _service(
    tmp_path: Path,
    now: list[datetime],
    invoker: FakeInvoker,
    processor: RecordingProcessor,
    *,
    current_instance: str = "kis-op",
    max_external_reads: int | None = None,
    max_mutations: int | None = None,
) -> CommissioningRuntimeService:
    settings = load_post_merge_commissioning_settings()
    if max_external_reads is not None:
        settings = replace(settings, max_external_reads=max_external_reads)
    if max_mutations is not None:
        settings = replace(settings, max_mutations=max_mutations)
    return CommissioningRuntimeService(
        settings,
        CommissioningStateStore(tmp_path, retention=settings.receipt_retention),
        invoker=invoker,
        processor=processor,
        clock=lambda: now[0],
        current_instance=current_instance,
    )


def test_first_run_initializes_checkpoint_without_provider_reads(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    invoker = FakeInvoker()
    processor = RecordingProcessor()
    service = _service(tmp_path, now, invoker, processor)

    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is True
    assert result["initialized"] is True
    assert result["candidate_count"] == 0
    assert invoker.calls == []
    assert processor.calls == []
    assert service.store.load_checkpoint(REPOSITORY) == now[0]


def test_successful_run_uses_overlap_and_advances_checkpoint(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    invoker = FakeInvoker({"github_search_pull_requests": [_search(453, 452)]})
    processor = RecordingProcessor()
    service = _service(tmp_path, now, invoker, processor)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is True
    assert result["candidate_count"] == 2
    assert processor.calls == [453, 452]
    query = invoker.calls[0][1]["query"]
    assert "repo:NielPieterse0/kis-mcp" in query
    assert "is:merged" in query
    assert "base:main" in query
    assert "updated:>=2026-08-21T14:45:00Z" in query
    assert service.store.load_checkpoint(REPOSITORY) == now[0]


def test_blocked_evidence_candidate_is_accounted_and_replayable(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    invoker = FakeInvoker(
        {"github_search_pull_requests": [_search(452, 453), _search(452, 453)]}
    )
    processor = RecordingProcessor(blocked_on=452)
    service = _service(tmp_path, now, invoker, processor)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    now[0] = now[0] + timedelta(seconds=300)
    first = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    assert first["complete"] is True
    assert [item["classification"] for item in first["outcomes"]] == [
        "not_required",
        "blocked_evidence",
    ]
    assert service.store.load_checkpoint(REPOSITORY) == now[0]

    processor.blocked_on = None
    now[0] = now[0] + timedelta(seconds=300)
    second = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    assert second["complete"] is True
    assert [item["classification"] for item in second["outcomes"]] == [
        "not_required",
        "not_required",
    ]
    assert processor.calls == [453, 452, 453, 452]
    assert service.store.load_checkpoint(REPOSITORY) == now[0]


def test_failed_candidate_does_not_advance_checkpoint_and_is_retryable(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    invoker = FakeInvoker({"github_search_pull_requests": [_search(452, 453)]})
    processor = RecordingProcessor(fail_on=453)
    service = _service(tmp_path, now, invoker, processor)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    original = service.store.load_checkpoint(REPOSITORY)

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is False
    assert result["candidate_count"] == 2
    assert result["error_type"] == "RuntimeError"
    assert service.store.load_checkpoint(REPOSITORY) == original
    receipt = service.store.load_receipt(result["receipt_id"])
    assert "provider detail" not in str(receipt)
    assert receipt["outcomes"][0]["pull_number"] == 453


def test_retryable_merge_evidence_error_preserves_checkpoint(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    invoker = FakeInvoker({"github_search_pull_requests": [_search(452)]})
    processor = RetryableEvidenceProcessor()
    service = _service(tmp_path, now, invoker, processor)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    original = service.store.load_checkpoint(REPOSITORY)

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is False
    assert result["error_type"] == "MergeEvidenceError"
    assert result["outcomes"] == [
        {
            "pull_number": 452,
            "classification": "unresolved_candidate",
            "error_type": "MergeEvidenceError",
            "error_code": "provider_evidence_invalid",
        }
    ]
    assert service.store.load_checkpoint(REPOSITORY) == original
    receipt = service.store.load_receipt(result["receipt_id"])
    assert "provider detail" not in str(receipt)


def test_historical_merge_evidence_failure_does_not_wedge_later_merge(tmp_path: Path) -> None:
    now = [datetime(2026, 9, 1, 9, 0, tzinfo=UTC)]
    invoker = FakeInvoker(
        {
            "github_search_pull_requests": [
                _search(565, 570, 615, closed_at="2026-09-01T09:01:00Z")
            ]
        }
    )
    processor = RetryableEvidenceProcessor(fail_on=570)
    service = _service(tmp_path, now, invoker, processor)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    original = service.store.load_checkpoint(REPOSITORY)

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is False
    assert result["candidate_count"] == 3
    assert result["error_type"] == "MergeEvidenceError"
    assert processor.calls == [615, 570, 565]
    assert result["outcomes"][0]["pull_number"] == 615
    assert result["outcomes"][0]["classification"] == "not_required"
    assert result["outcomes"][1] == {
        "pull_number": 570,
        "classification": "unresolved_candidate",
        "error_type": "MergeEvidenceError",
        "error_code": "provider_evidence_invalid",
    }
    assert result["outcomes"][2]["pull_number"] == 565
    assert result["outcomes"][2]["classification"] == "not_required"
    assert service.store.load_checkpoint(REPOSITORY) == original


def test_mixed_candidate_failures_preserve_each_error_type(tmp_path: Path) -> None:
    now = [datetime(2026, 9, 1, 9, 0, tzinfo=UTC)]
    invoker = FakeInvoker(
        {
            "github_search_pull_requests": [
                _search(565, 570, 615, closed_at="2026-09-01T09:01:00Z")
            ]
        }
    )
    processor = MixedFailureProcessor()
    service = _service(tmp_path, now, invoker, processor)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    original = service.store.load_checkpoint(REPOSITORY)

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is False
    assert result["error_type"] == "MultipleCandidateErrors"
    assert result["outcomes"][0]["pull_number"] == 615
    assert [item["error_type"] for item in result["outcomes"][1:]] == [
        "ValueError",
        "MergeEvidenceError",
    ]
    assert service.store.load_checkpoint(REPOSITORY) == original


def test_corrupt_checkpoint_recovers_at_current_time_without_backfill(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    invoker = FakeInvoker()
    processor = RecordingProcessor()
    service = _service(tmp_path, now, invoker, processor)
    path = service.store.checkpoint_path(REPOSITORY)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("broken", encoding="utf-8")

    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is False
    assert result["recovered_corrupt_checkpoint"] is True
    assert service.store.load_checkpoint(REPOSITORY) == now[0]
    assert invoker.calls == []
    assert processor.calls == []


def test_external_read_budget_failure_preserves_checkpoint(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    invoker = FakeInvoker(
        {
            "github_search_pull_requests": [_search(452)],
            "github_issue_read": [{"number": 1}],
        }
    )
    processor = RecordingProcessor(extra_reads=2)
    service = _service(
        tmp_path, now, invoker, processor, max_external_reads=1
    )
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    original = service.store.load_checkpoint(REPOSITORY)

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is False
    assert result["error_type"] == "CommissioningBudgetError"
    assert result["outcomes"] == [
        {
            "pull_number": 452,
            "classification": "unresolved_candidate",
            "error_type": "CommissioningBudgetError",
            "error_code": "external_read_budget_exceeded",
        }
    ]
    assert service.store.load_checkpoint(REPOSITORY) == original


def test_shared_mutation_budget_exhaustion_is_whole_scan_failure(tmp_path: Path) -> None:
    now = [datetime(2026, 9, 1, 9, 0, tzinfo=UTC)]
    invoker = FakeInvoker(
        {
            "github_search_pull_requests": [
                _search(452, 453, closed_at="2026-09-01T09:01:00Z")
            ],
            "github_issue_write": [{"number": 9001}],
        }
    )
    processor = MutatingProcessor()
    service = _service(tmp_path, now, invoker, processor, max_mutations=1)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    original = service.store.load_checkpoint(REPOSITORY)

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is False
    assert result["error_type"] == "CommissioningBudgetError"
    assert processor.calls == [453, 452]
    assert result["outcomes"][0]["pull_number"] == 453
    assert result["outcomes"][0]["classification"] == "not_required"
    assert service.store.load_checkpoint(REPOSITORY) == original


def test_candidate_read_budget_exhaustion_does_not_starve_later_candidate(tmp_path: Path) -> None:
    now = [datetime(2026, 9, 1, 9, 0, tzinfo=UTC)]
    invoker = FakeInvoker(
        {
            "github_search_pull_requests": [
                _search(452, 453, closed_at="2026-09-01T09:01:00Z")
            ],
            "github_issue_read": [{"number": 1}, {"number": 1}],
        }
    )
    processor = VariableReadProcessor({452: 2, 453: 1})
    service = _service(tmp_path, now, invoker, processor, max_external_reads=1)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    original = service.store.load_checkpoint(REPOSITORY)

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is False
    assert processor.calls == [453, 452]
    assert result["outcomes"][0]["pull_number"] == 453
    assert result["outcomes"][0]["classification"] == "not_required"
    assert result["outcomes"][1] == {
        "pull_number": 452,
        "classification": "unresolved_candidate",
        "error_type": "CommissioningBudgetError",
        "error_code": "external_read_budget_exceeded",
    }
    assert service.store.load_checkpoint(REPOSITORY) == original


def test_candidate_read_budgets_prevent_later_candidate_starvation(tmp_path: Path) -> None:
    now = [datetime(2026, 9, 1, 9, 0, tzinfo=UTC)]
    numbers = tuple(range(600, 626))
    invoker = FakeInvoker(
        {
            "github_search_pull_requests": [
                _search(*numbers, closed_at="2026-09-01T09:01:00Z")
            ],
            "github_issue_read": [{"number": 1}] * (len(numbers) * 8),
        }
    )
    processor = RecordingProcessor(extra_reads=8)
    service = _service(tmp_path, now, invoker, processor, max_external_reads=8)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is True
    assert result["candidate_count"] == 26
    assert processor.calls == list(reversed(numbers))
    assert len(invoker.calls) == 1 + (26 * 8)
    assert service.store.load_checkpoint(REPOSITORY) == now[0]


def test_scheduler_is_hosted_only_on_kis_op(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    dev = _service(
        tmp_path,
        now,
        FakeInvoker(),
        RecordingProcessor(),
        current_instance="kis-dev",
    )

    assert asyncio.run(dev.start()) is False
    assert dev.active is False

    op = _service(tmp_path, now, FakeInvoker(), RecordingProcessor())
    assert asyncio.run(op.start()) is True
    assert op.active is True
    asyncio.run(op.stop())
    assert op.active is False


def test_stop_waits_for_foreign_running_loop_task(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    service = _service(tmp_path, now, FakeInvoker(), RecordingProcessor())
    loop = asyncio.new_event_loop()
    ready = threading.Event()
    holder: dict[str, asyncio.Task[None]] = {}

    def run_loop() -> None:
        asyncio.set_event_loop(loop)

        async def sleeper() -> None:
            await asyncio.sleep(3600)

        holder["task"] = loop.create_task(sleeper())
        ready.set()
        loop.run_forever()
        loop.close()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    assert ready.wait(timeout=2.0)
    task = holder["task"]
    service._tasks[REPOSITORY.casefold()] = task
    service._active = True

    asyncio.run(service.stop())

    assert task.done()
    assert service.active is False
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2.0)
    assert not thread.is_alive()


def test_stop_rejects_pending_task_on_stopped_foreign_loop(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    service = _service(tmp_path, now, FakeInvoker(), RecordingProcessor())
    loop = asyncio.new_event_loop()

    async def sleeper() -> None:
        await asyncio.sleep(3600)

    task = loop.create_task(sleeper())
    service._tasks[REPOSITORY.casefold()] = task
    service._active = True

    with pytest.raises(RuntimeError, match="foreign task loop is stopped"):
        asyncio.run(service.stop())

    assert service.active is True
    assert service._tasks[REPOSITORY.casefold()] is task
    task.cancel()
    loop.run_until_complete(asyncio.gather(task, return_exceptions=True))
    loop.close()


def test_truncated_candidate_search_preserves_checkpoint(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    invoker = FakeInvoker(
        {"github_search_pull_requests": [_search(452, total_count=2)]}
    )
    processor = RecordingProcessor()
    service = _service(tmp_path, now, invoker, processor)
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))
    original = service.store.load_checkpoint(REPOSITORY)

    now[0] = now[0] + timedelta(seconds=300)
    result = asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    assert result["complete"] is False
    assert result["error_type"] == "RuntimeError"
    assert processor.calls == []
    assert service.store.load_checkpoint(REPOSITORY) == original


def test_start_freezes_non_backfill_boundary_before_initial_delay(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    search = {
        "incomplete_results": False,
        "items": [
            {"number": 451, "closed_at": "2026-08-21T14:59:59Z"},
            {"number": 452, "closed_at": "2026-08-21T15:00:01Z"},
        ],
        "total_count": 2,
    }
    invoker = FakeInvoker({"github_search_pull_requests": [search]})
    processor = RecordingProcessor()
    service = _service(tmp_path, now, invoker, processor)

    async def scenario() -> dict[str, Any]:
        assert await service.start() is True
        state = service.store.load_checkpoint_state(REPOSITORY)
        assert state is not None and state.initialized_at == now[0]
        now[0] = now[0] + timedelta(seconds=300)
        result = await service.run_scheduled_once(REPOSITORY, scheduled_for=now[0])
        await service.stop()
        return result

    result = asyncio.run(scenario())

    assert result["complete"] is True
    assert result["candidate_count"] == 1
    assert processor.calls == [452]


def test_status_reports_activation_boundary_and_freshness(tmp_path: Path) -> None:
    now = [datetime(2026, 8, 21, 15, 0, tzinfo=UTC)]
    service = _service(tmp_path, now, FakeInvoker(), RecordingProcessor())
    asyncio.run(service.run_scheduled_once(REPOSITORY, scheduled_for=now[0]))

    target = service.status()["targets"][0]
    assert target["initialized_at"] == "2026-08-21T15:00:00Z"
    assert target["checkpoint_at"] == "2026-08-21T15:00:00Z"
    assert target["freshness"] == "fresh"
    assert target["age_seconds"] == 0
    assert target["first_scan_pending"] is True
    assert target["last_receipt_id"].startswith("post-merge-commissioning:")
    assert target["last_receipt_complete"] is True
    assert target["last_receipt_error_type"] is None

    now[0] = now[0] + timedelta(
        seconds=service.settings.freshness_stale_after_seconds + 1
    )
    stale = service.status()["targets"][0]
    assert stale["freshness"] == "stale"
    assert stale["age_seconds"] == service.settings.freshness_stale_after_seconds + 1


class PlaneInvoker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def external(self, operation: str, _arguments: dict[str, Any]) -> Any:
        self.calls.append(("external", operation))
        return {"ok": True}

    async def read(self, operation: str, _arguments: dict[str, Any]) -> Any:
        self.calls.append(("read", operation))
        return {"ok": True}

    async def change(self, operation: str, _arguments: dict[str, Any]) -> Any:
        self.calls.append(("change", operation))
        return {"outcomes": [{"success": True}]}


def test_budget_wrapper_counts_read_and_change_control_planes() -> None:
    inner = PlaneInvoker()
    bounded = BudgetedInvoker(inner, max_external_reads=1, max_mutations=1)
    assert asyncio.run(bounded.read("project_management_board_data", {}))["ok"] is True
    assert asyncio.run(bounded.change("project_management_reconcile", {}))["outcomes"]

    with pytest.raises(CommissioningBudgetError, match="read budget"):
        asyncio.run(bounded.read("project_management_contract", {}))
    with pytest.raises(CommissioningBudgetError, match="mutation budget"):
        asyncio.run(bounded.change("project_management_reconcile", {}))