from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from kis_mcp.state import (
    StateNamespaceRequest,
    StateNamespaceResolver,
    StateOwnershipClass,
    derive_change_source_id,
)

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
    run_id: str
    packet_id: str
    project_id: str
    change_id: str
    task_id: str
    governed_worktree: str
    lifecycle_phase: str
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
            "execution_id", "run_id", "packet_id", "project_id", "change_id", "task_id",
            "governed_worktree", "lifecycle_phase", "reservation_id",
            "lease_id", "worker_id", "attempt_id",
        ):
            _require_non_empty(getattr(self, label), label)
        for label in ("assignment_generation", "authority_revision", "fence_token"):
            _require_positive_int(getattr(self, label), label)
        object.__setattr__(self, "runtime_binding", MappingProxyType(_runtime_binding_ref(self.runtime_binding)))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "run_id": self.run_id,
            "packet_id": self.packet_id,
            "project_id": self.project_id,
            "change_id": self.change_id,
            "task_id": self.task_id,
            "governed_worktree": self.governed_worktree,
            "lifecycle_phase": self.lifecycle_phase,
            "assignment_generation": self.assignment_generation,
            "reservation_id": self.reservation_id,
            "authority_revision": self.authority_revision,
            "lease_id": self.lease_id,
            "fence_token": self.fence_token,
            "worker_id": self.worker_id,
            "runtime_binding": dict(self.runtime_binding),
            "attempt_id": self.attempt_id,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> ExecutionIdentity:
        try:
            runtime_binding = value["runtime_binding"]
            if not isinstance(runtime_binding, Mapping):
                raise ValueError("runtime_binding must be an object")
            return cls(
                execution_id=value["execution_id"],
                run_id=value["run_id"],
                packet_id=value["packet_id"],
                project_id=value["project_id"],
                change_id=value["change_id"],
                task_id=value["task_id"],
                governed_worktree=value["governed_worktree"],
                lifecycle_phase=value["lifecycle_phase"],
                assignment_generation=value["assignment_generation"],
                reservation_id=value["reservation_id"],
                authority_revision=value["authority_revision"],
                lease_id=value["lease_id"],
                fence_token=value["fence_token"],
                worker_id=value["worker_id"],
                runtime_binding=runtime_binding,
                attempt_id=value["attempt_id"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("worker execution identity payload is invalid") from exc


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

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ExecutionIdentity):
            raise ValueError("identity must be an ExecutionIdentity")
        if not isinstance(self.state, WorkerExecutionState):
            raise ValueError("state must be a WorkerExecutionState")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 0:
            raise ValueError("sequence must be a non-negative integer")
        if not isinstance(self.observed_at, str) or not self.observed_at.strip():
            raise ValueError("observed_at must be a timezone-aware date-time")
        try:
            observed = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("observed_at must be a timezone-aware date-time") from exc
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("observed_at must be a timezone-aware date-time")
        for label, value in (("progress_id", self.progress_id), ("result_id", self.result_id)):
            if value is not None:
                _require_non_empty(value, label)
        if not isinstance(self.residual_state, Sequence) or isinstance(
            self.residual_state, (str, bytes, bytearray)
        ):
            raise ValueError("residual_state must be an array of strings")
        residual = tuple(self.residual_state)
        _unique_strings(residual, "residual_state")
        object.__setattr__(self, "residual_state", residual)
        accepted = tuple(tuple(item) for item in self.accepted_events)
        event_ids: set[str] = set()
        for item in accepted:
            if len(item) != 2:
                raise ValueError("accepted_events entries must contain event_id and digest")
            event_id, digest = item
            _require_non_empty(event_id, "accepted event_id")
            if event_id in event_ids:
                raise ValueError("accepted_events event_id values must be unique")
            event_ids.add(event_id)
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ValueError("accepted_events digest must be a lowercase SHA-256 digest")
        object.__setattr__(self, "accepted_events", accepted)
        if self.sequence != len(accepted):
            raise ValueError("sequence must equal the accepted_events count")
        if (self.last_event_id is None) != (self.last_event_digest is None):
            raise ValueError("last_event id and digest must both be present or both be absent")
        if accepted:
            if (self.last_event_id, self.last_event_digest) != accepted[-1]:
                raise ValueError("last_event must match the most recently accepted event")
        elif self.last_event_id is not None:
            raise ValueError("last_event requires accepted_events evidence")
        if self.state is WorkerExecutionState.COMPLETED and self.result_id is None:
            raise ValueError("result_id is required for completed state")
        if self.state in {
            WorkerExecutionState.FAILED,
            WorkerExecutionState.CANCELLED,
            WorkerExecutionState.RECOVERABLE,
        } and not residual:
            raise ValueError("residual_state is required for failed, cancelled, or recoverable state")

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
            "schema_version": 3,
            "contract": "coordinator-worker-execution-v3",
            "identity": self.identity.to_json_dict(),
            "state": self.state.value,
            "sequence": self.sequence,
            "observed_at": self.observed_at,
            "progress_id": self.progress_id,
            "result_id": self.result_id,
            "residual_state": list(self.residual_state),
            "accepted_events": {
                event_id: digest for event_id, digest in self.accepted_events
            },
            "last_event": last_event,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> WorkerExecution:
        try:
            if value.get("schema_version") != 3 or value.get("contract") != "coordinator-worker-execution-v3":
                raise ValueError("worker execution contract identity is invalid")
            identity_value = value["identity"]
            accepted_value = value["accepted_events"]
            if not isinstance(identity_value, Mapping) or not isinstance(accepted_value, Mapping):
                raise ValueError("worker execution durable payload is invalid")
            last_event = value.get("last_event")
            if last_event is not None and not isinstance(last_event, Mapping):
                raise ValueError("last_event must be an object or null")
            accepted = tuple((str(event_id), str(digest)) for event_id, digest in accepted_value.items())
            return cls(
                identity=ExecutionIdentity.from_json_dict(identity_value),
                state=WorkerExecutionState(value["state"]),
                sequence=value["sequence"],
                observed_at=value["observed_at"],
                progress_id=value.get("progress_id"),
                result_id=value.get("result_id"),
                residual_state=tuple(value.get("residual_state", ())),
                accepted_events=accepted,
                last_event_id=(str(last_event["event_id"]) if last_event is not None else None),
                last_event_digest=(str(last_event["digest"]) if last_event is not None else None),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("worker execution durable payload is invalid") from exc


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
            "schema_version": 3,
            "contract": "coordinator-worker-handoff-v3",
            "handoff_id": handoff_id,
            "execution_id": identity.execution_id,
            "run_id": identity.run_id,
            "attempt_id": identity.attempt_id,
            "packet_id": identity.packet_id,
            "project_id": identity.project_id,
            "change_id": identity.change_id,
            "task_id": identity.task_id,
            "governed_worktree": identity.governed_worktree,
            "lifecycle_phase": identity.lifecycle_phase,
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


class WorkerExecutionStore:
    STATE_KEY = "coordinator-worker-executions"

    def __init__(
        self,
        *,
        project_id: str,
        change_id: str,
        namespace_resolver: StateNamespaceResolver | None = None,
    ) -> None:
        resolver = namespace_resolver or StateNamespaceResolver()
        namespace = resolver.resolve(
            StateNamespaceRequest(
                ownership=StateOwnershipClass.DURABLE_EVIDENCE,
                state_key=self.STATE_KEY,
                identities={
                    "project_id": project_id,
                    "source_id": derive_change_source_id(change_id),
                },
            )
        )
        self.namespace = namespace
        self._root = Path(namespace.path)

    def load(self, execution_id: str) -> WorkerExecution | None:
        _require_non_empty(execution_id, "execution_id")
        path = self._execution_path(execution_id)
        if not path.is_file():
            return None
        payload = _read_json_object(path, "WORKER_EXECUTION_STORE_INVALID")
        if payload.get("schema_version") != 1 or payload.get("contract") != "coordinator-worker-execution-record-v1":
            raise ReservationAdmissionError(
                "WORKER_EXECUTION_STORE_INVALID",
                "Durable worker execution record contract identity is invalid.",
            )
        execution_value = payload.get("execution")
        accepted_order = payload.get("accepted_event_order")
        if not isinstance(execution_value, Mapping) or not isinstance(accepted_order, list):
            raise ReservationAdmissionError(
                "WORKER_EXECUTION_STORE_INVALID", "Durable worker execution is missing."
            )
        accepted_value = execution_value.get("accepted_events")
        if not isinstance(accepted_value, Mapping):
            raise ReservationAdmissionError(
                "WORKER_EXECUTION_STORE_INVALID", "Durable accepted-event ledger is invalid."
            )
        try:
            order = _unique_strings(accepted_order, "accepted_event_order")
        except ValueError as exc:
            raise ReservationAdmissionError("WORKER_EXECUTION_STORE_INVALID", str(exc)) from exc
        if set(order) != set(accepted_value) or len(order) != len(accepted_value):
            raise ReservationAdmissionError(
                "WORKER_EXECUTION_STORE_INVALID",
                "Durable accepted-event order does not match the execution ledger.",
            )
        ordered_execution = dict(execution_value)
        ordered_execution["accepted_events"] = {
            event_id: accepted_value[event_id] for event_id in order
        }
        try:
            execution = WorkerExecution.from_json_dict(ordered_execution)
        except ValueError as exc:
            raise ReservationAdmissionError("WORKER_EXECUTION_STORE_INVALID", str(exc)) from exc
        if execution.identity.execution_id != execution_id:
            raise ReservationAdmissionError(
                "WORKER_EXECUTION_STORE_INVALID",
                "Durable worker execution identity does not match its storage key.",
            )
        return execution

    def apply(
        self,
        identity: ExecutionIdentity,
        event: ExecutionEvent,
        *,
        initial_observed_at: datetime,
    ) -> WorkerExecution:
        with self._execution_lock(identity.execution_id):
            current = self.load(identity.execution_id)
            if current is None:
                current = WorkerExecution.pending(identity, observed_at=initial_observed_at)
            elif current.identity != identity:
                raise ReservationAdmissionError(
                    "WORKER_EXECUTION_IDENTITY_CONFLICT",
                    "Durable execution identity changed across restart/retry.",
                )
            updated = WorkerLifecycle.transition(current, event)
            return self._save_locked(updated)

    def save(self, execution: WorkerExecution) -> WorkerExecution:
        with self._execution_lock(execution.identity.execution_id):
            return self._save_locked(execution)

    def _save_locked(self, execution: WorkerExecution) -> WorkerExecution:
        path = self._execution_path(execution.identity.execution_id)
        existing = self.load(execution.identity.execution_id)
        if existing is not None:
            if existing == execution:
                return existing
            if existing.identity != execution.identity:
                raise ReservationAdmissionError(
                    "WORKER_EXECUTION_IDENTITY_CONFLICT",
                    "Durable execution identity cannot be replaced.",
                )
            if existing.sequence > execution.sequence:
                raise ReservationAdmissionError(
                    "STALE_WORKER_EXECUTION",
                    "A newer durable worker execution already exists.",
                )
            if existing.sequence == execution.sequence:
                raise ReservationAdmissionError(
                    "WORKER_EXECUTION_STORE_CONFLICT",
                    "Durable worker execution sequence has conflicting content.",
                )
            if execution.accepted_events[: existing.sequence] != existing.accepted_events:
                raise ReservationAdmissionError(
                    "WORKER_EXECUTION_STORE_CONFLICT",
                    "Durable worker execution history diverged from the stored journal.",
                )
        payload = {
            "schema_version": 1,
            "contract": "coordinator-worker-execution-record-v1",
            "accepted_event_order": [event_id for event_id, _digest in execution.accepted_events],
            "execution": execution.to_json_dict(),
        }
        _write_json_atomic(path, payload)
        return execution

    def begin_mutation(
        self,
        execution: WorkerExecution,
        *,
        tool_name: str,
        arguments: Mapping[str, Any],
        progress_id: str,
        result_id: str,
    ) -> dict[str, Any] | None:
        with self._execution_lock(execution.identity.execution_id):
            return self._begin_mutation_locked(
                execution,
                tool_name=tool_name,
                arguments=arguments,
                progress_id=progress_id,
                result_id=result_id,
            )

    def _begin_mutation_locked(
        self,
        execution: WorkerExecution,
        *,
        tool_name: str,
        arguments: Mapping[str, Any],
        progress_id: str,
        result_id: str,
    ) -> dict[str, Any] | None:
        fingerprint, record = self._mutation_identity(
            execution,
            tool_name=tool_name,
            arguments=arguments,
            progress_id=progress_id,
            result_id=result_id,
        )
        path = self._mutation_path(execution.identity.execution_id, result_id)
        if path.is_file():
            existing = _read_json_object(path, "WORKER_MUTATION_RECEIPT_INVALID")
            self._validate_mutation_record(
                existing,
                fingerprint,
                execution_id=execution.identity.execution_id,
                result_id=result_id,
            )
            if existing.get("status") == "completed":
                return existing
            raise ReservationAdmissionError(
                "WORKER_MUTATION_RECONCILIATION_REQUIRED",
                "A prior mutating dispatch has uncertain completion and will not be replayed automatically.",
            )
        if execution.state in _TERMINAL_STATES:
            raise ReservationAdmissionError(
                "WORKER_EXECUTION_TERMINAL",
                "Terminal worker execution cannot dispatch new mutation work.",
            )
        try:
            _write_json_once(path, {**record, "status": "in_flight"})
        except FileExistsError:
            existing = _read_json_object(path, "WORKER_MUTATION_RECEIPT_INVALID")
            self._validate_mutation_record(
                existing,
                fingerprint,
                execution_id=execution.identity.execution_id,
                result_id=result_id,
            )
            if existing.get("status") == "completed":
                return existing
            raise ReservationAdmissionError(
                "WORKER_MUTATION_RECONCILIATION_REQUIRED",
                "A concurrent or prior mutating dispatch already owns this durable result identity.",
            )
        return None

    def complete_mutation(
        self,
        execution: WorkerExecution,
        *,
        tool_name: str,
        arguments: Mapping[str, Any],
        progress_id: str,
        result_id: str,
        result: Any,
    ) -> dict[str, Any]:
        with self._execution_lock(execution.identity.execution_id):
            return self._complete_mutation_locked(
                execution,
                tool_name=tool_name,
                arguments=arguments,
                progress_id=progress_id,
                result_id=result_id,
                result=result,
            )

    def _complete_mutation_locked(
        self,
        execution: WorkerExecution,
        *,
        tool_name: str,
        arguments: Mapping[str, Any],
        progress_id: str,
        result_id: str,
        result: Any,
    ) -> dict[str, Any]:
        fingerprint, record = self._mutation_identity(
            execution,
            tool_name=tool_name,
            arguments=arguments,
            progress_id=progress_id,
            result_id=result_id,
        )
        path = self._mutation_path(execution.identity.execution_id, result_id)
        existing = _read_json_object(path, "WORKER_MUTATION_RECEIPT_INVALID")
        self._validate_mutation_record(
            existing,
            fingerprint,
            execution_id=execution.identity.execution_id,
            result_id=result_id,
        )
        if existing.get("status") == "completed":
            return existing
        completed = {**record, "status": "completed", "result": result}
        _write_json_atomic(path, completed)
        return completed

    def _mutation_identity(
        self,
        execution: WorkerExecution,
        *,
        tool_name: str,
        arguments: Mapping[str, Any],
        progress_id: str,
        result_id: str,
    ) -> tuple[str, dict[str, Any]]:
        _require_non_empty(tool_name, "tool_name")
        _require_non_empty(progress_id, "progress_id")
        _require_non_empty(result_id, "result_id")
        canonical_arguments = _canonical(dict(arguments))
        identity = execution.identity.to_json_dict()
        authority = {
            "reservation_id": execution.identity.reservation_id,
            "authority_revision": execution.identity.authority_revision,
            "lease_id": execution.identity.lease_id,
            "fence_token": execution.identity.fence_token,
        }
        stable = {
            "execution_id": execution.identity.execution_id,
            "attempt_id": execution.identity.attempt_id,
            "tool_name": tool_name,
            "arguments_sha256": hashlib.sha256(canonical_arguments.encode("utf-8")).hexdigest(),
            "progress_id": progress_id,
            "result_id": result_id,
            "identity": identity,
            "authority": authority,
        }
        fingerprint = hashlib.sha256(_canonical(stable).encode("utf-8")).hexdigest()
        return fingerprint, {
            "schema_version": 1,
            "contract": "coordinator-worker-mutation-receipt-v1",
            "fingerprint": fingerprint,
            **stable,
        }

    def _validate_mutation_record(
        self,
        value: Mapping[str, Any],
        fingerprint: str,
        *,
        execution_id: str,
        result_id: str,
    ) -> None:
        if (
            value.get("schema_version") != 1
            or value.get("contract") != "coordinator-worker-mutation-receipt-v1"
            or value.get("fingerprint") != fingerprint
            or value.get("execution_id") != execution_id
            or value.get("result_id") != result_id
            or value.get("status") not in {"in_flight", "completed"}
        ):
            raise ReservationAdmissionError(
                "WORKER_MUTATION_RECEIPT_CONFLICT",
                "Durable mutation result identity conflicts with existing evidence.",
            )

    @contextmanager
    def _execution_lock(self, execution_id: str) -> Iterable[None]:
        key = hashlib.sha256(execution_id.encode("utf-8")).hexdigest()
        lock_path = self._root / "locks" / f"{key}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as stream:
            stream.seek(0)
            _lock_file(stream)
            try:
                # Seed the byte only after serialization authority is held.
                stream.seek(0, os.SEEK_END)
                if stream.tell() == 0:
                    stream.write(b"0")
                    stream.flush()
                    os.fsync(stream.fileno())
                stream.seek(0)
                yield
            finally:
                _unlock_file(stream)

    def _execution_path(self, execution_id: str) -> Path:
        key = hashlib.sha256(execution_id.encode("utf-8")).hexdigest()
        return self._root / "executions" / f"{key}.json"

    def _mutation_path(self, execution_id: str, result_id: str) -> Path:
        key = hashlib.sha256(f"{execution_id}\0{result_id}".encode("utf-8")).hexdigest()
        return self._root / "mutations" / f"{key}.json"


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
        execution_store: WorkerExecutionStore | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._admit_tool = admit_tool
        self._assert_authority = assert_authority
        self._is_mutating = is_mutating
        self._execution_store = execution_store
        self._client_manager: McpWorkerClient | None = None
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
        client_manager = self._client_factory(verified_binding)
        entered_client = await client_manager.__aenter__()
        self._client_manager = client_manager
        self._client = entered_client
        self._allowed_tools = None
        self._packet_id = None
        self._packet_digest = None
        self._runtime_binding = binding_ref

    async def discover(self, packet: Mapping[str, Any]) -> tuple[Any, ...]:
        client = self._require_client()
        packet_id = _packet_identity(packet)
        self._require_runtime_binding(packet)
        authority = _packet_authority(packet)
        observed_authority = self._observed_authority(authority)
        if observed_authority != authority:
            raise ReservationAdmissionError(
                "WORKER_AUTHORITY_CHANGED",
                "Current mutation authority no longer matches the work packet.",
            )
        tools = tuple(await client.list_tools())
        names: list[str] = []
        admitted: list[Any] = []
        admitted_by_name: dict[str, Any] = {}
        for tool in tools:
            try:
                name = _tool_name(tool)
            except ValueError as exc:
                raise ReservationAdmissionError("WORKER_TOOL_DISCOVERY_INVALID", str(exc)) from exc
            if name in names:
                raise ReservationAdmissionError(
                    "WORKER_TOOL_DISCOVERY_INVALID",
                    f"MCP discovery returned duplicate tool {name}.",
                )
            names.append(name)
            if self._admit_tool(packet, tool):
                admitted.append(tool)
                admitted_by_name[name] = tool
        self._allowed_tools = admitted_by_name
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
        execution: WorkerExecution | None = None,
    ) -> dict[str, Any]:
        client = self._require_client()
        try:
            _require_non_empty(name, "tool name")
            _require_non_empty(progress_id, "progress_id")
            _require_non_empty(result_id, "result_id")
        except ValueError as exc:
            raise ReservationAdmissionError("WORKER_INVOCATION_INVALID", str(exc)) from exc
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
        if execution is not None:
            _validate_execution_packet(execution, packet, authority)
        tool = self._allowed_tools[name]
        dispatch_arguments, classification_arguments = _snapshot_tool_arguments(arguments)
        mutating = self._is_mutating(name, classification_arguments, tool)
        durable_execution = execution
        if mutating:
            observed_authority = self._observed_authority(authority)
            if observed_authority != authority:
                raise ReservationAdmissionError(
                    "WORKER_AUTHORITY_CHANGED",
                    "Current mutation authority no longer matches the work packet.",
                )
            if self._execution_store is not None:
                if execution is None:
                    raise ReservationAdmissionError(
                        "WORKER_EXECUTION_REQUIRED",
                        "Durable mutating invocation requires worker execution identity.",
                    )
                stored = self._execution_store.load(execution.identity.execution_id)
                if stored is None:
                    raise ReservationAdmissionError(
                        "WORKER_EXECUTION_NOT_DURABLE",
                        "Mutating invocation requires a persisted worker execution.",
                    )
                if stored != execution:
                    raise ReservationAdmissionError(
                        "STALE_WORKER_EXECUTION",
                        "Mutating invocation must use the current durable worker execution.",
                    )
                durable_execution = stored
                receipt = self._execution_store.begin_mutation(
                    stored,
                    tool_name=name,
                    arguments=dispatch_arguments,
                    progress_id=progress_id,
                    result_id=result_id,
                )
                if receipt is not None:
                    return _invocation_payload(
                        packet, name, progress_id, result_id, receipt.get("result"), stored
                    )
        result = _normalize_tool_result(await client.call_tool(name, dispatch_arguments))
        if mutating and self._execution_store is not None and durable_execution is not None:
            receipt = self._execution_store.complete_mutation(
                durable_execution,
                tool_name=name,
                arguments=dispatch_arguments,
                progress_id=progress_id,
                result_id=result_id,
                result=result,
            )
            result = receipt["result"]
        return _invocation_payload(packet, name, progress_id, result_id, result, execution)

    async def reconnect(self, runtime_binding: Mapping[str, Any]) -> None:
        await self.close()
        await self.connect(runtime_binding)

    async def close(self) -> None:
        client_manager = self._client_manager
        self._client_manager = None
        self._client = None
        self._allowed_tools = None
        self._packet_id = None
        self._packet_digest = None
        self._runtime_binding = None
        if client_manager is not None:
            await client_manager.__aexit__(None, None, None)

    def _require_client(self) -> McpWorkerClient:
        if self._client is None:
            raise ReservationAdmissionError(
                "WORKER_TRANSPORT_NOT_CONNECTED", "MCP worker transport is not connected."
            )
        return self._client

    def _observed_authority(self, authority: Mapping[str, Any]) -> dict[str, Any]:
        try:
            observed = self._assert_authority(authority)
            if not isinstance(observed, Mapping):
                raise ValueError("authority callback must return an authority object")
            return _authority_projection(observed)
        except ValueError as exc:
            raise ReservationAdmissionError("WORKER_AUTHORITY_INVALID", str(exc)) from exc

    def _require_runtime_binding(self, packet: Mapping[str, Any]) -> None:
        packet_binding = packet.get("runtime_binding")
        if not isinstance(packet_binding, Mapping):
            raise ReservationAdmissionError(
                "WORKER_PACKET_INVALID", "Work packet runtime binding is required."
            )
        try:
            packet_binding_ref = _runtime_binding_ref(packet_binding)
        except ValueError as exc:
            raise ReservationAdmissionError("WORKER_PACKET_INVALID", str(exc)) from exc
        if self._runtime_binding != packet_binding_ref:
            raise ReservationAdmissionError(
                "WORKER_RUNTIME_BINDING_MISMATCH",
                "Connected MCP runtime does not match the work packet binding.",
            )


def _validate_execution_packet(
    execution: WorkerExecution,
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> None:
    identity = execution.identity
    expected_authority = {
        "reservation_id": identity.reservation_id,
        "authority_revision": identity.authority_revision,
        "lease_id": identity.lease_id,
        "fence_token": identity.fence_token,
    }
    packet_binding = packet.get("runtime_binding")
    if not isinstance(packet_binding, Mapping):
        raise ReservationAdmissionError("WORKER_PACKET_INVALID", "Work packet runtime binding is required.")
    try:
        packet_binding_ref = _runtime_binding_ref(packet_binding)
    except ValueError as exc:
        raise ReservationAdmissionError("WORKER_PACKET_INVALID", str(exc)) from exc
    governed = packet.get("governed")
    if not isinstance(governed, Mapping):
        raise ReservationAdmissionError(
            "WORKER_PACKET_INVALID", "Work packet governed envelope is required."
        )
    if (
        identity.run_id != packet.get("run_id")
        or identity.packet_id != packet.get("packet_id")
        or identity.project_id != packet.get("project_id")
        or identity.change_id != packet.get("change_id")
        or identity.task_id != packet.get("task_id")
        or identity.governed_worktree != governed.get("worktree")
        or identity.lifecycle_phase != packet.get("lifecycle_phase")
        or expected_authority != dict(authority)
        or dict(identity.runtime_binding) != packet_binding_ref
    ):
        raise ReservationAdmissionError(
            "WORKER_EXECUTION_PACKET_MISMATCH",
            "Worker execution identity does not match the exact work packet authority/binding.",
        )
    assignment = packet.get("assignment")
    if isinstance(assignment, Mapping) and assignment.get("generation") != identity.assignment_generation:
        raise ReservationAdmissionError(
            "WORKER_EXECUTION_PACKET_MISMATCH",
            "Worker execution assignment generation does not match the work packet.",
        )


def _invocation_payload(
    packet: Mapping[str, Any],
    name: str,
    progress_id: str,
    result_id: str,
    result: Any,
    execution: WorkerExecution | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "packet_id": str(packet["packet_id"]),
        "task_id": str(packet["task_id"]),
        "tool_name": name,
        "progress_id": progress_id,
        "result_id": result_id,
        "result": result,
    }
    if execution is not None:
        identity = execution.identity
        payload.update(
            {
                "execution_id": identity.execution_id,
                "attempt_id": identity.attempt_id,
                "authority": {
                    "reservation_id": identity.reservation_id,
                    "authority_revision": identity.authority_revision,
                    "lease_id": identity.lease_id,
                    "fence_token": identity.fence_token,
                },
                "runtime_binding": dict(identity.runtime_binding),
            }
        )
    return payload


def _lock_file(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)


def _unlock_file(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _read_json_object(path: Path, error_code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReservationAdmissionError(error_code, f"Cannot read durable worker state: {exc}"[:1000]) from exc
    if not isinstance(value, dict):
        raise ReservationAdmissionError(error_code, "Durable worker state must be a JSON object.")
    return value


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f"{path.name}.tmp-{os.getpid()}-{hashlib.sha256(os.urandom(16)).hexdigest()[:12]}"
    )
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(_canonical(dict(value)) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _write_json_once(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(_canonical(dict(value)) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _packet_identity(packet: Mapping[str, Any]) -> str:
    packet_id = packet.get("packet_id")
    task_id = packet.get("task_id")
    capabilities = packet.get("required_capabilities")
    try:
        _require_non_empty(packet_id, "packet_id")
        _require_non_empty(task_id, "task_id")
        if not isinstance(capabilities, Sequence) or isinstance(
            capabilities, (str, bytes, bytearray)
        ):
            raise ValueError("required_capabilities must be an array")
        _unique_strings(capabilities, "required_capabilities")
    except ValueError as exc:
        raise ReservationAdmissionError("WORKER_PACKET_INVALID", str(exc)) from exc
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
    try:
        return _authority_projection(authority)
    except ValueError as exc:
        raise ReservationAdmissionError("WORKER_PACKET_INVALID", str(exc)) from exc


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
        _consume_text_budget(value, budget)
        return value
    if type(value) is dict:
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("result object keys must be strings")
            _consume_text_budget(key, budget)
            result[key] = _json_safe(item, depth=depth + 1, budget=budget)
        return result
    if type(value) in {list, tuple}:
        return [_json_safe(item, depth=depth + 1, budget=budget) for item in value]
    raise TypeError(f"unsupported MCP result type: {type(value).__name__}")


def _consume_text_budget(value: str, budget: list[int]) -> None:
    remaining = _MAX_TOOL_RESULT_BYTES - budget[1]
    if len(value) > remaining:
        raise _ResultTooLarge(f"more than {_MAX_TOOL_RESULT_BYTES} estimated bytes")
    encoded_length = len(value.encode("utf-8"))
    if encoded_length > remaining:
        raise _ResultTooLarge(f"more than {_MAX_TOOL_RESULT_BYTES} estimated bytes")
    budget[1] += encoded_length


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
