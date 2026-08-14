from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from threading import RLock
from typing import Any, Iterator


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


_CURRENT_REQUEST_ID: ContextVar[str | None] = ContextVar(
    "kis_mcp_current_request_id", default=None
)


def current_request_id() -> str | None:
    return _CURRENT_REQUEST_ID.get()


@contextmanager
def boundary_request_context(request_id: str) -> Iterator[None]:
    token = _CURRENT_REQUEST_ID.set(str(request_id))
    try:
        yield
    finally:
        _CURRENT_REQUEST_ID.reset(token)


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
class SkillActivityRecord:
    event_id: str
    timestamp: str
    event_name: str
    source: str
    skill_id: str | None
    snapshot_id: str | None
    content_sha256: str | None
    project_id: str | None
    activation_id: str | None
    request_id: str | None
    outcome: str
    duration_ms: int | None = None
    error_class: str | None = None
    total_tokens: int | None = None
    tool_calls: int | None = None
    retries: int | None = None
    verification_passed: bool | None = None


def _optional_text(values: dict[str, Any], key: str) -> str | None:
    value = values.get(key)
    return str(value) if value is not None else None


def _skill_activity_record(event_id: str, values: dict[str, Any]) -> SkillActivityRecord:
    return SkillActivityRecord(
        event_id=event_id,
        timestamp=_timestamp(),
        event_name=str(values["event_name"]),
        source=str(values["source"]),
        skill_id=_optional_text(values, "skill_id"),
        snapshot_id=_optional_text(values, "snapshot_id"),
        content_sha256=_optional_text(values, "content_sha256"),
        project_id=_optional_text(values, "project_id"),
        activation_id=_optional_text(values, "activation_id"),
        request_id=_optional_text(values, "request_id"),
        outcome=str(values["outcome"]),
        duration_ms=values.get("duration_ms"),
        error_class=_optional_text(values, "error_class"),
        total_tokens=values.get("total_tokens"),
        tool_calls=values.get("tool_calls"),
        retries=values.get("retries"),
        verification_passed=values.get("verification_passed"),
    )


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
    recent_skill_activity: tuple[SkillActivityRecord, ...] = ()

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
        self._skill_activity: deque[SkillActivityRecord] = deque(maxlen=max_recent_calls)
        self._processes: dict[int, ActiveProcessRecord] = {}
        self._searches: dict[str, ActiveSearchRecord] = {}
        self._next_call_id = 1
        self._next_request_id = 1
        self._next_skill_event_id = 1
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

    def reserve_boundary_request_id(self) -> str:
        with self._lock:
            request_id = f"request-{self._next_request_id:06d}"
            self._next_request_id += 1
            return request_id

    def record_boundary_request(
        self,
        *,
        method: str,
        outcome: str,
        tool_name: str | None = None,
        error_type: str | None = None,
        request_id: str | None = None,
    ) -> str:
        selected = request_id or self.reserve_boundary_request_id()
        with self._lock:
            self._boundary_requests.appendleft(
                BoundaryRequestRecord(
                    request_id=selected,
                    timestamp=_timestamp(),
                    method=str(method),
                    outcome=str(outcome),
                    tool_name=str(tool_name) if tool_name is not None else None,
                    error_type=str(error_type) if error_type is not None else None,
                )
            )
            return selected

    def record_skill_activity(self, **values: Any) -> None:
        with self._lock:
            event_id = f"skill-event-{self._next_skill_event_id:06d}"
            self._next_skill_event_id += 1
            self._skill_activity.appendleft(_skill_activity_record(event_id, values))

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
                recent_skill_activity=tuple(self._skill_activity),
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
    "RuntimeObservability",
    "RuntimeObservabilitySnapshot",
    "SkillActivityRecord",
    "ToolCallRecord",
    "boundary_request_context",
    "current_request_id",
    "get_runtime_observability",
    "reset_runtime_observability_for_tests",
]
