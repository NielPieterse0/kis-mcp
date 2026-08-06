from __future__ import annotations

from ..capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationDescriptor,
    OperationEffect,
    ReadinessSnapshot,
    ReadinessState,
)
from ..capabilities.normalization import default_quality


def _ready(contribution_id: str) -> ReadinessSnapshot:
    return ReadinessSnapshot(
        contribution_id=contribution_id,
        state=ReadinessState.READY,
        summary="Discover capability is available.",
    )


def discover_capability_contributions() -> tuple[CapabilityContribution, ...]:
    project_id = "discover.project"
    change_id = "discover.change"
    project_operation = OperationDescriptor(
        operation_id="discover.inspect-project",
        name="inspect_project",
        description="Return bounded deterministic local repository evidence.",
        capabilities=("repository.inspect", "repository.git-read"),
        effects=(OperationEffect.READ_ONLY,),
        dependencies=(),
        exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=95),
        quality=default_quality(context_cost=20, reliability=95, workflow_integration=95),
    )
    change_operation = OperationDescriptor(
        operation_id="discover.inspect-change",
        name="inspect_change",
        description="Inspect the current working tree and affected repository scopes.",
        capabilities=("git.change.inspect", "repository.git-read"),
        effects=(OperationEffect.READ_ONLY,),
        dependencies=(),
        exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=98),
        quality=default_quality(context_cost=15, reliability=95, workflow_integration=100),
    )
    return (
        CapabilityContribution(
            contribution_id=project_id,
            domain=CapabilityDomain.DISCOVER,
            category="repository-analysis",
            capabilities=("repository.inspect", "repository.git-read", "verification.discover"),
            operations=(project_operation,),
            dependencies=(),
            effects=(OperationEffect.READ_ONLY,),
            readiness_probe=lambda: _ready(project_id),
            exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=95),
            quality=default_quality(context_cost=20, reliability=95, workflow_integration=95),
        ),
        CapabilityContribution(
            contribution_id=change_id,
            domain=CapabilityDomain.DISCOVER,
            category="change-analysis",
            capabilities=(
                "git.change.inspect",
                "repository.git-read",
                "change.impact.analyze",
                "contract.change.inspect",
            ),
            operations=(change_operation,),
            dependencies=(),
            effects=(OperationEffect.READ_ONLY,),
            readiness_probe=lambda: _ready(change_id),
            exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=98),
            quality=default_quality(context_cost=15, reliability=95, workflow_integration=100),
        ),
    )


__all__ = ["discover_capability_contributions"]
