from __future__ import annotations

import pytest

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
)


def _quality() -> QualityMetadata:
    return QualityMetadata(
        schema_precision=90,
        description_clarity=80,
        effect_accuracy=100,
        bounded_output=85,
        reversibility=95,
        reliability=90,
        workflow_integration=75,
        context_cost=20,
    )


def _readiness() -> ReadinessSnapshot:
    return ReadinessSnapshot(
        contribution_id="discover-core",
        state=ReadinessState.READY,
        summary="ready",
    )


def test_capability_contribution_is_complete_and_deterministic() -> None:
    operation = OperationDescriptor(
        operation_id="discover.inspect-change",
        name="inspect_change",
        description="Inspect the current working tree.",
        capabilities=("git.change.inspect",),
        effects=(OperationEffect.READ_ONLY,),
        dependencies=(CapabilityRequirement("repository.git-read"),),
        exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=90),
        quality=_quality(),
    )
    contribution = CapabilityContribution(
        contribution_id="discover-core",
        domain=CapabilityDomain.DISCOVER,
        category="repository-analysis",
        capabilities=("git.change.inspect", "repository.git-read"),
        operations=(operation,),
        dependencies=(),
        effects=(OperationEffect.READ_ONLY,),
        readiness_probe=_readiness,
        exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=80),
        quality=_quality(),
    )

    payload = contribution.to_json_dict()

    assert payload["contribution_id"] == "discover-core"
    assert payload["capabilities"] == ["git.change.inspect", "repository.git-read"]
    assert payload["operations"][0]["name"] == "inspect_change"
    assert contribution.readiness_probe().state is ReadinessState.READY


def test_contribution_rejects_uncategorized_or_empty_capabilities() -> None:
    with pytest.raises(ValueError, match="category"):
        CapabilityContribution(
            contribution_id="bad",
            domain=CapabilityDomain.SKILL,
            category="uncategorized",
            capabilities=("architecture.assess",),
            operations=(),
            dependencies=(),
            effects=(OperationEffect.READ_ONLY,),
            readiness_probe=_readiness,
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
            quality=_quality(),
        )

    with pytest.raises(ValueError, match="capabilities"):
        CapabilityContribution(
            contribution_id="bad",
            domain=CapabilityDomain.SKILL,
            category="architecture",
            capabilities=(),
            operations=(),
            dependencies=(),
            effects=(OperationEffect.READ_ONLY,),
            readiness_probe=_readiness,
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
            quality=_quality(),
        )


def test_quality_metadata_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="schema_precision"):
        QualityMetadata(
            schema_precision=101,
            description_clarity=80,
            effect_accuracy=80,
            bounded_output=80,
            reversibility=80,
            reliability=80,
            workflow_integration=80,
            context_cost=20,
        )
