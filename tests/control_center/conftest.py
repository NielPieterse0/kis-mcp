from __future__ import annotations

import pytest

from kis_mcp.control_center.contracts import (
    ControlCenterSnapshot,
    Diagnostic,
    GitSummary,
    PolicyRuleSummary,
    PolicySummary,
    ProjectSummary,
    ProviderSummary,
    QuarantineSummary,
    RuntimeSummary,
    VerificationSummary,
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
        quarantine=QuarantineSummary(
            root=r"C:\Projects\.kis-mcp\quarantine",
            status="available",
            total_records=2,
            active_records=1,
            restored_records=1,
            invalid_records=0,
            truncated=False,
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
