from __future__ import annotations

from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationDescriptor,
    OperationEffect,
    QualityMetadata,
    ReadinessSnapshot,
    ReadinessState,
    WorkflowDescriptor,
)
from kis_mcp.capabilities.resolver import CapabilityResolver
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.workflows.platform import workflow_descriptors


def _quality() -> QualityMetadata:
    return QualityMetadata(
        schema_precision=90,
        description_clarity=90,
        effect_accuracy=90,
        bounded_output=90,
        reversibility=90,
        reliability=90,
        workflow_integration=90,
        context_cost=10,
    )


def _workflow() -> WorkflowDescriptor:
    return WorkflowDescriptor(
        workflow_id="verify-current-change",
        title="Verify current change",
        description="Analyze the current repository change and execute affected verification evidence.",
        capabilities=("change.impact.analyze", "git.change.inspect", "verification.execute"),
        required_steps=("inspect_change", "analyze_change", "run_verification"),
        executable_steps=("inspect_change", "analyze_change", "run_verification"),
        completion_criteria=("verification evidence is complete",),
        activation_terms=("verify current change", "run affected verification"),
        effects=(OperationEffect.READ_ONLY, OperationEffect.PROCESS),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=90),
    )


def _contribution(*, include_verification: bool) -> CapabilityContribution:
    names = ["inspect_change", "analyze_change"]
    if include_verification:
        names.append("run_verification")
    operations = tuple(
        OperationDescriptor(
            operation_id=f"test.{name.replace('_', '-')}",
            name=name,
            description=f"Run {name}.",
            capabilities=(f"operation.{name}",),
            effects=(OperationEffect.READ_ONLY,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=80),
            quality=_quality(),
        )
        for name in names
    )
    contribution_id = "test.workflow-runtime"
    return CapabilityContribution(
        contribution_id=contribution_id,
        domain=CapabilityDomain.TOOL,
        category="verification",
        capabilities=("change.impact.analyze", "git.change.inspect", "verification.execute"),
        operations=operations,
        dependencies=(),
        effects=(OperationEffect.READ_ONLY,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id=contribution_id,
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=80),
        quality=_quality(),
    )


def test_shared_platform_includes_verification_workflows_with_executable_steps() -> None:
    workflows = {item.workflow_id: item for item in workflow_descriptors()}

    assert workflows["verify-current-change"].executable_steps == (
        "inspect_change",
        "analyze_change",
        "run_verification",
    )
    assert workflows["triage-exact-head-ci"].executable_steps == (
        "inspect_change",
        "github_actions_list",
        "github_actions_get",
    )


def test_workflow_recommendation_rejects_unresolved_executable_step() -> None:
    resolver = CapabilityResolver(
        CapabilityCatalogue((_contribution(include_verification=False),), (_workflow(),)),
        load_capability_settings(),
    )

    result = resolver.recommend_workflows("please verify the current change and run verification")

    assert result == ()


def test_workflow_recommendation_delegates_to_weighted_matcher() -> None:
    resolver = CapabilityResolver(
        CapabilityCatalogue((_contribution(include_verification=True),), (_workflow(),)),
        load_capability_settings(),
    )

    result = resolver.recommend_workflows("please verify the current change and run verification")

    assert [item.workflow_id for item in result] == ["verify-current-change"]
    assert result[0].score >= 70
    assert "workflow id/title match" in result[0].reasons
    assert "activation term match" in result[0].reasons
    assert "capability match" in result[0].reasons
    assert "all executable steps resolve" in result[0].reasons


def test_exact_head_ci_triage_is_recommended_for_realistic_prompt() -> None:
    workflow = next(
        item for item in workflow_descriptors() if item.workflow_id == "triage-exact-head-ci"
    )
    names = ("inspect_change", "github_actions_list", "github_actions_get")
    operations = tuple(
        OperationDescriptor(
            operation_id=f"test.{name.replace('_', '-')}",
            name=name,
            description=f"Run {name}.",
            capabilities=(f"operation.{name}",),
            effects=(OperationEffect.READ_ONLY,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=80),
            quality=_quality(),
        )
        for name in names
    )
    contribution_id = "test.ci-triage-runtime"
    contribution = CapabilityContribution(
        contribution_id=contribution_id,
        domain=CapabilityDomain.TOOL,
        category="ci-triage",
        capabilities=("git.change.inspect", "github.actions.read"),
        operations=operations,
        dependencies=(),
        effects=(OperationEffect.READ_ONLY,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id=contribution_id,
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=80),
        quality=_quality(),
    )
    resolver = CapabilityResolver(
        CapabilityCatalogue((contribution,), (workflow,)),
        load_capability_settings(),
    )

    result = resolver.recommend_workflows(
        "triage the exact-head CI failure and inspect the GitHub Actions workflow run"
    )

    assert [item.workflow_id for item in result] == ["triage-exact-head-ci"]
    assert result[0].score >= 70
    assert "activation term match" in result[0].reasons
    assert "all executable steps resolve" in result[0].reasons
