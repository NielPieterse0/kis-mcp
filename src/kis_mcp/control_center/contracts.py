from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from kis_mcp.runtime_observability import RuntimeObservabilitySnapshot


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
class ProviderRuntimeSummary:
    provider_id: str
    namespace: str
    registered: bool
    enabled: bool
    mounted: bool
    state: str
    readiness: str
    action: str
    commissioning: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ApprovalSummary:
    approval_id: str
    title: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class DiscoverSummary:
    status: str
    project_id: str | None
    languages: tuple[str, ...]
    frameworks: tuple[str, ...]
    module_count: int
    finding_count: int
    confidence: str
    truncated: bool
    findings: tuple[str, ...]
    detail: str


@dataclass(frozen=True, slots=True)
class QuarantineRecordSummary:
    operation_id: str
    original_path: str
    item_type: str
    restored: bool


@dataclass(frozen=True, slots=True)
class AvailableAction:
    label: str
    tool_name: str
    kind: str


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
    approvals: tuple[ApprovalSummary, ...]
    discover: DiscoverSummary
    providers: tuple[ProviderSummary, ...]
    provider_runtime: tuple[ProviderRuntimeSummary, ...]
    observability: RuntimeObservabilitySnapshot
    quarantine: QuarantineSummary
    quarantine_records: tuple[QuarantineRecordSummary, ...]
    actions: tuple[AvailableAction, ...]
    verification: VerificationSummary
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict[str, Any]:
        document = asdict(self)
        from kis_mcp.work_management.board_bridge import get_work_board_bridge

        document["work_board"] = dict(get_work_board_bridge().current())
        return document
