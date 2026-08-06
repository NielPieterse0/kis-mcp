from __future__ import annotations

import asyncio

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationDescriptor,
    OperationEffect,
    ReadinessSnapshot,
    ReadinessState,
)
from kis_mcp.capabilities.exposure import ExposureMiddleware, ExposurePlanner
from kis_mcp.capabilities.execution import CapabilityExecutionRouter
from kis_mcp.capabilities.normalization import default_quality
from kis_mcp.capabilities.runtime import CapabilityRuntimeState
from kis_mcp.capabilities.settings import load_capability_settings


def contribution(
    contribution_id: str,
    operation_name: str,
    effect: OperationEffect,
    *,
    readiness: ReadinessState = ReadinessState.READY,
    direct: bool = False,
    approval_required: bool = False,
) -> CapabilityContribution:
    operation = OperationDescriptor(
        operation_id=f"{contribution_id}.{operation_name}",
        name=operation_name,
        description=f"Run {operation_name}.",
        capabilities=(f"{contribution_id}.operate",),
        effects=(effect,),
        dependencies=(),
        exposure=ExposurePolicy(
            mode=ExposureMode.DIRECT if direct else ExposureMode.DISCOVERABLE,
            priority=90,
        ),
        quality=default_quality(),
        approval_required=approval_required,
    )
    return CapabilityContribution(
        contribution_id=contribution_id,
        domain=CapabilityDomain.TOOL,
        category="test-tool",
        capabilities=(f"{contribution_id}.operate",),
        operations=(operation,),
        dependencies=(),
        effects=(effect,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id=contribution_id,
            state=readiness,
            summary=readiness.value,
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )


def state(*contributions: CapabilityContribution) -> CapabilityRuntimeState:
    settings = load_capability_settings()
    return CapabilityRuntimeState.build(
        CapabilityCatalogue(contributions, ()),
        settings,
    )


def test_exposure_planner_filters_unavailable_and_long_tail() -> None:
    runtime = state(
        contribution("core", "read_file", OperationEffect.READ_ONLY, direct=True),
        contribution("long-tail", "rare_tool", OperationEffect.READ_ONLY),
        contribution(
            "offline",
            "inspect_project",
            OperationEffect.READ_ONLY,
            readiness=ReadinessState.UNAVAILABLE,
            direct=True,
        ),
    )

    plan = ExposurePlanner(runtime).plan()

    assert "read_file" in plan.direct_operations
    assert "rare_tool" not in plan.direct_operations
    assert "inspect_project" not in plan.direct_operations
    assert "rare_tool" in plan.discoverable_operations
    assert "inspect_project" in plan.status_only_operations


def test_explicit_valid_operation_can_be_exposed_without_overriding_readiness() -> None:
    runtime = state(
        contribution("ready", "rare_tool", OperationEffect.READ_ONLY),
        contribution(
            "offline",
            "offline_tool",
            OperationEffect.READ_ONLY,
            readiness=ReadinessState.UNAVAILABLE,
        ),
    )

    plan = ExposurePlanner(runtime).plan(explicit_operations={"rare_tool", "offline_tool"})

    assert "rare_tool" in plan.direct_operations
    assert "offline_tool" not in plan.direct_operations


def test_exposure_middleware_hides_long_tail_but_does_not_disable_calling() -> None:
    server = FastMCP("exposure-test")

    @server.tool
    def visible_tool() -> str:
        return "visible"

    @server.tool
    def hidden_tool() -> str:
        return "hidden"

    server.add_middleware(ExposureMiddleware({"visible_tool"}))

    async def run() -> tuple[set[str], str]:
        async with Client(server) as client:
            names = {item.name for item in await client.list_tools()}
            result = await client.call_tool("hidden_tool", {})
            return names, result.content[0].text

    names, result = asyncio.run(run())
    assert names == {"visible_tool"}
    assert result == "hidden"


def test_execution_router_preserves_original_schema_and_effect_boundary() -> None:
    server = FastMCP("execution-test")

    @server.tool
    def hidden_read(value: int) -> int:
        return value * 2

    runtime = state(contribution("hidden", "hidden_read", OperationEffect.READ_ONLY))
    router = CapabilityExecutionRouter(server, runtime)

    result = asyncio.run(router.execute_read("hidden_read", {"value": 4}))
    assert result.structured_content == {"result": 8}

    with pytest.raises(Exception, match="validation"):
        asyncio.run(router.execute_read("hidden_read", {"value": "bad"}))
    with pytest.raises(ToolError, match="EFFECT_MISMATCH"):
        asyncio.run(router.execute_change("hidden_read", {"value": 4}))


def test_execution_router_never_bypasses_approval_or_readiness() -> None:
    server = FastMCP("execution-gates-test")

    @server.tool
    def merge_tool() -> str:
        return "merged"

    approval_state = state(
        contribution(
            "approval",
            "merge_tool",
            OperationEffect.EXTERNAL,
            approval_required=True,
        )
    )
    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        asyncio.run(
            CapabilityExecutionRouter(server, approval_state).execute_external(
                "merge_tool", {}
            )
        )

    unavailable_state = state(
        contribution(
            "unavailable",
            "merge_tool",
            OperationEffect.EXTERNAL,
            readiness=ReadinessState.UNAVAILABLE,
        )
    )
    with pytest.raises(ToolError, match="OPERATION_INELIGIBLE"):
        asyncio.run(
            CapabilityExecutionRouter(server, unavailable_state).execute_external(
                "merge_tool", {}
            )
        )
