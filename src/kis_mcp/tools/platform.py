from __future__ import annotations

from pathlib import Path

from ..capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationDescriptor,
    ReadinessSnapshot,
    ReadinessState,
)
from ..capabilities.normalization import default_quality, normalize_effects
from .contracts import ToolDescriptor, ToolState
from .everything import EverythingToolSettings, everything_tool_descriptor
from .fetch import FetchToolSettings, fetch_tool_descriptor
from .mcp_spec import McpSpecSettings, mcp_spec_tool_descriptor
from .registry import ToolRegistry


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_platform_tool_registry(repository_root: Path | None = None) -> ToolRegistry:
    root = (repository_root or _repository_root()).resolve()
    registry = ToolRegistry()
    registry.register(
        everything_tool_descriptor(
            EverythingToolSettings.load(root / "settings" / "tools" / "everything.tool.json")
        )
    )
    registry.register(
        fetch_tool_descriptor(
            FetchToolSettings.load(root / "settings" / "tools" / "fetch.tool.json")
        )
    )
    registry.register(
        mcp_spec_tool_descriptor(
            McpSpecSettings.load(root / "settings" / "tools" / "mcp-spec.tool.json")
        )
    )
    return registry


def _readiness(descriptor: ToolDescriptor) -> ReadinessSnapshot:
    readiness = descriptor.readiness_probe()
    state = {
        ToolState.READY: ReadinessState.READY,
        ToolState.DEGRADED: ReadinessState.DEGRADED,
        ToolState.DISABLED: ReadinessState.DISABLED,
        ToolState.UNAVAILABLE: ReadinessState.UNAVAILABLE,
    }[readiness.state]
    return ReadinessSnapshot(
        contribution_id=f"tool.{descriptor.tool_id}",
        state=state,
        summary=readiness.summary,
        details=readiness.details,
    )


def tool_capability_contributions(
    registry: ToolRegistry,
) -> tuple[CapabilityContribution, ...]:
    contributions: list[CapabilityContribution] = []
    for descriptor in registry.list():
        operations: list[OperationDescriptor] = []
        all_effects: list[str] = []
        for capability in descriptor.capabilities:
            all_effects.extend(capability.effects)
            for operation_name in capability.operation_names:
                effects = normalize_effects(capability.effects)
                operations.append(
                    OperationDescriptor(
                        operation_id=f"tool.{descriptor.tool_id}.{operation_name}",
                        name=operation_name,
                        description=capability.description,
                        capabilities=(capability.capability_id,),
                        effects=effects,
                        dependencies=(),
                        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=55),
                        quality=default_quality(context_cost=45, workflow_integration=55),
                        enabled=descriptor.enabled,
                    )
                )
        effects = normalize_effects(all_effects)
        contributions.append(
            CapabilityContribution(
                contribution_id=f"tool.{descriptor.tool_id}",
                domain=CapabilityDomain.TOOL,
                category=descriptor.tool_kind.value.replace("_", "-"),
                capabilities=tuple(item.capability_id for item in descriptor.capabilities),
                operations=tuple(operations),
                dependencies=(),
                effects=effects,
                readiness_probe=lambda descriptor=descriptor: _readiness(descriptor),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=50),
                quality=default_quality(context_cost=40, workflow_integration=55),
            )
        )
    return tuple(contributions)


__all__ = ["build_platform_tool_registry", "tool_capability_contributions"]
