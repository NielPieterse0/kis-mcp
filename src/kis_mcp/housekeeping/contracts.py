from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

SCHEMA_VERSION = 1


class RunnerKind(StrEnum):
    WORK_MANAGEMENT_RECONCILIATION = "work_management_reconciliation"
    BACKLOG_READINESS = "backlog_readiness"


class RunMode(StrEnum):
    PREVIEW = "preview"
    APPLY = "apply"


class TriggerKind(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class FindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CONFLICT = "conflict"


class FindingKind(StrEnum):
    MISSING_PROJECT_RECORD = "missing_project_record"
    SOURCE_CLOSED_PROJECT_ACTIVE = "source_closed_project_active"
    PROJECT_DONE_SOURCE_OPEN = "project_done_source_open"
    STALE_EXECUTION_CLAIM = "stale_execution_claim"
    CHANGE_PROJECTION_MISSING = "change_projection_missing"
    BLOCKED_WITHOUT_DEPENDENCY = "blocked_without_dependency"
    DEPENDENCY_WITHOUT_BLOCKED_STATE = "dependency_without_blocked_state"
    RESOLVED_DEPENDENCY_STILL_BLOCKING = "resolved_dependency_still_blocking"
    AMBIGUOUS_DEPENDENCY = "ambiguous_dependency"
    MISSING_READY_METADATA = "missing_ready_metadata"
    INVENTORY_INCOMPLETE = "inventory_incomplete"
    DUPLICATE_SOURCE_BINDING = "duplicate_source_binding"
    AUTHORITY_UNAVAILABLE = "authority_unavailable"
    SOURCE_EVIDENCE_INCOMPLETE = "source_evidence_incomplete"
    APPLY_FAILED = "apply_failed"


@dataclass(frozen=True, slots=True)
class HousekeepingTrigger:
    runner: RunnerKind
    mode: RunMode = RunMode.PREVIEW
    trigger_kind: TriggerKind = TriggerKind.MANUAL
    trigger_id: str = "manual"
    idempotency_key: str | None = None
    scheduled_for: str | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("trigger schema_version must be 1")
        if not isinstance(self.runner, RunnerKind):
            raise ValueError("runner must be a RunnerKind")
        if not isinstance(self.mode, RunMode):
            raise ValueError("mode must be a RunMode")
        if not isinstance(self.trigger_kind, TriggerKind):
            raise ValueError("trigger_kind must be a TriggerKind")
        if not isinstance(self.trigger_id, str) or not self.trigger_id.strip():
            raise ValueError("trigger_id must be a non-empty string")
        if self.mode is RunMode.APPLY and (
            not isinstance(self.idempotency_key, str)
            or not self.idempotency_key.strip()
        ):
            raise ValueError("apply mode requires idempotency_key")
        if self.trigger_kind is TriggerKind.SCHEDULED and (
            not isinstance(self.scheduled_for, str) or not self.scheduled_for.strip()
        ):
            raise ValueError("scheduled trigger requires scheduled_for")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "runner": self.runner.value,
            "mode": self.mode.value,
            "trigger_kind": self.trigger_kind.value,
            "trigger_id": self.trigger_id,
            "idempotency_key": self.idempotency_key,
            "scheduled_for": self.scheduled_for,
        }


@dataclass(frozen=True, slots=True)
class Finding:
    kind: FindingKind
    severity: FindingSeverity
    record_id: str
    summary: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    recommendation: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "severity": self.severity.value,
            "record_id": self.record_id,
            "summary": self.summary,
            "evidence": dict(self.evidence),
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True, slots=True)
class PlannedAction:
    action_id: str
    operation: str
    arguments: Mapping[str, Any]
    rationale: str
    safe_to_apply: bool = True

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "operation": self.operation,
            "arguments": dict(self.arguments),
            "rationale": self.rationale,
            "safe_to_apply": self.safe_to_apply,
        }


@dataclass(frozen=True, slots=True)
class HousekeepingMetrics:
    scanned_records: int = 0
    findings: int = 0
    safe_actions: int = 0
    applied_actions: int = 0
    conflicts: int = 0
    ambiguities: int = 0
    source_failures: int = 0

    def to_json_dict(self) -> dict[str, int]:
        return {
            "scanned_records": self.scanned_records,
            "findings": self.findings,
            "safe_actions": self.safe_actions,
            "applied_actions": self.applied_actions,
            "conflicts": self.conflicts,
            "ambiguities": self.ambiguities,
            "source_failures": self.source_failures,
        }


@dataclass(frozen=True, slots=True)
class HousekeepingReceipt:
    trigger: HousekeepingTrigger
    project_id: str
    repository: str
    findings: tuple[Finding, ...] = ()
    actions: tuple[PlannedAction, ...] = ()
    applied_receipts: tuple[Mapping[str, Any], ...] = ()
    metrics: HousekeepingMetrics = HousekeepingMetrics()
    selection: Mapping[str, Any] | None = None
    complete: bool = True
    conflicts: tuple[str, ...] = ()

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "trigger": self.trigger.to_json_dict(),
            "project_id": self.project_id,
            "repository": self.repository,
            "complete": self.complete,
            "conflicts": list(self.conflicts),
            "findings": [item.to_json_dict() for item in self.findings],
            "actions": [item.to_json_dict() for item in self.actions],
            "applied_receipts": [dict(item) for item in self.applied_receipts],
            "metrics": self.metrics.to_json_dict(),
            "selection": dict(self.selection) if self.selection is not None else None,
        }


__all__ = [
    "Finding",
    "FindingKind",
    "FindingSeverity",
    "HousekeepingMetrics",
    "HousekeepingReceipt",
    "HousekeepingTrigger",
    "PlannedAction",
    "RunMode",
    "RunnerKind",
    "TriggerKind",
]
