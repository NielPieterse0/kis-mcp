from __future__ import annotations

import asyncio
import hashlib
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
    def __init__(self, *, result: object | None = None) -> None:
        self.entered = 0
        self.exited = 0
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.result = result

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
        if self.result is not None:
            return self.result
        return {"ok": True, "name": name}


def _packet() -> dict[str, object]:
    binding = _binding()
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
        "runtime_binding": {
            "binding_id": binding["binding_id"],
            "binding_fingerprint": binding["binding_fingerprint"],
        },
    }


def _binding(**overrides: object) -> dict[str, object]:
    binding: dict[str, object] = {
        "schema_version": 1,
        "contract": "coordinator-runtime-binding-v1",
        "binding_id": "kis-dev",
        "worker_id": "implementer",
        "worker_revision": "develop-code@10ab0e84",
        "runtime_id": "kis-dev",
        "runtime_revision": SHA,
        "tool_id": "codex-cli",
        "tool_revision": "0.147.0",
        "protocol": "mcp",
        "interface": "reviewable-worker-v1",
        "endpoint": "127.0.0.1:8011/mcp",
        "binding": "development",
        "transport": "mcp",
        "capabilities": ["filesystem.read", "filesystem.write"],
        "observed_at": "2026-08-16T02:55:00Z",
        "grants_mutation_authority": False,
    }
    binding.update(overrides)
    fingerprint_input = dict(binding)
    fingerprint_input.pop("binding_fingerprint", None)
    canonical = json.dumps(
        fingerprint_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    binding["binding_fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return binding


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
        is_mutating=lambda name, _arguments, _tool: name == "write_file",
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
        is_mutating=lambda _name, _arguments, _tool: False,
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
    execution_payload = completed.to_json_dict()
    assert execution_payload["accepted_events"] == {
        "start-contract": completed.accepted_events[0][1],
        "complete-contract": completed.accepted_events[1][1],
    }
    invalid_ledger = {**execution_payload, "accepted_events": []}
    assert list(
        Draft202012Validator(_schema("worker-execution")).iter_errors(invalid_ledger)
    )
    legacy_execution = {
        **completed.to_json_dict(),
        "schema_version": 1,
        "contract": "coordinator-worker-execution-v1",
    }
    assert list(
        Draft202012Validator(_schema("worker-execution")).iter_errors(legacy_execution)
    )

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
        is_mutating=lambda _name, _arguments, _tool: False,
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


def test_worker_lifecycle_replays_any_accepted_event_idempotently() -> None:
    pending = WorkerExecution.pending(_identity(), observed_at=NOW)
    start = _event("history-start", WorkerExecutionState.RUNNING)
    running = WorkerLifecycle.transition(pending, start)
    waiting = WorkerLifecycle.transition(
        running,
        _event(
            "history-wait",
            WorkerExecutionState.WAITING_INPUT,
            expected_sequence=1,
            progress_id="progress-wait",
        ),
    )

    assert WorkerLifecycle.transition(waiting, start) == waiting

    conflicting = _event(
        "history-start",
        WorkerExecutionState.RUNNING,
        progress_id="different-progress",
    )
    with pytest.raises(ReservationAdmissionError, match="WORKER_EVENT_CONFLICT"):
        WorkerLifecycle.transition(waiting, conflicting)


def test_mcp_adapter_rejects_tampered_runtime_binding_fingerprint() -> None:
    binding = _binding()
    binding["endpoint"] = "127.0.0.1:9999/mcp"
    adapter = McpWorkerAdapter(
        client_factory=lambda _binding: FakeClient(),
        admit_tool=lambda _packet, _tool: True,
        assert_authority=lambda authority: authority,
        is_mutating=lambda _name, _arguments, _tool: False,
    )

    async def scenario() -> None:
        with pytest.raises(ReservationAdmissionError, match="WORKER_RUNTIME_BINDING_INVALID"):
            await adapter.connect(binding)

    asyncio.run(scenario())


def test_mcp_adapter_binds_exposure_to_exact_packet_snapshot() -> None:
    adapter = McpWorkerAdapter(
        client_factory=lambda _binding: FakeClient(),
        admit_tool=lambda _packet, tool: tool["name"] == "read_file",  # type: ignore[index]
        assert_authority=lambda authority: authority,
        is_mutating=lambda _name, _arguments, _tool: False,
    )
    packet = _packet()
    changed_packet = _packet()
    changed_packet["task_id"] = "different-task"

    async def scenario() -> None:
        await adapter.connect(_binding())
        await adapter.discover(packet)
        with pytest.raises(ReservationAdmissionError, match="WORKER_PACKET_MISMATCH"):
            await adapter.invoke(
                "read_file",
                {},
                packet=changed_packet,
                progress_id="packet-progress",
                result_id="packet-result",
            )
        await adapter.close()

    asyncio.run(scenario())


def test_mcp_adapter_classifies_mutation_from_arguments_and_tool_metadata() -> None:
    checks = 0

    def assert_authority(authority: Mapping[str, Any]) -> Mapping[str, Any]:
        nonlocal checks
        checks += 1
        return authority

    def is_mutating(name: str, arguments: Mapping[str, Any], tool: object) -> bool:
        assert tool["name"] == name  # type: ignore[index]
        return name == "write_file" and not bool(arguments.get("dry_run"))

    adapter = McpWorkerAdapter(
        client_factory=lambda _binding: FakeClient(),
        admit_tool=lambda _packet, tool: tool["name"] == "write_file",  # type: ignore[index]
        assert_authority=assert_authority,
        is_mutating=is_mutating,
    )

    async def scenario() -> None:
        await adapter.connect(_binding())
        await adapter.discover(_packet())
        assert checks == 1
        await adapter.invoke(
            "write_file",
            {"dry_run": True},
            packet=_packet(),
            progress_id="dry-progress",
            result_id="dry-result",
        )
        assert checks == 1
        await adapter.invoke(
            "write_file",
            {"dry_run": False},
            packet=_packet(),
            progress_id="write-progress",
            result_id="write-result",
        )
        assert checks == 2
        await adapter.close()

    asyncio.run(scenario())


def test_mcp_adapter_rejects_unbounded_or_nonserializable_results() -> None:
    async def invoke_with(result: object) -> None:
        adapter = McpWorkerAdapter(
            client_factory=lambda _binding: FakeClient(result=result),
            admit_tool=lambda _packet, tool: tool["name"] == "read_file",  # type: ignore[index]
            assert_authority=lambda authority: authority,
            is_mutating=lambda _name, _arguments, _tool: False,
        )
        await adapter.connect(_binding())
        await adapter.discover(_packet())
        await adapter.invoke(
            "read_file",
            {},
            packet=_packet(),
            progress_id="result-progress",
            result_id="result-id",
        )

    with pytest.raises(ReservationAdmissionError, match="WORKER_RESULT_INVALID"):
        asyncio.run(invoke_with(object()))
    with pytest.raises(ReservationAdmissionError, match="WORKER_RESULT_TOO_LARGE"):
        asyncio.run(invoke_with("x" * 70_000))


def test_mutation_classifier_cannot_change_dispatched_argument_snapshot() -> None:
    client = FakeClient()
    checks = 0

    def assert_authority(authority: Mapping[str, Any]) -> Mapping[str, Any]:
        nonlocal checks
        checks += 1
        return authority

    def classifier(_name: str, arguments: Mapping[str, Any], _tool: object) -> bool:
        was_mutating = arguments.get("mode") == "mutate"
        if isinstance(arguments, dict):
            arguments["mode"] = "mutate"
        return was_mutating

    adapter = McpWorkerAdapter(
        client_factory=lambda _binding: client,
        admit_tool=lambda _packet, tool: tool["name"] == "write_file",  # type: ignore[index]
        assert_authority=assert_authority,
        is_mutating=classifier,
    )
    caller_arguments = {"mode": "read"}

    async def scenario() -> None:
        await adapter.connect(_binding())
        await adapter.discover(_packet())
        await adapter.invoke(
            "write_file",
            caller_arguments,
            packet=_packet(),
            progress_id="snapshot-progress",
            result_id="snapshot-result",
        )
        await adapter.close()

    asyncio.run(scenario())
    assert checks == 1
    assert caller_arguments == {"mode": "read"}
    assert client.calls == [("write_file", {"mode": "read"})]


def test_result_normalization_bounds_container_breadth_before_encoded_size() -> None:
    async def scenario() -> None:
        adapter = McpWorkerAdapter(
            client_factory=lambda _binding: FakeClient(result=[0] * 5_000),
            admit_tool=lambda _packet, tool: tool["name"] == "read_file",  # type: ignore[index]
            assert_authority=lambda authority: authority,
            is_mutating=lambda _name, _arguments, _tool: False,
        )
        await adapter.connect(_binding())
        await adapter.discover(_packet())
        await adapter.invoke(
            "read_file", {}, packet=_packet(), progress_id="breadth-p", result_id="breadth-r"
        )

    with pytest.raises(ReservationAdmissionError, match="WORKER_RESULT_TOO_LARGE"):
        asyncio.run(scenario())


def test_result_normalization_rejects_custom_sequence_without_iterating_it() -> None:
    class CustomSequence(Sequence[object]):
        def __init__(self) -> None:
            self.reads = 0

        def __len__(self) -> int:
            return 2

        def __getitem__(self, index: int) -> object:
            self.reads += 1
            if index >= 2:
                raise IndexError
            return "x"

    result = CustomSequence()

    async def scenario() -> None:
        adapter = McpWorkerAdapter(
            client_factory=lambda _binding: FakeClient(result=result),
            admit_tool=lambda _packet, tool: tool["name"] == "read_file",  # type: ignore[index]
            assert_authority=lambda authority: authority,
            is_mutating=lambda _name, _arguments, _tool: False,
        )
        await adapter.connect(_binding())
        await adapter.discover(_packet())
        await adapter.invoke(
            "read_file", {}, packet=_packet(), progress_id="custom-p", result_id="custom-r"
        )

    with pytest.raises(ReservationAdmissionError, match="WORKER_RESULT_INVALID"):
        asyncio.run(scenario())
    assert result.reads == 0


def test_result_normalization_rejects_oversized_text_before_encoding() -> None:
    class GuardedString(str):
        def encode(self, *args: object, **kwargs: object) -> bytes:
            raise AssertionError("oversized text must be rejected before encoding")

    async def invoke_with(result: object) -> None:
        adapter = McpWorkerAdapter(
            client_factory=lambda _binding: FakeClient(result=result),
            admit_tool=lambda _packet, tool: tool["name"] == "read_file",  # type: ignore[index]
            assert_authority=lambda authority: authority,
            is_mutating=lambda _name, _arguments, _tool: False,
        )
        await adapter.connect(_binding())
        await adapter.discover(_packet())
        await adapter.invoke(
            "read_file", {}, packet=_packet(), progress_id="text-p", result_id="text-r"
        )

    huge = GuardedString("é" * 70_000)
    with pytest.raises(ReservationAdmissionError, match="WORKER_RESULT_TOO_LARGE"):
        asyncio.run(invoke_with(huge))

    huge_key = GuardedString("k" * 70_000)
    with pytest.raises(ReservationAdmissionError, match="WORKER_RESULT_TOO_LARGE"):
        asyncio.run(invoke_with({huge_key: "value"}))


def test_mcp_adapter_closes_original_context_manager_when_enter_returns_client() -> None:
    class EnteredClient(FakeClient):
        pass

    class ClientManager(FakeClient):
        def __init__(self, entered: EnteredClient) -> None:
            super().__init__()
            self.entered_client = entered

        async def __aenter__(self) -> EnteredClient:
            self.entered += 1
            return self.entered_client

    entered = EnteredClient()
    manager = ClientManager(entered)
    adapter = McpWorkerAdapter(
        client_factory=lambda _binding: manager,
        admit_tool=lambda _packet, tool: tool["name"] == "read_file",  # type: ignore[index]
        assert_authority=lambda authority: authority,
        is_mutating=lambda _name, _arguments, _tool: False,
    )

    async def scenario() -> None:
        await adapter.connect(_binding())
        await adapter.discover(_packet())
        await adapter.close()

    asyncio.run(scenario())
    assert manager.entered == 1
    assert manager.exited == 1
    assert entered.exited == 0


def test_adapter_boundary_validation_uses_typed_errors() -> None:
    async def discover(packet: dict[str, object]) -> None:
        adapter = McpWorkerAdapter(
            client_factory=lambda _binding: FakeClient(),
            admit_tool=lambda _packet, _tool: True,
            assert_authority=lambda authority: authority,
            is_mutating=lambda _name, _arguments, _tool: False,
        )
        await adapter.connect(_binding())
        await adapter.discover(packet)

    bad_packet_id = _packet()
    bad_packet_id["packet_id"] = ""
    with pytest.raises(ReservationAdmissionError, match="WORKER_PACKET_INVALID"):
        asyncio.run(discover(bad_packet_id))

    bad_authority = _packet()
    bad_authority["authority"] = {
        "reservation_id": "res-150",
        "authority_revision": 0,
        "lease_id": "lease-150",
        "fence_token": 4,
    }
    with pytest.raises(ReservationAdmissionError, match="WORKER_PACKET_INVALID"):
        asyncio.run(discover(bad_authority))

    bad_binding = _packet()
    bad_binding["runtime_binding"] = {"binding_id": "kis-dev", "binding_fingerprint": "bad"}
    with pytest.raises(ReservationAdmissionError, match="WORKER_PACKET_INVALID"):
        asyncio.run(discover(bad_binding))

    async def discover_with_bad_authority_callback() -> None:
        adapter = McpWorkerAdapter(
            client_factory=lambda _binding: FakeClient(),
            admit_tool=lambda _packet, _tool: True,
            assert_authority=lambda _authority: None,  # type: ignore[arg-type,return-value]
            is_mutating=lambda _name, _arguments, _tool: False,
        )
        await adapter.connect(_binding())
        await adapter.discover(_packet())

    with pytest.raises(ReservationAdmissionError, match="WORKER_AUTHORITY_INVALID"):
        asyncio.run(discover_with_bad_authority_callback())


def test_invoke_boundary_validation_uses_typed_errors() -> None:
    adapter = McpWorkerAdapter(
        client_factory=lambda _binding: FakeClient(),
        admit_tool=lambda _packet, tool: tool["name"] == "read_file",  # type: ignore[index]
        assert_authority=lambda authority: authority,
        is_mutating=lambda _name, _arguments, _tool: False,
    )

    async def scenario() -> None:
        await adapter.connect(_binding())
        await adapter.discover(_packet())
        await adapter.invoke(
            "read_file", {}, packet=_packet(), progress_id="", result_id="typed-result"
        )

    with pytest.raises(ReservationAdmissionError, match="WORKER_INVOCATION_INVALID"):
        asyncio.run(scenario())


def test_worker_execution_rejects_schema_invalid_direct_construction() -> None:
    base = {
        "identity": _identity(),
        "state": WorkerExecutionState.RUNNING,
        "sequence": 1,
        "observed_at": "2026-08-16T02:55:00Z",
        "accepted_events": (("start", DIGEST),),
        "last_event_id": "start",
        "last_event_digest": DIGEST,
    }

    with pytest.raises(ValueError, match="sequence"):
        WorkerExecution(**{**base, "sequence": -1})
    with pytest.raises(ValueError, match="observed_at"):
        WorkerExecution(**{**base, "observed_at": "not-a-timestamp"})
    with pytest.raises(ValueError, match="result_id"):
        WorkerExecution(**{**base, "state": WorkerExecutionState.COMPLETED})
    with pytest.raises(ValueError, match="residual_state"):
        WorkerExecution(**{**base, "state": WorkerExecutionState.FAILED})
    with pytest.raises(ValueError, match="residual_state"):
        WorkerExecution(**{**base, "residual_state": "abc"})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="last_event"):
        WorkerExecution(**{**base, "last_event_digest": None})
