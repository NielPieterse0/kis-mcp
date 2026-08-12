from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from threading import RLock
from typing import Any


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    call_id: str
    timestamp: str
    tool_name: str
    argument_keys: tuple[str, ...]
    decision: str
    outcome: str
    code: str | None = None


@dataclass(frozen=True, slots=True)
class BoundaryRequestRecord:
    request_id: str
    timestamp: str
    method: str
    outcome: str
    tool_name: str | None = None
    error_type: str | None = None


@dataclass(frozen=True, slots=True)
class ActiveProcessRecord:
    pid: int
    cwd: str
    shell: str
    started_at: str
    last_seen_at: str
    interaction_count: int = 0


@dataclass(frozen=True, slots=True)
class ActiveSearchRecord:
    search_id: str
    tool_name: str
    started_at: str
    last_seen_at: str


@dataclass(frozen=True, slots=True)
class RuntimeObservabilitySnapshot:
    recent_calls: tuple[ToolCallRecord, ...]
    recent_policy_decisions: tuple[ToolCallRecord, ...]
    recent_boundary_requests: tuple[BoundaryRequestRecord, ...]
    active_processes: tuple[ActiveProcessRecord, ...]
    active_searches: tuple[ActiveSearchRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RuntimeObservability:
    """Keep bounded, redacted, process-local runtime evidence."""

    def __init__(
        self,
        *,
        max_recent_calls: int = 50,
        max_policy_decisions: int = 50,
        max_boundary_requests: int = 50,
    ) -> None:
        if min(max_recent_calls, max_policy_decisions, max_boundary_requests) < 1:
            raise ValueError("observability limits must be positive")
        self._recent_calls: deque[ToolCallRecord] = deque(maxlen=max_recent_calls)
        self._policy_decisions: deque[ToolCallRecord] = deque(
            maxlen=max_policy_decisions
        )
        self._boundary_requests: deque[BoundaryRequestRecord] = deque(
            maxlen=max_boundary_requests
        )
        self._processes: dict[int, ActiveProcessRecord] = {}
        self._searches: dict[str, ActiveSearchRecord] = {}
        self._next_call_id = 1
        self._next_request_id = 1
        self._lock = RLock()

    def record_tool_call(
        self,
        *,
        tool_name: str,
        argument_keys: tuple[str, ...] | list[str],
        decision: str,
        outcome: str,
        code: str | None = None,
    ) -> None:
        with self._lock:
            call_id = f"call-{self._next_call_id:06d}"
            self._next_call_id += 1
            record = ToolCallRecord(
                call_id=call_id,
                timestamp=_timestamp(),
                tool_name=str(tool_name),
                argument_keys=tuple(sorted({str(key) for key in argument_keys})),
                decision=str(decision),
                outcome=str(outcome),
                code=str(code) if code is not None else None,
            )
            self._recent_calls.appendleft(record)
            if record.decision in {"block", "quarantine"}:
                self._policy_decisions.appendleft(record)

    def record_boundary_request(
        self,
        *,
        method: str,
        outcome: str,
        tool_name: str | None = None,
        error_type: str | None = None,
    ) -> str:
        with self._lock:
            request_id = f"request-{self._next_request_id:06d}"
            self._next_request_id += 1
            self._boundary_requests.appendleft(
                BoundaryRequestRecord(
                    request_id=request_id,
                    timestamp=_timestamp(),
                    method=str(method),
                    outcome=str(outcome),
                    tool_name=str(tool_name) if tool_name is not None else None,
                    error_type=str(error_type) if error_type is not None else None,
                )
            )
            return request_id
    def process_started(self, *, pid: int, cwd: str, shell: str) -> None:
        now = _timestamp()
        record = ActiveProcessRecord(
            pid=int(pid),
            cwd=str(cwd),
            shell=str(shell),
            started_at=now,
            last_seen_at=now,
        )
        with self._lock:
            self._processes[record.pid] = record

    def process_interacted(self, *, pid: int) -> None:
        with self._lock:
            record = self._processes.get(int(pid))
            if record is None:
                return
            self._processes[int(pid)] = replace(
                record,
                last_seen_at=_timestamp(),
                interaction_count=record.interaction_count + 1,
            )

    def process_stopped(self, *, pid: int) -> None:
        with self._lock:
            self._processes.pop(int(pid), None)

    def search_started(self, *, search_id: str, tool_name: str) -> None:
        normalized = str(search_id).strip()
        if not normalized:
            return
        now = _timestamp()
        record = ActiveSearchRecord(
            search_id=normalized,
            tool_name=str(tool_name),
            started_at=now,
            last_seen_at=now,
        )
        with self._lock:
            self._searches[normalized] = record

    def search_interacted(self, *, search_id: str) -> None:
        normalized = str(search_id).strip()
        with self._lock:
            record = self._searches.get(normalized)
            if record is None:
                return
            self._searches[normalized] = replace(
                record,
                last_seen_at=_timestamp(),
            )

    def search_stopped(self, *, search_id: str) -> None:
        with self._lock:
            self._searches.pop(str(search_id).strip(), None)

    def snapshot(self) -> RuntimeObservabilitySnapshot:
        with self._lock:
            return RuntimeObservabilitySnapshot(
                recent_calls=tuple(self._recent_calls),
                recent_policy_decisions=tuple(self._policy_decisions),
                recent_boundary_requests=tuple(self._boundary_requests),
                active_processes=tuple(
                    self._processes[pid] for pid in sorted(self._processes)
                ),
                active_searches=tuple(
                    self._searches[key] for key in sorted(self._searches)
                ),
            )


_RUNTIME_OBSERVABILITY = RuntimeObservability()


def get_runtime_observability() -> RuntimeObservability:
    return _RUNTIME_OBSERVABILITY


def reset_runtime_observability_for_tests() -> RuntimeObservability:
    global _RUNTIME_OBSERVABILITY
    _RUNTIME_OBSERVABILITY = RuntimeObservability()
    return _RUNTIME_OBSERVABILITY


__all__ = [
    "ActiveProcessRecord",
    "ActiveSearchRecord",
    "BoundaryRequestRecord",
    "BoundaryRequestRecord",
    "RuntimeObservability",
    "RuntimeObservabilitySnapshot",
    "ToolCallRecord",
    "get_runtime_observability",
    "reset_runtime_observability_for_tests",
]
