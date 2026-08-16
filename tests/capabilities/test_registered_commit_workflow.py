from __future__ import annotations

import asyncio
from dataclasses import replace

from fastmcp import FastMCP

from kis_mcp.capabilities.contracts import OperationEffect
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.capabilities.surface import (
    augment_with_runtime_surface,
    capability_control_contribution,
)
from kis_mcp.config import load_runtime_config
from kis_mcp.providers.registry import ProviderRegistry
from kis_mcp.providers.service import ProviderService
from kis_mcp.work_management import load_work_management_settings
from kis_mcp.workflows.code_review import load_agent_settings_or_disabled
from kis_mcp.workflows.platform import register_platform_workflows, workflow_descriptors

EXACT_OPERATIONS = {
    "kis_github_publish_registered_commit",
    "kis_github_reconcile_registered_commit",
    "kis_github_create_registered_pull_request",
    "kis_github_configure_registered_repository",
    "kis_github_commission_registered_project_schema",
    "kis_github_merge_registered_pull_request",
    "kis_github_delete_registered_branch",
}


def test_exact_registered_github_operations_do_not_expand_direct_profile() -> None:
    settings = load_capability_settings()

    assert settings.direct_profile_max == 24
    assert len(settings.direct_operations) <= 24
    assert EXACT_OPERATIONS.isdisjoint(settings.direct_operations)
    assert "execute_external_action" in settings.direct_operations


def test_platform_registration_preserves_existing_local_tool_surface() -> None:
    server = FastMCP("root")
    work_management = replace(load_work_management_settings(), enabled=False)

    register_platform_workflows(
        server,
        load_runtime_config(),
        load_agent_settings_or_disabled(),
        ProviderService(ProviderRegistry()),
        work_management_settings=work_management,
    )

    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert EXACT_OPERATIONS.isdisjoint(names)


def test_capability_control_declares_virtual_exact_github_operations() -> None:
    contribution = capability_control_contribution()
    operations = {item.name: item for item in contribution.operations}

    assert EXACT_OPERATIONS.issubset(operations)
    for name in EXACT_OPERATIONS:
        operation = operations[name]
        assert operation.effects == (OperationEffect.EXTERNAL,)
        assert operation.approval_required is True
        assert "virtual" in operation.tags
        assert "registered-github" in operation.tags
        assert operation.input_schema["properties"]["approved"]["type"] == "boolean"
        assert "approved" in operation.input_schema["required"]


def test_pre_review_registered_github_operations_expose_timeout_recovery_controls() -> None:
    contribution = capability_control_contribution()
    operations = {item.name: item for item in contribution.operations}

    for name in {
        "kis_github_publish_registered_commit",
        "kis_github_reconcile_registered_commit",
        "kis_github_create_registered_pull_request",
    }:
        properties = operations[name].input_schema["properties"]
        assert properties["status_only"]["type"] == "boolean"
        assert properties["deadline_ms"] == {
            "type": "integer",
            "minimum": 1,
            "maximum": 300000,
        }
        assert "status_only" not in operations[name].input_schema["required"]
        assert "deadline_ms" not in operations[name].input_schema["required"]


def test_runtime_surface_preserves_capability_control_virtual_operations() -> None:
    contribution = capability_control_contribution()
    augmented = augment_with_runtime_surface((contribution,), (), {})
    control = next(
        item for item in augmented if item.contribution_id == "capability-control"
    )
    operations = {item.name: item for item in control.operations}

    assert EXACT_OPERATIONS.issubset(operations)
    assert all(operations[name].enabled is True for name in EXACT_OPERATIONS)


def test_workflow_descriptors_route_publish_and_closeout_to_virtual_operations() -> None:
    descriptors = {item.workflow_id: item for item in workflow_descriptors()}

    publish = descriptors["publish-registered-commit"]
    assert "operation.kis_github_publish_registered_commit" in publish.capabilities
    assert publish.required_steps == ("kis_github_publish_registered_commit",)

    closeout = descriptors["pull-request-safe-closeout"]
    assert closeout.required_steps[:4] == (
        "inspect_change",
        "github_pull_request_read",
        "github_actions_list",
        "github_actions_get",
    )
    assert "run_verification" not in closeout.required_steps
    assert "kis_github_merge_registered_pull_request" in closeout.required_steps
    assert "kis_github_delete_registered_branch" in closeout.required_steps
    assert "github_merge_pull_request" not in closeout.required_steps
