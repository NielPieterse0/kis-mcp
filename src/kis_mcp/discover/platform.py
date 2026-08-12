from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from ..config import RuntimeConfig
from ..projects import ProjectRegistry
from .change_service import InspectChangeService
from .git_change_reader import GitChangeReader
from .intelligence import ProjectIntelligenceService
from .read_authority import ReadAuthority
from .semantic import SemanticEvidenceProvider
from .service import InspectProjectService
from .planning import PlanChangeService
from .tools import register_change_tools, register_discover_tools, register_plan_change_tool

from ..capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationDescriptor,
    OperationEffect,
    ReadinessSnapshot,
    ReadinessState,
)
from ..capabilities.normalization import default_quality


def _ready(contribution_id: str) -> ReadinessSnapshot:
    return ReadinessSnapshot(
        contribution_id=contribution_id,
        state=ReadinessState.READY,
        summary="Discover capability is available.",
    )


def discover_capability_contributions() -> tuple[CapabilityContribution, ...]:
    project_id = "discover.project"
    change_id = "discover.change"
    project_operation = OperationDescriptor(
        operation_id="discover.inspect-project",
        name="inspect_project",
        description="Return bounded deterministic local repository evidence.",
        capabilities=("repository.inspect", "repository.git-read"),
        effects=(OperationEffect.READ_ONLY,),
        dependencies=(),
        exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=95),
        quality=default_quality(context_cost=20, reliability=95, workflow_integration=95),
    )
    change_operation = OperationDescriptor(
        operation_id="discover.inspect-change",
        name="inspect_change",
        description="Inspect the current working tree and affected repository scopes.",
        capabilities=("git.change.inspect", "repository.git-read"),
        effects=(OperationEffect.READ_ONLY,),
        dependencies=(),
        exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=98),
        quality=default_quality(context_cost=15, reliability=95, workflow_integration=100),
    )
    plan_operation = OperationDescriptor(
        operation_id="discover.plan-change",
        name="plan_change",
        description="Prepare bounded change scope, affected tests, verification, and active-claim evidence.",
        capabilities=("code.change.plan", "change.impact.analyze", "repository.inspect"),
        effects=(OperationEffect.READ_ONLY,),
        dependencies=(),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=90),
        quality=default_quality(context_cost=25, reliability=95, workflow_integration=100),
    )
    return (
        CapabilityContribution(
            contribution_id=project_id,
            domain=CapabilityDomain.DISCOVER,
            category="repository-analysis",
            capabilities=("repository.inspect", "repository.git-read", "verification.discover"),
            operations=(project_operation,),
            dependencies=(),
            effects=(OperationEffect.READ_ONLY,),
            readiness_probe=lambda: _ready(project_id),
            exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=95),
            quality=default_quality(context_cost=20, reliability=95, workflow_integration=95),
        ),
        CapabilityContribution(
            contribution_id=change_id,
            domain=CapabilityDomain.DISCOVER,
            category="change-analysis",
            capabilities=(
                "git.change.inspect",
                "repository.git-read",
                "repository.inspect",
                "change.impact.analyze",
                "contract.change.inspect",
                "code.change.plan",
            ),
            operations=(change_operation, plan_operation),
            dependencies=(),
            effects=(OperationEffect.READ_ONLY,),
            readiness_probe=lambda: _ready(change_id),
            exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=98),
            quality=default_quality(context_cost=15, reliability=95, workflow_integration=100),
        ),
    )


def register_platform_discover(
    server: FastMCP,
    runtime: RuntimeConfig,
    projects: ProjectRegistry | None = None,
    semantic_provider: SemanticEvidenceProvider | None = None,
) -> None:
    boundary = Path(runtime.project_boundary)
    intelligence = ProjectIntelligenceService(
        boundary=boundary,
        settings=runtime.discover_settings,
        projects=projects,
        semantic_provider=semantic_provider,
    )
    register_discover_tools(
        server,
        InspectProjectService(
            boundary=boundary,
            settings=runtime.discover_settings,
            projects=projects,
            intelligence_service=intelligence,
        ),
    )
    register_plan_change_tool(
        server,
        PlanChangeService(
            boundary=boundary,
            settings=runtime.discover_settings,
            intelligence_service=intelligence,
        ),
    )
    change_server = FastMCP("kis-mcp-discover-change")
    register_change_tools(
        change_server,
        InspectChangeService(
            GitChangeReader(
                authority=ReadAuthority(boundary, runtime.discover_settings),
                settings=runtime.discover_settings,
            ),
            intelligence_service=intelligence,
        ),
    )
    server.mount(change_server)


__all__ = ["discover_capability_contributions", "register_platform_discover"]
