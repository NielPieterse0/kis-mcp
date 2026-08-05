from __future__ import annotations

import pytest

from kis_mcp.control_center.contracts import (
    ApprovalSummary,
    AvailableAction,
    ControlCenterSnapshot,
    Diagnostic,
    DiscoverSummary,
    GitSummary,
    PolicyRuleSummary,
    PolicySummary,
    ProjectSummary,
    ProviderRuntimeSummary,
    ProviderSummary,
    QuarantineRecordSummary,
    QuarantineSummary,
    RuntimeSummary,
    VerificationSummary,
)
from kis_mcp.runtime_observability import (
    ActiveProcessRecord,
    ActiveSearchRecord,
    RuntimeObservabilitySnapshot,
    ToolCallRecord,
)


@pytest.fixture
def sample_snapshot() -> ControlCenterSnapshot:
    return ControlCenterSnapshot(
        schema_version=1,
        generated_at="2026-08-05T03:00:00+00:00",
        runtime=RuntimeSummary(
            status="available",
            product="kis-mcp <operator>",
            server="kis-mcp",
            desktop_commander_version="0.2.46",
            desktop_commander_installed=True,
            implementation_status=(("policy_core", "verified"),),
        ),
        project=ProjectSummary(
            path=r"C:\Projects\kis-mcp",
            exists=True,
            git=GitSummary(
                status="available",
                branch="main<script>alert(1)</script>",
                dirty=False,
                changed_files=0,
                detail="Local status only.",
            ),
        ),
        policy=PolicySummary(
            status="available",
            closed_rule_set=True,
            rules=(
                PolicyRuleSummary(
                    rule_id="HR-001",
                    name="Write boundary",
                    prohibited_outcome="write outside C:\\Projects",
                    decision="block",
                ),
                PolicyRuleSummary(
                    rule_id="HR-002",
                    name="External network",
                    prohibited_outcome="external network through Work",
                    decision="block",
                ),
                PolicyRuleSummary(
                    rule_id="HR-003",
                    name="Permanent deletion",
                    prohibited_outcome="permanent deletion",
                    decision="quarantine",
                ),
            ),
        ),
        approvals=(
            ApprovalSummary(
                approval_id="HR1-01",
                title="Outside write resolver",
                status="pending",
                detail="Operator decision required.",
            ),
        ),
        discover=DiscoverSummary(
            status="available",
            project_id="project-1",
            languages=("Python",),
            frameworks=("FastMCP",),
            module_count=8,
            finding_count=1,
            confidence="high",
            truncated=False,
            findings=("Sample finding <unsafe>",),
            detail="Bounded local inspect_project evidence.",
        ),
        providers=(
            ProviderSummary(
                provider_id="github-mcp",
                namespace="github",
                enabled=True,
                readiness="runtime_check_required",
                action="Use kis_provider_status.",
            ),
            ProviderSummary(
                provider_id="supabase",
                namespace="supabase",
                enabled=True,
                readiness="runtime_check_required",
                action="Use kis_provider_status.",
            ),
        ),
        provider_runtime=(
            ProviderRuntimeSummary(
                provider_id="control-center",
                namespace="controlcenter",
                registered=True,
                enabled=True,
                mounted=True,
                state="mounted",
                readiness="ready",
                action="Local dashboard ready.",
                commissioning=(("live_verified", "not_applicable"),),
            ),
            ProviderRuntimeSummary(
                provider_id="github-mcp",
                namespace="github",
                registered=True,
                enabled=True,
                mounted=True,
                state="mounted",
                readiness="ready",
                action="Authenticate <unsafe> before live operations.",
                commissioning=(("authenticated", "required"),),
            ),
        ),
        observability=RuntimeObservabilitySnapshot(
            recent_calls=(
                ToolCallRecord(
                    timestamp="2026-08-05T02:59:00+00:00",
                    tool_name="read_file",
                    argument_keys=("path",),
                    decision="allow",
                    outcome="success",
                    code="ALLOW",
                ),
            ),
            recent_policy_decisions=(
                ToolCallRecord(
                    timestamp="2026-08-05T02:58:00+00:00",
                    tool_name="execute_command",
                    argument_keys=("command",),
                    decision="block",
                    outcome="rejected",
                    code="HR-002_EXTERNAL_NETWORK",
                ),
            ),
            active_processes=(
                ActiveProcessRecord(
                    pid=42,
                    cwd=r"C:\Projects\kis-mcp",
                    shell="powershell",
                    started_at="2026-08-05T02:50:00+00:00",
                    last_seen_at="2026-08-05T02:59:00+00:00",
                    interaction_count=2,
                ),
            ),
            active_searches=(
                ActiveSearchRecord(
                    search_id="search-1",
                    tool_name="start_search",
                    started_at="2026-08-05T02:55:00+00:00",
                    last_seen_at="2026-08-05T02:59:00+00:00",
                ),
            ),
        ),
        quarantine=QuarantineSummary(
            root=r"C:\Projects\.kis-mcp\quarantine",
            status="available",
            total_records=2,
            active_records=1,
            restored_records=1,
            invalid_records=0,
            truncated=False,
        ),
        quarantine_records=(
            QuarantineRecordSummary(
                operation_id="20260805T010203000000Z-aaaaaaaaaaaa",
                original_path=r"C:\Projects\old.txt",
                item_type="file",
                restored=False,
            ),
        ),
        actions=(
            AvailableAction("Refresh project evidence", "inspect_project", "read"),
            AvailableAction("List quarantine", "kis_list_quarantine", "read"),
            AvailableAction("Restore quarantine record", "kis_restore_quarantine", "mutation"),
        ),
        verification=VerificationSummary(
            status="not_recorded",
            command=("pwsh", "-NoProfile", "-File", "scripts/verify.ps1"),
            detail="Run verification for current evidence.",
        ),
        diagnostics=(
            Diagnostic(
                code="CONTROL_CENTER_SAMPLE",
                message="Sample <b>diagnostic</b>",
            ),
        ),
    )
