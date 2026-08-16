from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class DecisionKind(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    QUARANTINE = "quarantine"


@dataclass(frozen=True, slots=True)
class InvocationEffects:
    """Provider-neutral effects resolved from one concrete invocation.

    ``write_paths`` may write through the final path target and therefore require
    full effective-path resolution. ``entry_paths`` mutate directory entries
    (for example, move sources) and resolve only existing ancestors. Delete
    intent remains separate because it must be transformed to quarantine.

    ``unresolved_*_paths`` preserve syntactically definite mutation targets that
    cannot be statically bounded. They are structural invocation failures rather
    than evidence for any hard policy rule. ``unresolved_delete`` remains the
    targetless destructive-intent signal used for operations such as ``git clean``.
    """

    write_paths: tuple[str, ...] = ()
    entry_paths: tuple[str, ...] = ()
    delete_paths: tuple[str, ...] = ()
    unresolved_delete: bool = False
    external_network: bool = False
    unresolved_write_paths: tuple[str, ...] = ()
    unresolved_entry_paths: tuple[str, ...] = ()
    unresolved_delete_paths: tuple[str, ...] = ()

    @property
    def mutated_paths(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys((*self.write_paths, *self.entry_paths, *self.delete_paths))
        )


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    kind: DecisionKind
    code: str
    message: str
    rule_id: str | None = None
    paths: tuple[str, ...] = field(default_factory=tuple)

    @property
    def allowed(self) -> bool:
        return self.kind is DecisionKind.ALLOW


PUBLIC_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PolicyRuleResponse:
    id: str
    name: str
    prohibited_outcome: str
    decision: str


@dataclass(frozen=True, slots=True)
class HealthResponse:
    ready: bool
    server: str
    project_boundary: str
    quarantine_root: str
    desktop_commander_entry: str
    desktop_commander_installed: bool
    policy_rules: tuple[PolicyRuleResponse, ...]
    policy_fingerprint: str
    runtime_instance: str
    server_instance_id: str
    server_started_at: str
    source_revision: str
    contract_fingerprint: str
    transport: Mapping[str, str | bool]
    implementation_status: Mapping[str, str]
    schema_version: int = PUBLIC_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class QuarantineResponse:
    operation_id: str
    original_path: str
    payload_path: str
    item_type: str
    quarantined_at: str
    restored_at: str | None
    schema_version: int = PUBLIC_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class QuarantineListResponse:
    records: tuple[QuarantineResponse, ...]
    schema_version: int = PUBLIC_SCHEMA_VERSION
