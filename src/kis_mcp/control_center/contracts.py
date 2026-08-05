from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class RuntimeSummary:
    status: str
    product: str
    server: str
    desktop_commander_version: str
    desktop_commander_installed: bool | None
    implementation_status: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class GitSummary:
    status: str
    branch: str | None
    dirty: bool | None
    changed_files: int | None
    detail: str


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    path: str
    exists: bool
    git: GitSummary


@dataclass(frozen=True, slots=True)
class PolicyRuleSummary:
    rule_id: str
    name: str
    prohibited_outcome: str
    decision: str


@dataclass(frozen=True, slots=True)
class PolicySummary:
    status: str
    closed_rule_set: bool
    rules: tuple[PolicyRuleSummary, ...]


@dataclass(frozen=True, slots=True)
class ProviderSummary:
    provider_id: str
    namespace: str
    enabled: bool
    readiness: str
    action: str


@dataclass(frozen=True, slots=True)
class QuarantineSummary:
    root: str
    status: str
    total_records: int
    active_records: int
    restored_records: int
    invalid_records: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class VerificationSummary:
    status: str
    command: tuple[str, ...]
    detail: str


@dataclass(frozen=True, slots=True)
class ControlCenterSnapshot:
    schema_version: int
    generated_at: str
    runtime: RuntimeSummary
    project: ProjectSummary
    policy: PolicySummary
    providers: tuple[ProviderSummary, ...]
    quarantine: QuarantineSummary
    verification: VerificationSummary
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
