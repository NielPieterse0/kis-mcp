from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from kis_mcp.config import load_runtime_config
from kis_mcp.providers.registry import ProviderRegistry
from kis_mcp.providers.service import ProviderService
from kis_mcp.work_management import (
    BackendBindingSettings,
    EvidenceSettings,
    FeatureMode,
    GateMode,
    ManagedProject,
    ProjectOwnerType,
    WorkManagementSettings,
)
from kis_mcp.workflows.code_review import load_agent_settings_or_disabled
from kis_mcp.workflows.platform import register_platform_workflows, workflow_descriptors


class Service:
    pass


def settings(enabled: bool) -> WorkManagementSettings:
    return WorkManagementSettings(
        enabled=enabled,
        portfolio_id="default",
        managed_projects=(
            ManagedProject(
                project_id="alpha-project",
                local_root="C:\\Projects\\alpha",
                repository="ExampleOwner/alpha",
                backend_binding="github-default",
            ),
        ),
        backend_bindings=(
            BackendBindingSettings(
                binding_id="github-default",
                provider="github-mcp",
                owner="ExampleOwner",
                owner_type=ProjectOwnerType.USER,
                project_number=12,
            ),
        ),
        features=(("programme_status", FeatureMode.ENABLED),),
        gates=(("programme_drift", GateMode.ADVISORY),),
        evidence=EvidenceSettings(),
    )


def test_platform_descriptors_include_p5_workflows() -> None:
    workflow_ids = {item.workflow_id for item in workflow_descriptors()}

    assert {
        "capture-project-work",
        "persist-review-evidence",
        "reconcile-project-state",
        "report-programme-status",
        "verify-change-traceability",
    }.issubset(workflow_ids)


def test_disabled_settings_add_no_project_management_tools() -> None:
    server = FastMCP("root")
    register_platform_workflows(
        server,
        load_runtime_config(),
        load_agent_settings_or_disabled(),
        ProviderService(ProviderRegistry()),
        work_management_settings=settings(False),
        work_management_service=Service(),
    )

    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert "review_change_with_agent" in names
    assert not any(name.startswith("project_management_") for name in names)


def test_enabled_settings_mount_project_management_tools() -> None:
    server = FastMCP("root")
    register_platform_workflows(
        server,
        load_runtime_config(),
        load_agent_settings_or_disabled(),
        ProviderService(ProviderRegistry()),
        work_management_settings=settings(True),
        work_management_service=Service(),
    )

    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert {
        "project_management_inventory",
        "project_management_admit_work",
        "project_management_reconcile",
        "project_management_portfolio_status",
        "project_management_persist_review",
        "project_management_verify_traceability",
    }.issubset(names)
