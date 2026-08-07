from __future__ import annotations

from types import SimpleNamespace

import pytest

from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationEffect,
    ReadinessSnapshot,
    ReadinessState,
)
from kis_mcp.capabilities.exposure import ExposurePlanner
from kis_mcp.capabilities.normalization import default_quality
from kis_mcp.capabilities.runtime import CapabilityRuntimeState
from kis_mcp.capabilities.settings import load_capability_settings


def _provider_contribution(state: dict[str, ReadinessState]) -> CapabilityContribution:
    contribution_id = "provider.github-mcp"
    return CapabilityContribution(
        contribution_id=contribution_id,
        domain=CapabilityDomain.PROVIDER,
        category="connector",
        capabilities=("repository.remote_read_write",),
        operations=(),
        dependencies=(),
        effects=(OperationEffect.EXTERNAL,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id=contribution_id,
            state=state["value"],
            summary="Current GitHub runtime state.",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=55),
        quality=default_quality(context_cost=40, workflow_integration=75),
    )


def test_runtime_tool_snapshot_and_readiness_refresh_without_gateway_rebuild() -> None:
    state = {"value": ReadinessState.AUTHENTICATION_REQUIRED}
    tools: list[object] = []
    runtime = CapabilityRuntimeState.build(
        CapabilityCatalogue((_provider_contribution(state),), ()),
        load_capability_settings(),
        runtime_tools_source=lambda: tuple(tools),
        provider_namespaces={"github-mcp": "github"},
    )

    with pytest.raises(KeyError, match="github_get_file_contents"):
        runtime.operation("github_get_file_contents")
    assert runtime.readiness["provider.github-mcp"].state is (
        ReadinessState.AUTHENTICATION_REQUIRED
    )

    tools.append(
        SimpleNamespace(
            name="github_get_file_contents",
            description="Read repository contents.",
            annotations={"readOnlyHint": True},
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )
    )
    state["value"] = ReadinessState.READY

    operation = runtime.operation("github_get_file_contents")
    assert operation.name == "github_get_file_contents"
    assert operation.effects == (
        OperationEffect.EXTERNAL,
        OperationEffect.READ_ONLY,
    )
    assert operation.input_schema == {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    assert runtime.readiness_for(operation).state is ReadinessState.READY
    assert "repository.remote_read_write" in runtime.available_capabilities


def test_runtime_long_tail_tools_remain_discoverable_not_direct() -> None:
    state = {"value": ReadinessState.READY}
    tools = [
        SimpleNamespace(
            name="github_get_file_contents",
            description="Read repository contents.",
            annotations={"readOnlyHint": True},
        )
    ]
    runtime = CapabilityRuntimeState.build(
        CapabilityCatalogue((_provider_contribution(state),), ()),
        load_capability_settings(),
        runtime_tools_source=lambda: tuple(tools),
        provider_namespaces={"github-mcp": "github"},
    )

    plan = ExposurePlanner(runtime).plan()

    assert "github_get_file_contents" in plan.discoverable_operations
    assert "github_get_file_contents" not in plan.direct_operations
