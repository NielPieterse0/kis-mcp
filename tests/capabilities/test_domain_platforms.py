from __future__ import annotations

from types import SimpleNamespace

from fastmcp import FastMCP

from kis_mcp.capabilities.contracts import OperationEffect, ReadinessState
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.discover.platform import discover_capability_contributions
from kis_mcp.providers.contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from kis_mcp.providers.platform import provider_capability_contributions
from kis_mcp.providers.registry import ProviderRegistry
from kis_mcp.providers.runtime import (
    ProviderMountResult,
    ProviderMountState,
    ProviderRuntimeComposition,
)
from kis_mcp.providers.service import ProviderService
from kis_mcp.skills.models import SkillCard
from kis_mcp.capabilities.surface import _runtime_effects, augment_with_runtime_surface
from kis_mcp.skills.platform import enrich_skill_card, skill_capability_contributions
from kis_mcp.tools.platform import build_platform_tool_registry, tool_capability_contributions
from kis_mcp.workflows.platform import workflow_descriptors


def provider_descriptor(provider_id: str, *, state: ProviderState = ProviderState.READY) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=provider_id,
        display_name=provider_id,
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=f"repository:{provider_id}",
        source_revision="1",
        capabilities=(
            ProviderCapability(
                capability_id=f"{provider_id}.operate",
                description=f"Operate {provider_id}.",
                effects=("external_network",),
                tool_names=(f"{provider_id}_status",),
            ),
        ),
        builder=lambda: FastMCP(provider_id),
        readiness_probe=lambda: ProviderReadiness(
            provider_id=provider_id,
            state=state,
            summary=state.value,
        ),
    )


def test_provider_contributions_use_instance_composition_state() -> None:
    service = ProviderService(ProviderRegistry((provider_descriptor("ready-provider"), provider_descriptor("failed-provider"))))
    composition = ProviderRuntimeComposition(
        results=(
            ProviderMountResult(
                provider_id="ready-provider",
                namespace="ready",
                registered=True,
                enabled=True,
                build_attempted=True,
                built=True,
                mounted=True,
                state=ProviderMountState.MOUNTED,
            ),
            ProviderMountResult(
                provider_id="failed-provider",
                namespace="failed",
                registered=True,
                enabled=True,
                build_attempted=True,
                built=False,
                mounted=False,
                state=ProviderMountState.BUILD_FAILED,
                error_type="RuntimeError",
            ),
        )
    )

    contributions = {item.contribution_id: item for item in provider_capability_contributions(service, composition)}

    assert contributions["provider.ready-provider"].readiness_probe().state is ReadinessState.READY
    failed = contributions["provider.failed-provider"].readiness_probe()
    assert failed.state is ReadinessState.BUILD_FAILED
    assert failed.details == {"error_type": "RuntimeError", "namespace": "failed"}


def test_tool_discover_and_workflow_platforms_emit_complete_metadata() -> None:
    tool_contributions = tool_capability_contributions(build_platform_tool_registry())
    discover_contributions = discover_capability_contributions()
    workflows = workflow_descriptors()

    assert {item.contribution_id for item in tool_contributions} == {
        "tool.mcp-everything",
        "tool.mcp-fetch",
        "tool.mcp-spec-plugin",
    }
    assert {operation.name for item in discover_contributions for operation in item.operations} >= {
        "inspect_project",
        "inspect_change",
    }
    workflow_ids = {item.workflow_id for item in workflows}
    assert "pull-request-safe-closeout" in workflow_ids
    assert "develop-isolated-change" in workflow_ids
    assert all(item.capabilities and item.required_steps and item.completion_criteria for item in workflows)


def test_all_registered_shared_skills_gain_capability_metadata() -> None:
    settings = load_capability_settings()
    cards = tuple(
        SkillCard(
            id=skill_id,
            summary=f"Summary for {skill_id}",
            category="uncategorized",
            capabilities=(),
            status="active",
        )
        for skill_id in settings.skill_metadata
    )

    enriched = tuple(enrich_skill_card(card, settings) for card in cards)
    contributions = skill_capability_contributions(enriched, settings)

    assert len(enriched) == 17
    assert all(card.category != "uncategorized" and card.capabilities for card in enriched)
    assert len(contributions) == 17
    assert all(item.domain.value == "skill" for item in contributions)



def test_runtime_effect_classification_distinguishes_reads_processes_and_external_mutations() -> None:
    read_tool = SimpleNamespace(annotations={"readOnlyHint": True})
    plain_tool = SimpleNamespace(annotations={})

    assert _runtime_effects("kis_list_quarantine", read_tool, owner_effects=()) == (
        OperationEffect.READ_ONLY,
    )
    assert _runtime_effects("read_process_output", read_tool, owner_effects=()) == (
        OperationEffect.READ_ONLY,
    )
    assert _runtime_effects("start_process", plain_tool, owner_effects=()) == (
        OperationEffect.PROCESS,
    )
    assert _runtime_effects(
        "github_create_issue",
        plain_tool,
        owner_effects=(OperationEffect.EXTERNAL,),
    ) == (OperationEffect.EXTERNAL,)
    assert _runtime_effects(
        "controlcenter_open_kis_control_center",
        read_tool,
        owner_effects=(OperationEffect.READ_ONLY,),
    ) == (OperationEffect.READ_ONLY,)


def test_declared_tool_operations_are_ineligible_until_registered_on_server() -> None:
    contributions = tool_capability_contributions(build_platform_tool_registry())

    normalized = augment_with_runtime_surface(contributions, (), {})
    mcp_spec = next(item for item in normalized if item.contribution_id == "tool.mcp-spec-plugin")

    assert mcp_spec.operations
    assert all(operation.enabled is False for operation in mcp_spec.operations)
    assert all(operation.exposure.mode.value == "status_only" for operation in mcp_spec.operations)
