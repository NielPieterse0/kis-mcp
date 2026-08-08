from __future__ import annotations

import asyncio
import json

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
from kis_mcp.capabilities.surface import capability_control_contribution
from kis_mcp.capabilities.tools import register_capability_tools
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


def test_generic_execution_budgets_oversized_provider_result() -> None:
    server = FastMCP("execution-budget-test")

    @server.tool
    def huge_external() -> dict[str, object]:
        return {
            "workflow_runs": [
                {
                    "id": index,
                    "repository": {
                        "name": "kis-mcp",
                        "description": "x" * 12_000,
                    },
                }
                for index in range(20)
            ]
        }

    runtime = state(contribution("github-like", "huge_external", OperationEffect.EXTERNAL))
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool(
            "execute_external_action",
            {"operation": "huge_external", "arguments": {}},
        )
    ).structured_content

    assert payload is not None
    assert payload["truncated"] is True
    assert payload["reason"] == "RESULT_BUDGET_EXCEEDED"
    assert payload["operation"] == "huge_external"
    assert payload["original_chars"] > payload["max_chars"]
    assert payload["preview"]["workflow_runs"]["omitted_items"] == 10
    assert len(json.dumps(payload, ensure_ascii=False)) < payload["max_chars"]


def test_generic_execution_preserves_small_provider_result() -> None:
    server = FastMCP("execution-budget-small-test")

    @server.tool
    def small_external() -> dict[str, object]:
        return {"items": [{"id": 1, "name": "ok"}], "count": 1}

    runtime = state(contribution("github-like", "small_external", OperationEffect.EXTERNAL))
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool(
            "execute_external_action",
            {"operation": "small_external", "arguments": {}},
        )
    ).structured_content

    assert payload == {"items": [{"id": 1, "name": "ok"}], "count": 1}


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



def test_execution_router_rejects_capability_control_recursion() -> None:
    server = FastMCP("execution-recursion-test")
    runtime = state(capability_control_contribution())
    router = CapabilityExecutionRouter(server, runtime)

    with pytest.raises(ToolError, match="DISPATCH_RECURSION_BLOCKED"):
        asyncio.run(
            router.execute_read(
                "execute_read_action",
                {"operation": "execute_read_action", "arguments": {}},
            )
        )



def test_runtime_capabilities_exclude_contributions_without_registered_operations() -> None:
    base = contribution("unregistered", "missing_tool", OperationEffect.READ_ONLY)
    from dataclasses import replace

    disabled_operation = replace(base.operations[0], enabled=False)
    unavailable_operation_contribution = replace(
        base, operations=(disabled_operation,)
    )
    skill_like = CapabilityContribution(
        contribution_id="skill-like",
        domain=CapabilityDomain.SKILL,
        category="analysis",
        capabilities=("analysis.skill",),
        operations=(),
        dependencies=(),
        effects=(OperationEffect.READ_ONLY,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="skill-like",
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )

    runtime = state(unavailable_operation_contribution, skill_like)

    assert "unregistered.operate" not in runtime.available_capabilities
    assert "analysis.skill" in runtime.available_capabilities



def test_capability_search_reports_per_category_truncation() -> None:
    def skill_like(contribution_id: str) -> CapabilityContribution:
        return CapabilityContribution(
            contribution_id=contribution_id,
            domain=CapabilityDomain.SKILL,
            category="alpha-analysis",
            capabilities=(f"{contribution_id}.alpha",),
            operations=(),
            dependencies=(),
            effects=(OperationEffect.READ_ONLY,),
            readiness_probe=lambda: ReadinessSnapshot(
                contribution_id=contribution_id,
                state=ReadinessState.READY,
                summary="ready",
            ),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
            quality=default_quality(),
        )

    runtime = state(skill_like("alpha-one"), skill_like("alpha-two"))
    server = FastMCP("search-truncation-test")
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool("search_capabilities", {"query": "alpha", "limit": 1})
    ).structured_content

    assert payload is not None
    assert len(payload["contributions"]) == 1
    assert payload["truncated"] is True


def test_describe_exact_operation_is_bounded_and_includes_invocation_schema() -> None:
    provider = CapabilityContribution(
        contribution_id="provider.github-mcp",
        domain=CapabilityDomain.PROVIDER,
        category="connector",
        capabilities=(
            "operation.github_create_pull_request",
            "operation.github_get_gist",
            "repository.git",
        ),
        operations=(
            OperationDescriptor(
                operation_id="runtime.github_create_pull_request",
                name="github_create_pull_request",
                description="Create a pull request.",
                capabilities=("operation.github_create_pull_request", "repository.git"),
                effects=(OperationEffect.EXTERNAL,),
                dependencies=(),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
                quality=default_quality(),
                input_schema={
                    "type": "object",
                    "properties": {"title": {"type": "string"}},
                    "required": ["title"],
                },
            ),
            OperationDescriptor(
                operation_id="runtime.github_get_gist",
                name="github_get_gist",
                description="Read a gist.",
                capabilities=("operation.github_get_gist", "repository.git"),
                effects=(OperationEffect.EXTERNAL, OperationEffect.READ_ONLY),
                dependencies=(),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
                quality=default_quality(),
            ),
        ),
        dependencies=(),
        effects=(OperationEffect.EXTERNAL, OperationEffect.READ_ONLY),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="provider.github-mcp",
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )
    runtime = state(provider)
    server = FastMCP("describe-exact-test")
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool(
            "describe_capability",
            {"capability_id": "operation.github_create_pull_request"},
        )
    ).structured_content

    assert payload is not None
    assert payload["contributions"] == []
    assert [item["name"] for item in payload["operations"]] == [
        "github_create_pull_request"
    ]
    assert payload["operations"][0]["input_schema"]["required"] == ["title"]
    assert payload["operations"][0]["execution_surface"] == "execute_external_action"


def test_capability_search_ranks_exact_operation_before_generic_git_matches() -> None:
    provider = CapabilityContribution(
        contribution_id="provider.github-mcp",
        domain=CapabilityDomain.PROVIDER,
        category="connector",
        capabilities=("operation.github_merge_pull_request", "repository.git"),
        operations=(
            OperationDescriptor(
                operation_id="runtime.github_get_gist",
                name="github_get_gist",
                description="Read a gist.",
                capabilities=("operation.github_get_gist", "repository.git"),
                effects=(OperationEffect.EXTERNAL, OperationEffect.READ_ONLY),
                dependencies=(),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
                quality=default_quality(),
            ),
            OperationDescriptor(
                operation_id="runtime.github_merge_pull_request",
                name="github_merge_pull_request",
                description="Merge a pull request.",
                capabilities=("operation.github_merge_pull_request", "repository.git"),
                effects=(OperationEffect.EXTERNAL,),
                dependencies=(),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
                quality=default_quality(),
            ),
        ),
        dependencies=(),
        effects=(OperationEffect.EXTERNAL, OperationEffect.READ_ONLY),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="provider.github-mcp",
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )
    runtime = state(provider)
    server = FastMCP("search-ranking-test")
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool(
            "search_capabilities",
            {"query": "github_merge_pull_request git", "limit": 10},
        )
    ).structured_content

    assert payload is not None
    assert payload["operations"][0]["operation_name"] == "github_merge_pull_request"
    assert payload["operations"][0]["match_score"] > payload["operations"][1]["match_score"]
