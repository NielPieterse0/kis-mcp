from __future__ import annotations

from fastmcp import FastMCP

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
from .registry import ProjectRegistry


def project_capability_contribution() -> CapabilityContribution:
    exposure = ExposurePolicy(mode=ExposureMode.DIRECT, priority=98)
    quality = default_quality(
        context_cost=5,
        reversibility=100,
        reliability=95,
        workflow_integration=95,
    )
    operations = (
        OperationDescriptor(
            operation_id="projects.list",
            name="kis_list_projects",
            description="List configured KIS projects and their routing bindings.",
            capabilities=("project.context.read",),
            effects=(OperationEffect.READ_ONLY,),
            dependencies=(),
            exposure=exposure,
            quality=quality,
        ),
        OperationDescriptor(
            operation_id="projects.status",
            name="kis_project_status",
            description="Describe one configured KIS project and provider routing bindings.",
            capabilities=("project.context.read",),
            effects=(OperationEffect.READ_ONLY,),
            dependencies=(),
            exposure=exposure,
            quality=quality,
        ),
    )
    return CapabilityContribution(
        contribution_id="projects",
        domain=CapabilityDomain.TOOL,
        category="project-context",
        capabilities=("project.context.read",),
        operations=operations,
        dependencies=(),
        effects=(OperationEffect.READ_ONLY,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="projects",
            state=ReadinessState.READY,
            summary="Configured project registry is ready.",
        ),
        exposure=exposure,
        quality=quality,
    )


def register_project_tools(server: FastMCP, registry: ProjectRegistry) -> None:
    @server.tool
    def kis_list_projects() -> dict[str, object]:
        """List explicitly configured projects and their non-secret routing bindings."""

        return {
            "schema_version": registry.schema_version,
            "default_project_id": registry.default_project_id,
            "projects": [project.to_json_dict() for project in registry.projects],
        }

    @server.tool
    def kis_project_status(project_id: str) -> dict[str, object]:
        """Describe one configured project by stable project ID."""

        return {
            "schema_version": registry.schema_version,
            "project": registry.project(project_id).to_json_dict(),
        }


__all__ = ["project_capability_contribution", "register_project_tools"]
