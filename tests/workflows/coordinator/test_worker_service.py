from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.workflows.coordinator import (
    ExecutionEvent,
    ExecutionIdentity,
    McpWorkerAdapter,
    ReservationAdmissionError,
    WorkerExecution,
    WorkerExecutionState,
    WorkerLifecycle,
)


ROOT = Path(__file__).parents[3]
SHA = "a" * 40
DIGEST = "d" * 64
NOW = datetime(2026, 8, 16, 4, 55, tzinfo=UTC)


def _schema(name: str) -> dict[str, object]:
    path = ROOT / "contracts" / "coordinator" / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _identity() -> ExecutionIdentity:
    return ExecutionIdentity(
        execution_id="exec-251-alpha",
        packet_id="packet-alpha",
        task_id="alpha",
        assignment_generation=1,
        reservation_id="res-150",
        authority_revision=4,
        lease_id="lease-150",
        fence_token=4,
        worker_id="implementer",
        runtime_binding={"binding_id": "kis-dev", "binding_fingerprint": DIGEST},
        attempt_id="attempt-1",
    )


def _event(event_id: str, state: WorkerExecutionState, **overrides: object) -> ExecutionEvent:
    values: dict[str, object] = {
        "event_id": event_id,
        "expected_sequence": 0,
        "state": state,
        "observed_at": NOW,
    }
    values.update(overrides)
    return ExecutionEvent(**values)  # type: ignore[arg-type]


def test_worker_lifecycle_is_deterministic_and_exact_duplicates_are_idempotent() -> None:
    pending = WorkerExecution.pending(_identity(), observed_at=NOW)
    event = _event("event-start", WorkerExecutionState.RUNNING, progress_id="progress-1")

    running = WorkerLifecycle.transition(pending, event)
    duplicate = WorkerLifecycle.transition(running, event)

    assert running == duplicate
    assert running.state is WorkerExecutionState.RUNNING
    assert running.sequence == 1
    assert running.progress_id == "progress-1"
    assert running.last_event_id == "event-start"

    conflicting = _event("event-start", WorkerExecutionState.FAILED, residual_state=("tool failed",))
    with pytest.raises(ReservationAdmissionError, match="WORKER_EVENT_CONFLICT"):
        WorkerLifecycle.transition(running, conflicting)


def test_worker_lifecycle_rejects_stale_and_illegal_transitions() -> None:
    pending = WorkerExecution.pending(_identity(), observed_at=NOW)
    running = WorkerLifecycle.transition(
        pending,
        _event("event-start", WorkerExecutionState.RUNNING),
    )
    stale = _event(
        "event-complete",
        WorkerExecutionState.COMPLETED,
        result_id="result-1",
        expected_sequence=0,
    )
    with pytest.raises(ReservationAdmissionError, match="STALE_WORKER_EXECUTION"):
        WorkerLifecycle.transition(running, stale)

    completed = WorkerLifecycle.transition(
        running,
        _event(
            "event-complete",
            WorkerExecutionState.COMPLETED,
            expected_sequence=1,
            result_id="result-1",
        ),
    )
    with pytest.raises(ReservationAdmissionError, match="WORKER_TRANSITION_INVALID"):
        WorkerLifecycle.transition(
            completed,
            _event("event-restart", WorkerExecutionState.RUNNING, expected_sequence=2),
        )


def test_failure_and_cancellation_require_deterministic_residual_state() -> None:
    pending = WorkerExecution.pending(_identity(), observed_at=NOW)
    running = WorkerLifecycle.transition(pending, _event("start", WorkerExecutionState.RUNNING))
    with pytest.raises(ValueError, match="residual_state"):
        _event("fail", WorkerExecutionState.FAILED, expected_sequence=1)

    failed = WorkerLifecycle.transition(
        running,
        _event(
            "fail",
            WorkerExecutionState.FAILED,
            expected_sequence=1,
            result_id="result-failed",
            residual_state=("uncommitted edits remain",),
        ),
    )
    assert failed.residual_state == ("uncommitted edits remain",)


class FakeClient:
    def __init__(self) -> None:
        self.entered = 0
        self.exited = 0
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self) -> FakeClient:
        self.entered += 1
        return self

    async def __aexit__(self, *args: object) -> None:
        self.exited += 1

    async def list_tools(self) -> Sequence[Mapping[str, object]]:
        return (
            {"name": "read_file", "capabilities": ["filesystem.read"]},
            {"name": "write_file", "capabilities": ["filesystem.write"]},
            {"name": "admin_shell", "capabilities": ["host.admin"]},
        )

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
        self.calls.append((name, arguments))
        return {"ok": True, "name": name}


def _packet() -> dict[str, object]:
    return {
        "packet_id": "packet-alpha",
        "task_id": "alpha",
        "required_capabilities": ["filesystem.read", "filesystem.write"],
        "authority": {
            "reservation_id": "res-150",
            "authority_revision": 4,
            "lease_id": "lease-150",
            "fence_token": 4,
        },
        "runtime_binding": {"binding_id": "kis-dev", "binding_fingerprint": DIGEST},
    }


def _binding() -> dict[str, object]:
    return {
        "binding_id": "kis-dev",
        "binding_fingerprint": DIGEST,
        "grants_mutation_authority": False,
    }


def test_mcp_adapter_filters_before_invocation_and_rechecks_mutation_authority() -> None:
    client = FakeClient()
    authority_checks: list[dict[str, object]] = []

    def admit_tool(packet: Mapping[str, Any], tool: object) -> bool:
        assert packet["required_capabilities"] == ["filesystem.read", "filesystem.write"]
        capabilities = set(tool["capabilities"])  # type: ignore[index]
        return capabilities.issubset(set(packet["required_capabilities"]))

    def assert_authority(authority: Mapping[str, Any]) -> Mapping[str, Any]:
        authority_checks.append(dict(authority))
        return authority

    adapter = McpWorkerAdapter(
        client_factory=lambda _binding: client,
        admit_tool=admit_tool,
        assert_authority=assert_authority,
        is_mutating=lambda name: name == "write_file",
    )

    async def scenario() -> None:
        await adapter.connect(_binding())
        exposed = await adapter.discover(_packet())
        assert [tool["name"] for tool in exposed] == ["read_file", "write_file"]
        with pytest.raises(ReservationAdmissionError, match="WORKER_TOOL_NOT_ALLOWED"):
            await adapter.invoke(
                "admin_shell", {}, packet=_packet(), progress_id="p-admin", result_id="r-admin"
            )
        read_result = await adapter.invoke(
            "read_file",
            {"path": "SPEC.md"},
            packet=_packet(),
            progress_id="p-read",
            result_id="r-read",
        )
        write_result = await adapter.invoke(
            "write_file",
            {"path": "x", "content": "y"},
            packet=_packet(),
            progress_id="p-write",
            result_id="r-write",
        )
        assert read_result["task_id"] == "alpha"
        assert read_result["progress_id"] == "p-read"
        assert write_result["result_id"] == "r-write"
        assert len(authority_checks) == 2
        await adapter.close()

    asyncio.run(scenario())
    assert client.calls == [
        ("read_file", {"path": "SPEC.md"}),
        ("write_file", {"path": "x", "content": "y"}),
    ]


def test_reconnect_is_transport_only_and_requires_rediscovery() -> None:
    clients = [FakeClient(), FakeClient()]
    checks = 0

    def assert_authority(authority: Mapping[str, Any]) -> Mapping[str, Any]:
        nonlocal checks
        checks += 1
        return authority

    adapter = McpWorkerAdapter(
        client_factory=lambda _binding: clients.pop(0),
        admit_tool=lambda _packet, tool: tool["name"] == "read_file",  # type: ignore[index]
        assert_authority=assert_authority,
        is_mutating=lambda _name: False,
    )

    async def scenario() -> None:
        await adapter.connect(_binding())
        await adapter.discover(_packet())
        assert checks == 1
        await adapter.reconnect(_binding())
        assert checks == 1
        with pytest.raises(ReservationAdmissionError, match="WORKER_TOOL_DISCOVERY_REQUIRED"):
            await adapter.invoke(
                "read_file", {}, packet=_packet(), progress_id="p", result_id="r"
            )
        await adapter.close()

    asyncio.run(scenario())


def test_worker_execution_and_handoff_validate_strict_contracts() -> None:
    pending = WorkerExecution.pending(_identity(), observed_at=NOW)
    running = WorkerLifecycle.transition(pending, _event("start-contract", WorkerExecutionState.RUNNING))
    completed = WorkerLifecycle.transition(
        running,
        _event(
            "complete-contract",
            WorkerExecutionState.COMPLETED,
            expected_sequence=1,
            progress_id="progress-contract",
            result_id="result-contract",
        ),
    )
    execution_errors = list(
        Draft202012Validator(_schema("worker-execution")).iter_errors(completed.to_json_dict())
    )
    assert execution_errors == []

    handoff = WorkerLifecycle.handoff(
        completed,
        handoff_id="handoff-contract",
        exact_head={"commit_sha": SHA, "tree_sha": SHA},
        changed_paths=("src/kis_mcp/workflows/coordinator/worker.py",),
        evidence=({"kind": "test", "reference": "pytest:worker", "digest": DIGEST},),
        observed_at=NOW,
    )
    handoff_errors = list(
        Draft202012Validator(_schema("worker-handoff")).iter_errors(handoff)
    )
    assert handoff_errors == []
    assert handoff["execution_id"] == "exec-251-alpha"
    assert handoff["result_id"] == "result-contract"


def test_mcp_adapter_rejects_packet_bound_to_different_runtime() -> None:
    adapter = McpWorkerAdapter(
        client_factory=lambda _binding: FakeClient(),
        admit_tool=lambda _packet, _tool: True,
        assert_authority=lambda authority: authority,
        is_mutating=lambda _name: False,
    )
    packet = _packet()
    packet["runtime_binding"] = {
        "binding_id": "other-runtime",
        "binding_fingerprint": "e" * 64,
    }

    async def scenario() -> None:
        await adapter.connect(_binding())
        with pytest.raises(ReservationAdmissionError, match="WORKER_RUNTIME_BINDING_MISMATCH"):
            await adapter.discover(packet)
        await adapter.close()

    asyncio.run(scenario())
