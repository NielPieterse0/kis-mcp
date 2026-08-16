from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol, Sequence

from .models import ReservationAdmissionError


class WorkerExecutionState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERABLE = "recoverable"


_TERMINAL_STATES = frozenset(
    {WorkerExecutionState.COMPLETED, WorkerExecutionState.FAILED, WorkerExecutionState.CANCELLED}
)

_ALLOWED_TRANSITIONS = {
    WorkerExecutionState.PENDING: frozenset(
        {WorkerExecutionState.RUNNING, WorkerExecutionState.FAILED, WorkerExecutionState.CANCELLED}
    ),
    WorkerExecutionState.RUNNING: frozenset(
        {
            WorkerExecutionState.WAITING_INPUT,
            WorkerExecutionState.COMPLETED,
            WorkerExecutionState.FAILED,
            WorkerExecutionState.CANCELLED,
            WorkerExecutionState.RECOVERABLE,
        }
    ),
    WorkerExecutionState.WAITING_INPUT: frozenset(
        {
            WorkerExecutionState.RUNNING,
            WorkerExecutionState.FAILED,
            WorkerExecutionState.CANCELLED,
            WorkerExecutionState.RECOVERABLE,
        }
    ),
    WorkerExecutionState.RECOVERABLE: frozenset(
        {WorkerExecutionState.RUNNING, WorkerExecutionState.FAILED, WorkerExecutionState.CANCELLED}
    ),
}


@dataclass(frozen=True, slots=True)
class ExecutionIdentity:
    execution_id: str
    packet_id: str
    task_id: str
    assignment_generation: int
    reservation_id: str
    authority_revision: int
    lease_id: str
    fence_token: int
    worker_id: str
    runtime_binding: Mapping[str, str]
    attempt_id: str

    def __post_init__(self) -> None:
        for label in (
            "execution_id", "packet_id", "task_id", "reservation_id",
            "lease_id", "worker_id", "attempt_id",
        ):
            _require_non_empty(getattr(self, label), label)
        for label in ("assignment_generation", "authority_revision", "fence_token"):
            _require_positive_int(getattr(self, label), label)
        object.__setattr__(self, "runtime_binding", MappingProxyType(_runtime_binding_ref(self.runtime_binding)))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "packet_id": self.packet_id,
            "task_id": self.task_id,
            "assignment_generation": self.assignment_generation,
            "reservation_id": self.reservation_id,
            "authority_revision": self.authority_revision,
            "lease_id": self.lease_id,
            "fence_token": self.fence_token,
            "worker_id": self.worker_id,
            "runtime_binding": dict(self.runtime_binding),
            "attempt_id": self.attempt_id,
        }


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    event_id: str
    expected_sequence: int
    state: WorkerExecutionState
    observed_at: datetime
    progress_id: str | None = None
    result_id: str | None = None
    residual_state: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty(self.event_id, "event_id")
        if isinstance(self.expected_sequence, bool) or not isinstance(self.expected_sequence, int):
            raise ValueError("expected_sequence must be a non-negative integer")
        if self.expected_sequence < 0:
            raise ValueError("expected_sequence must be a non-negative integer")
        if not isinstance(self.state, WorkerExecutionState):
            raise ValueError("state must be a WorkerExecutionState")
        _timestamp(self.observed_at)
        for label, value in (("progress_id", self.progress_id), ("result_id", self.result_id)):
            if value is not None:
                _require_non_empty(value, label)
        object.__setattr__(self, "residual_state", tuple(self.residual_state))
        if len(set(self.residual_state)) != len(self.residual_state):
            raise ValueError("residual_state must contain unique strings")
        if any(not isinstance(item, str) or not item.strip() for item in self.residual_state):
            raise ValueError("residual_state must contain non-empty strings")
        if self.state in {WorkerExecutionState.FAILED, WorkerExecutionState.CANCELLED, WorkerExecutionState.RECOVERABLE} and not self.residual_state:
            raise ValueError("residual_state is required for failed, cancelled, or recoverable state")
        if self.state is WorkerExecutionState.COMPLETED and self.result_id is None:
            raise ValueError("result_id is required for completed state")

    def digest(self) -> str:
        payload = {
            "event_id": self.event_id,
            "expected_sequence": self.expected_sequence,
            "state": self.state.value,
            "observed_at": _timestamp(self.observed_at),
            "progress_id": self.progress_id,
            "result_id": self.result_id,
            "residual_state": list(self.residual_state),
        }
        return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class WorkerExecution:
    identity: ExecutionIdentity
    state: WorkerExecutionState
    sequence: int
    observed_at: str
    progress_id: str | None = None
    result_id: str | None = None
    residual_state: tuple[str, ...] = ()
    accepted_events: tuple[tuple[str, str], ...] = ()
    last_event_id: str | None = None
    last_event_digest: str | None = None

    @classmethod
    def pending(cls, identity: ExecutionIdentity, *, observed_at: datetime) -> WorkerExecution:
        return cls(
            identity=identity,
            state=WorkerExecutionState.PENDING,
            sequence=0,
            observed_at=_timestamp(observed_at),
        )

    def to_json_dict(self) -> dict[str, Any]:
        last_event = None
        if self.last_event_id is not None:
            last_event = {"event_id": self.last_event_id, "digest": self.last_event_digest}
        return {
            "schema_version": 1,
            "contract": "coordinator-worker-execution-v1",
            "identity": self.identity.to_json_dict(),
            "state": self.state.value,
            "sequence": self.sequence,
            "observed_at": self.observed_at,
            "progress_id": self.progress_id,
            "result_id": self.result_id,
            "residual_state": list(self.residual_state),
            "accepted_events": [
                {"event_id": event_id, "digest": digest}
                for event_id, digest in self.accepted_events
            ],
            "last_event": last_event,
        }


class WorkerLifecycle:
    @staticmethod
    def transition(execution: WorkerExecution, event: ExecutionEvent) -> WorkerExecution:
        digest = event.digest()
        accepted = dict(execution.accepted_events)
        if event.event_id in accepted:
            if accepted[event.event_id] == digest:
                return execution
            raise ReservationAdmissionError(
                "WORKER_EVENT_CONFLICT",
                f"Event {event.event_id} was already observed with different content.",
            )
        if event.expected_sequence != execution.sequence:
            raise ReservationAdmissionError(
                "STALE_WORKER_EXECUTION",
                f"Expected sequence {event.expected_sequence}; current sequence is {execution.sequence}.",
            )
        allowed = _ALLOWED_TRANSITIONS.get(execution.state, frozenset())
        if event.state not in allowed:
            raise ReservationAdmissionError(
                "WORKER_TRANSITION_INVALID",
                f"Cannot transition worker execution from {execution.state.value} to {event.state.value}.",
            )
        return WorkerExecution(
            identity=execution.identity,
            state=event.state,
            sequence=execution.sequence + 1,
            observed_at=_timestamp(event.observed_at),
            progress_id=event.progress_id,
            result_id=event.result_id,
            residual_state=event.residual_state,
            accepted_events=execution.accepted_events + ((event.event_id, digest),),
            last_event_id=event.event_id,
            last_event_digest=digest,
        )

    @staticmethod
    def handoff(
        execution: WorkerExecution,
        *,
        handoff_id: str,
        exact_head: Mapping[str, str],
        changed_paths: Sequence[str],
        evidence: Sequence[Mapping[str, str]],
        observed_at: datetime,
    ) -> dict[str, Any]:
        _require_non_empty(handoff_id, "handoff_id")
        head = _git_identity(exact_head)
        status = _handoff_status(execution.state)
        identity = execution.identity
        return {
            "schema_version": 1,
            "contract": "coordinator-worker-handoff-v1",
            "handoff_id": handoff_id,
            "execution_id": identity.execution_id,
            "attempt_id": identity.attempt_id,
            "packet_id": identity.packet_id,
            "task_id": identity.task_id,
            "assignment_generation": identity.assignment_generation,
            "reservation_id": identity.reservation_id,
            "authority_revision": identity.authority_revision,
            "fence_token": identity.fence_token,
            "worker_id": identity.worker_id,
            "runtime_binding": dict(identity.runtime_binding),
            "result_id": execution.result_id,
            "exact_head": head,
            "changed_paths": _unique_strings(changed_paths, "changed_paths"),
            "evidence": _evidence(evidence),
            "residual_state": list(execution.residual_state),
            "status": status,
            "observed_at": _timestamp(observed_at),
        }


class McpWorkerClient(Protocol):
    async def __aenter__(self) -> McpWorkerClient: ...
    async def __aexit__(self, *args: object) -> None: ...
    async def list_tools(self) -> Sequence[Any]: ...
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> object: ...


ClientFactory = Callable[[Mapping[str, Any]], McpWorkerClient]
AdmitTool = Callable[[Mapping[str, Any], Any], bool]
AssertAuthority = Callable[[Mapping[str, Any]], Mapping[str, Any]]
IsMutating = Callable[[str, Mapping[str, Any], Any], bool]

_MAX_TOOL_RESULT_BYTES = 64 * 1024
_MAX_TOOL_RESULT_ITEMS = 4_096
_MAX_TOOL_ARGUMENT_BYTES = 64 * 1024


class _ResultTooLarge(ValueError):
    pass


class McpWorkerAdapter:
    def __init__(
        self,
        *,
        client_factory: ClientFactory,
        admit_tool: AdmitTool,
        assert_authority: AssertAuthority,
        is_mutating: IsMutating,
    ) -> None:
        self._client_factory = client_factory
        self._admit_tool = admit_tool
        self._assert_authority = assert_authority
        self._is_mutating = is_mutating
        self._client: McpWorkerClient | None = None
        self._allowed_tools: dict[str, Any] | None = None
        self._packet_id: str | None = None
        self._packet_digest: str | None = None
        self._runtime_binding: dict[str, str] | None = None

    async def connect(self, runtime_binding: Mapping[str, Any]) -> None:
        if self._client is not None:
            raise ReservationAdmissionError("WORKER_TRANSPORT_ALREADY_CONNECTED", "MCP worker transport is already connected.")
        verified_binding = _verify_runtime_binding(runtime_binding)
        binding_ref = _runtime_binding_ref(verified_binding)
        client = self._client_factory(verified_binding)
        self._client = await client.__aenter__()
        self._allowed_tools = None
        self._packet_id = None
        self._packet_digest = None
        self._runtime_binding = binding_ref

    async def discover(self, packet: Mapping[str, Any]) -> tuple[Any, ...]:
        client = self._require_client()
        packet_id = _packet_identity(packet)
        self._require_runtime_binding(packet)
        authority = _packet_authority(packet)
        observed = self._assert_authority(authority)
        if _authority_projection(observed) != authority:
            raise ReservationAdmissionError(
                "WORKER_AUTHORITY_CHANGED",
                "Current mutation authority no longer matches the work packet.",
            )
        tools = tuple(await client.list_tools())
        names: list[str] = []
        admitted: list[Any] = []
        for tool in tools:
            name = _tool_name(tool)
            if name in names:
                raise ReservationAdmissionError(
                    "WORKER_TOOL_DISCOVERY_INVALID",
                    f"MCP discovery returned duplicate tool {name}.",
                )
            names.append(name)
            if self._admit_tool(packet, tool):
                admitted.append(tool)
        self._allowed_tools = {_tool_name(tool): tool for tool in admitted}
        self._packet_id = packet_id
        self._packet_digest = _packet_digest(packet)
        return tuple(admitted)

    async def invoke(
        self,
        name: str,
        arguments: Mapping[str, Any],
        *,
        packet: Mapping[str, Any],
        progress_id: str,
        result_id: str,
    ) -> dict[str, Any]:
        client = self._require_client()
        _require_non_empty(name, "tool name")
        _require_non_empty(progress_id, "progress_id")
        _require_non_empty(result_id, "result_id")
        packet_id = _packet_identity(packet)
        self._require_runtime_binding(packet)
        if (
            self._allowed_tools is None
            or self._packet_id is None
            or self._packet_digest is None
        ):
            raise ReservationAdmissionError(
                "WORKER_TOOL_DISCOVERY_REQUIRED",
                "MCP tools must be discovered and filtered before invocation.",
            )
        if packet_id != self._packet_id or _packet_digest(packet) != self._packet_digest:
            raise ReservationAdmissionError(
                "WORKER_PACKET_MISMATCH",
                "MCP tool exposure was produced for a different work packet snapshot.",
            )
        if name not in self._allowed_tools:
            raise ReservationAdmissionError("WORKER_TOOL_NOT_ALLOWED", f"Tool {name} is not admitted by the work packet.")
        authority = _packet_authority(packet)
        tool = self._allowed_tools[name]
        dispatch_arguments, classification_arguments = _snapshot_tool_arguments(arguments)
        if self._is_mutating(name, classification_arguments, tool):
            observed = self._assert_authority(authority)
            if _authority_projection(observed) != authority:
                raise ReservationAdmissionError(
                    "WORKER_AUTHORITY_CHANGED",
                    "Current mutation authority no longer matches the work packet.",
                )
        result = _normalize_tool_result(await client.call_tool(name, dispatch_arguments))
        return {
            "packet_id": packet_id,
            "task_id": str(packet["task_id"]),
            "tool_name": name,
            "progress_id": progress_id,
            "result_id": result_id,
            "result": result,
        }

    async def reconnect(self, runtime_binding: Mapping[str, Any]) -> None:
        await self.close()
        await self.connect(runtime_binding)

    async def close(self) -> None:
        client = self._client
        self._client = None
        self._allowed_tools = None
        self._packet_id = None
        self._packet_digest = None
        self._runtime_binding = None
        if client is not None:
            await client.__aexit__(None, None, None)

    def _require_client(self) -> McpWorkerClient:
        if self._client is None:
            raise ReservationAdmissionError(
                "WORKER_TRANSPORT_NOT_CONNECTED", "MCP worker transport is not connected."
            )
        return self._client

    def _require_runtime_binding(self, packet: Mapping[str, Any]) -> None:
        packet_binding = packet.get("runtime_binding")
        if not isinstance(packet_binding, Mapping):
            raise ReservationAdmissionError(
                "WORKER_PACKET_INVALID", "Work packet runtime binding is required."
            )
        if self._runtime_binding != _runtime_binding_ref(packet_binding):
            raise ReservationAdmissionError(
                "WORKER_RUNTIME_BINDING_MISMATCH",
                "Connected MCP runtime does not match the work packet binding.",
            )


def _packet_identity(packet: Mapping[str, Any]) -> str:
    packet_id = packet.get("packet_id")
    task_id = packet.get("task_id")
    capabilities = packet.get("required_capabilities")
    _require_non_empty(packet_id, "packet_id")
    _require_non_empty(task_id, "task_id")
    if not isinstance(capabilities, Sequence) or isinstance(capabilities, (str, bytes, bytearray)):
        raise ReservationAdmissionError(
            "WORKER_PACKET_INVALID", "required_capabilities must be an array."
        )
    _unique_strings(capabilities, "required_capabilities")
    _packet_authority(packet)
    return str(packet_id)


def _packet_digest(packet: Mapping[str, Any]) -> str:
    try:
        payload = _canonical(dict(packet))
    except (TypeError, ValueError) as exc:
        raise ReservationAdmissionError(
            "WORKER_PACKET_INVALID", "Work packet must be canonically JSON-serializable."
        ) from exc
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _packet_authority(packet: Mapping[str, Any]) -> dict[str, Any]:
    authority = packet.get("authority")
    if not isinstance(authority, Mapping):
        raise ReservationAdmissionError("WORKER_PACKET_INVALID", "Work packet authority is required.")
    return _authority_projection(authority)


def _authority_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for field in ("reservation_id", "lease_id"):
        item = value.get(field)
        _require_non_empty(item, field)
        projected[field] = str(item)
    for field in ("authority_revision", "fence_token"):
        item = value.get(field)
        _require_positive_int(item, field)
        projected[field] = item
    return projected


def _verify_runtime_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "contract", "binding_id", "binding_fingerprint",
        "worker_id", "worker_revision", "runtime_id", "runtime_revision",
        "tool_id", "tool_revision", "protocol", "interface", "endpoint",
        "binding", "transport", "capabilities", "observed_at",
        "grants_mutation_authority",
    }
    if set(value) != required:
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID",
            "Runtime binding must match the strict coordinator runtime-binding contract.",
        )
    if value.get("schema_version") != 1 or value.get("contract") != "coordinator-runtime-binding-v1":
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID", "Runtime binding contract identity is invalid."
        )
    normalized: dict[str, Any] = {
        "schema_version": 1,
        "contract": "coordinator-runtime-binding-v1",
    }
    for field in (
        "binding_id", "worker_id", "worker_revision", "runtime_id", "tool_id",
        "tool_revision", "protocol", "interface", "endpoint", "binding", "observed_at",
    ):
        item = value.get(field)
        if not isinstance(item, str) or not item.strip():
            raise ReservationAdmissionError(
                "WORKER_RUNTIME_BINDING_INVALID", f"Runtime binding {field} is invalid."
            )
        normalized[field] = item
    runtime_revision = value.get("runtime_revision")
    if not isinstance(runtime_revision, str) or re.fullmatch(r"[0-9a-f]{40}", runtime_revision) is None:
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID", "runtime_revision must be an exact Git SHA."
        )
    normalized["runtime_revision"] = runtime_revision
    transport = value.get("transport")
    if transport not in {"mcp", "a2a", "local-process", "other"}:
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID", "Runtime binding transport is invalid."
        )
    normalized["transport"] = transport
    raw_capabilities = value.get("capabilities")
    if not isinstance(raw_capabilities, Sequence) or isinstance(
        raw_capabilities, (str, bytes, bytearray)
    ):
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID", "Runtime binding capabilities must be an array."
        )
    capabilities = _unique_strings(raw_capabilities, "runtime binding capabilities")
    if capabilities != sorted(capabilities):
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID", "Runtime binding capabilities must be canonical."
        )
    normalized["capabilities"] = capabilities
    observed_at = normalized["observed_at"]
    try:
        parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID", "Runtime binding observed_at is invalid."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID", "Runtime binding observed_at must be timezone-aware."
        )
    if value.get("grants_mutation_authority") is not False:
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_AUTHORITY_CONFLICT",
            "MCP runtime binding must be explicitly non-authorizing.",
        )
    normalized["grants_mutation_authority"] = False
    fingerprint = value.get("binding_fingerprint")
    if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID", "Runtime binding fingerprint is invalid."
        )
    expected = hashlib.sha256(_canonical(normalized).encode("utf-8")).hexdigest()
    if fingerprint != expected:
        raise ReservationAdmissionError(
            "WORKER_RUNTIME_BINDING_INVALID",
            "Runtime binding fingerprint does not match its concrete binding evidence.",
        )
    return {**normalized, "binding_fingerprint": fingerprint}


def _runtime_binding_ref(value: Mapping[str, Any]) -> dict[str, str]:
    binding_id = value.get("binding_id")
    fingerprint = value.get("binding_fingerprint")
    _require_non_empty(binding_id, "binding_id")
    if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise ValueError("binding_fingerprint must be a lowercase SHA-256 digest")
    return {"binding_id": str(binding_id), "binding_fingerprint": fingerprint}


def _git_identity(value: Mapping[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in ("commit_sha", "tree_sha"):
        item = value.get(field)
        if not isinstance(item, str) or re.fullmatch(r"[0-9a-f]{40}", item) is None:
            raise ValueError(f"{field} must be an exact lowercase Git SHA")
        result[field] = item
    return result


def _unique_strings(values: Sequence[Any], label: str) -> list[str]:
    normalized = list(values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} must contain unique strings")
    if any(not isinstance(item, str) or not item.strip() for item in normalized):
        raise ValueError(f"{label} must contain non-empty strings")
    return normalized


def _evidence(values: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for value in values:
        item = dict(value)
        for field in ("kind", "reference"):
            _require_non_empty(item.get(field), field)
        digest = item.get("digest")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("evidence digest must be a lowercase SHA-256 digest")
        result.append({"kind": item["kind"], "reference": item["reference"], "digest": digest})
    return result


def _snapshot_tool_arguments(
    arguments: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        canonical = _canonical(dict(arguments))
    except (TypeError, ValueError, RecursionError) as exc:
        raise ReservationAdmissionError(
            "WORKER_ARGUMENTS_INVALID", "MCP tool arguments must be JSON-compatible."
        ) from exc
    if len(canonical.encode("utf-8")) > _MAX_TOOL_ARGUMENT_BYTES:
        raise ReservationAdmissionError(
            "WORKER_ARGUMENTS_TOO_LARGE",
            f"MCP tool arguments exceed {_MAX_TOOL_ARGUMENT_BYTES} bytes.",
        )
    dispatch = json.loads(canonical)
    classify = json.loads(canonical)
    if not isinstance(dispatch, dict) or not isinstance(classify, dict):
        raise ReservationAdmissionError(
            "WORKER_ARGUMENTS_INVALID", "MCP tool arguments must be an object."
        )
    return dispatch, classify


def _normalize_tool_result(value: object) -> Any:
    candidate = value
    model_dump = getattr(candidate, "model_dump", None)
    if callable(model_dump):
        try:
            candidate = model_dump(mode="json")
        except (TypeError, ValueError) as exc:
            raise ReservationAdmissionError(
                "WORKER_RESULT_INVALID", "MCP result model could not be normalized."
            ) from exc
    budget = [0, 0]
    try:
        normalized = _json_safe(candidate, budget=budget)
        encoded = _canonical(normalized).encode("utf-8")
    except _ResultTooLarge as exc:
        raise ReservationAdmissionError(
            "WORKER_RESULT_TOO_LARGE",
            f"Normalized MCP result exceeds the bounded result budget: {exc}",
        ) from exc
    except (TypeError, ValueError, RecursionError) as exc:
        raise ReservationAdmissionError(
            "WORKER_RESULT_INVALID", "MCP result is not a bounded JSON-compatible value."
        ) from exc
    if len(encoded) > _MAX_TOOL_RESULT_BYTES:
        raise ReservationAdmissionError(
            "WORKER_RESULT_TOO_LARGE",
            f"Normalized MCP result exceeds {_MAX_TOOL_RESULT_BYTES} bytes.",
        )
    return normalized


def _json_safe(value: object, *, depth: int = 0, budget: list[int]) -> Any:
    if depth > 20:
        raise ValueError("result nesting is too deep")
    budget[0] += 1
    if budget[0] > _MAX_TOOL_RESULT_ITEMS:
        raise _ResultTooLarge(f"more than {_MAX_TOOL_RESULT_ITEMS} values")
    if value is None or isinstance(value, (bool, int, float)):
        budget[1] += 32
        if budget[1] > _MAX_TOOL_RESULT_BYTES:
            raise _ResultTooLarge(f"more than {_MAX_TOOL_RESULT_BYTES} estimated bytes")
        return value
    if isinstance(value, str):
        budget[1] += len(value.encode("utf-8"))
        if budget[1] > _MAX_TOOL_RESULT_BYTES:
            raise _ResultTooLarge(f"more than {_MAX_TOOL_RESULT_BYTES} estimated bytes")
        return value
    if type(value) is dict:
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("result object keys must be strings")
            budget[1] += len(key.encode("utf-8"))
            if budget[1] > _MAX_TOOL_RESULT_BYTES:
                raise _ResultTooLarge(f"more than {_MAX_TOOL_RESULT_BYTES} estimated bytes")
            result[key] = _json_safe(item, depth=depth + 1, budget=budget)
        return result
    if type(value) in {list, tuple}:
        return [_json_safe(item, depth=depth + 1, budget=budget) for item in value]
    raise TypeError(f"unsupported MCP result type: {type(value).__name__}")


def _tool_name(tool: Any) -> str:
    name = tool.get("name") if isinstance(tool, Mapping) else getattr(tool, "name", None)
    _require_non_empty(name, "tool name")
    return str(name)


def _handoff_status(state: WorkerExecutionState) -> str:
    if state is WorkerExecutionState.COMPLETED:
        return "worker_done"
    if state in {WorkerExecutionState.FAILED, WorkerExecutionState.CANCELLED}:
        return "worker_failed"
    return "worker_incomplete"


def _require_non_empty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _require_positive_int(value: Any, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a positive integer")


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("worker timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


__all__ = [
    "AdmitTool",
    "AssertAuthority",
    "ClientFactory",
    "ExecutionEvent",
    "ExecutionIdentity",
    "IsMutating",
    "McpWorkerAdapter",
    "McpWorkerClient",
    "WorkerExecution",
    "WorkerExecutionState",
    "WorkerLifecycle",
]
