from __future__ import annotations

from dataclasses import replace

import pytest

from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    CapabilityRequirement,
    ExposureMode,
    ExposurePolicy,
    OperationDescriptor,
    OperationEffect,
    QualityMetadata,
    ReadinessSnapshot,
    ReadinessState,
    WorkflowDescriptor,
)
from kis_mcp.capabilities.eligibility import evaluate_eligibility
from kis_mcp.capabilities.readiness import evaluate_readiness
from kis_mcp.capabilities.resolver import CapabilityResolver, TaskContext
from kis_mcp.capabilities.scoring import intrinsic_quality_score
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.workflows.platform import workflow_descriptors


def quality(**overrides: int) -> QualityMetadata:
    values = {
        "schema_precision": 90,
        "description_clarity": 90,
        "effect_accuracy": 90,
        "bounded_output": 90,
        "reversibility": 90,
        "reliability": 90,
        "workflow_integration": 90,
        "context_cost": 10,
    }
    values.update(overrides)
    return QualityMetadata(**values)


def operation(
    operation_id: str = "discover.inspect-change",
    name: str = "inspect_change",
    *,
    effects: tuple[OperationEffect, ...] = (OperationEffect.READ_ONLY,),
    dependencies: tuple[CapabilityRequirement, ...] = (),
    authentication_preflight: bool = False,
    approval_required: bool = False,
    mode: ExposureMode = ExposureMode.DIRECT,
) -> OperationDescriptor:
    return OperationDescriptor(
        operation_id=operation_id,
        name=name,
        description="Inspect the current repository change safely.",
        capabilities=("git.change.inspect",),
        effects=effects,
        dependencies=dependencies,
        exposure=ExposurePolicy(mode=mode, priority=90),
        quality=quality(),
        authentication_preflight=authentication_preflight,
        approval_required=approval_required,
    )


def contribution(
    *,
    contribution_id: str = "discover-core",
    op: OperationDescriptor | None = None,
    readiness: ReadinessState = ReadinessState.READY,
) -> CapabilityContribution:
    def probe() -> ReadinessSnapshot:
        return ReadinessSnapshot(contribution_id=contribution_id, state=readiness, summary=readiness.value)

    return CapabilityContribution(
        contribution_id=contribution_id,
        domain=CapabilityDomain.DISCOVER,
        category="repository-analysis",
        capabilities=("git.change.inspect", "repository.git-read"),
        operations=(op or operation(),),
        dependencies=(),
        effects=(OperationEffect.READ_ONLY,),
        readiness_probe=probe,
        exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=90),
        quality=quality(),
    )


def workflow() -> WorkflowDescriptor:
    return WorkflowDescriptor(
        workflow_id="pull-request-safe-closeout",
        title="Review and merge pull request safely",
        description="Inspect, verify, review, merge, and clean the isolated worktree.",
        capabilities=("git.change.inspect", "github.pull-request.merge", "validation.execute"),
        required_steps=("inspect_change", "run_verification", "github_merge_pull_request"),
        completion_criteria=("checks pass", "approved head is merged", "worktree is cleaned"),
        activation_terms=("review and merge pull request", "merge pr safely", "clean worktree"),
        effects=(OperationEffect.READ_ONLY, OperationEffect.LOCAL_CHANGE, OperationEffect.EXTERNAL),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=95),
    )


def test_catalogue_rejects_duplicate_operation_names() -> None:
    first = contribution()
    second = contribution(
        contribution_id="other-discover",
        op=operation(operation_id="other.inspect", name="inspect_change"),
    )

    with pytest.raises(ValueError, match="duplicate operation name"):
        CapabilityCatalogue((first, second), ())


def test_readiness_probe_failure_is_contained_as_unavailable() -> None:
    base = contribution()

    def broken_probe() -> ReadinessSnapshot:
        raise RuntimeError("secret detail")

    broken = replace(base, readiness_probe=broken_probe)
    result = evaluate_readiness((broken,))["discover-core"]

    assert result.state is ReadinessState.UNAVAILABLE
    assert result.details == {"error_type": "RuntimeError"}
    assert "secret detail" not in result.summary


def test_eligibility_hard_filters_before_scoring() -> None:
    op = operation(dependencies=(CapabilityRequirement("validation.execute"),))
    unavailable = ReadinessSnapshot(
        contribution_id="discover-core",
        state=ReadinessState.UNAVAILABLE,
        summary="not ready",
    )

    decision = evaluate_eligibility(
        op,
        readiness=unavailable,
        available_capabilities={"git.change.inspect"},
        requested_effects={OperationEffect.READ_ONLY},
        credentials_available=set(),
    )

    assert decision.eligible is False
    assert "runtime state unavailable" in decision.reasons
    assert "missing dependency validation.execute" in decision.reasons


def test_authentication_required_only_allows_preflight_operations() -> None:
    readiness = ReadinessSnapshot(
        contribution_id="github",
        state=ReadinessState.AUTHENTICATION_REQUIRED,
        summary="sign in",
    )
    normal = evaluate_eligibility(
        operation(), readiness=readiness, available_capabilities=set(), requested_effects=set(), credentials_available=set()
    )
    preflight = evaluate_eligibility(
        operation(authentication_preflight=True), readiness=readiness, available_capabilities=set(), requested_effects=set(), credentials_available=set()
    )

    assert normal.eligible is False
    assert preflight.eligible is True


def test_scoring_is_deterministic_and_explainable_after_filtering() -> None:
    settings = load_capability_settings()
    catalogue = CapabilityCatalogue((contribution(),), (workflow(),))
    resolver = CapabilityResolver(catalogue, settings)

    recommendations = resolver.recommend_operations(
        TaskContext(
            query="inspect the current change for a pull request review",
            requested_capabilities=("git.change.inspect",),
            requested_effects=(OperationEffect.READ_ONLY,),
        )
    )

    assert [item.operation_name for item in recommendations] == ["inspect_change"]
    assert 0 <= recommendations[0].score <= 100
    assert "exact capability match" in recommendations[0].reasons
    assert "runtime ready" in recommendations[0].reasons
    assert intrinsic_quality_score(operation().quality, settings) == 90


def test_safe_closeout_uses_runtime_verification_capability() -> None:
    descriptor = next(
        item for item in workflow_descriptors() if item.workflow_id == "pull-request-safe-closeout"
    )

    assert "verification.execute" in descriptor.capabilities
    assert "validation.execute" not in descriptor.capabilities


def test_workflow_recommendation_excludes_ineligible_candidates() -> None:
    resolver = CapabilityResolver(
        CapabilityCatalogue((contribution(),), (workflow(),)),
        load_capability_settings(),
    )

    result = resolver.recommend_workflows(
        "review and merge this pull request safely and clean the worktree"
    )

    assert result == ()


def test_workflow_recommendation_returns_candidate_when_all_capabilities_exist() -> None:
    def ready_probe(contribution_id: str):
        return lambda: ReadinessSnapshot(
            contribution_id=contribution_id,
            state=ReadinessState.READY,
            summary="ready",
        )

    github = CapabilityContribution(
        contribution_id="github-workflow-capabilities",
        domain=CapabilityDomain.PROVIDER,
        category="connector",
        capabilities=("github.pull-request.merge",),
        operations=(),
        dependencies=(),
        effects=(OperationEffect.EXTERNAL,),
        readiness_probe=ready_probe("github-workflow-capabilities"),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=80),
        quality=quality(),
    )
    validation = CapabilityContribution(
        contribution_id="validation-capabilities",
        domain=CapabilityDomain.TOOL,
        category="validation",
        capabilities=("validation.execute",),
        operations=(),
        dependencies=(),
        effects=(OperationEffect.PROCESS,),
        readiness_probe=ready_probe("validation-capabilities"),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=80),
        quality=quality(),
    )
    resolver = CapabilityResolver(
        CapabilityCatalogue((contribution(), github, validation), (workflow(),)),
        load_capability_settings(),
    )

    result = resolver.recommend_workflows(
        "review and merge this pull request safely and clean the worktree"
    )

    assert len(result) == 1
    assert result[0].workflow_id == "pull-request-safe-closeout"
    assert result[0].required_steps == (
        "inspect_change",
        "run_verification",
        "github_merge_pull_request",
    )
    assert result[0].eligible is True
    assert result[0].missing_capabilities == ()
    assert "activation term match" in result[0].reasons
    assert "all capability prerequisites available" in result[0].reasons
