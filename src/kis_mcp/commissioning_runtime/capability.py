from __future__ import annotations

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
from kis_mcp.capabilities.normalization import default_quality


def post_merge_commissioning_capability_contribution() -> CapabilityContribution:
    exposure = ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=88)
    quality = default_quality(
        context_cost=5,
        reversibility=100,
        reliability=95,
        workflow_integration=100,
    )
    runner_quality = default_quality(
        context_cost=10,
        reversibility=80,
        reliability=95,
        workflow_integration=100,
    )
    operations = (
        OperationDescriptor(
            operation_id="post-merge-commissioning.status",
            name="kis_post_merge_commissioning_status",
            description="Read deterministic post-merge observer host and checkpoint status.",
            capabilities=("commissioning.observer.status.read",),
            effects=(OperationEffect.READ_ONLY,),
            dependencies=(),
            exposure=exposure,
            quality=quality,
        ),
        OperationDescriptor(
            operation_id="post-merge-commissioning.receipt",
            name="kis_post_merge_commissioning_receipt",
            description="Read one bounded deterministic post-merge observer receipt.",
            capabilities=("commissioning.observer.receipt.read",),
            effects=(OperationEffect.READ_ONLY,),
            dependencies=(),
            exposure=exposure,
            quality=quality,
        ),
        OperationDescriptor(
            operation_id="post-merge-commissioning.execution",
            name="kis_post_merge_commissioning_execution",
            description="Read one bounded commissioning execution state and proof receipt.",
            capabilities=("commissioning.execution.read",),
            effects=(OperationEffect.READ_ONLY,),
            dependencies=(),
            exposure=exposure,
            quality=quality,
        ),
        OperationDescriptor(
            operation_id="post-merge-commissioning.run",
            name="kis_post_merge_commissioning_run",
            description="Execute one claimed deterministic commissioning obligation with resumable evidence.",
            capabilities=("commissioning.execution.run",),
            effects=(OperationEffect.EXTERNAL,),
            dependencies=(),
            exposure=exposure,
            quality=runner_quality,
            approval_required=True,
        ),
    )
    contribution_id = "post-merge-commissioning-runtime"
    return CapabilityContribution(
        contribution_id=contribution_id,
        domain=CapabilityDomain.WORKFLOW,
        category="commissioning",
        capabilities=tuple(
            capability for operation in operations for capability in operation.capabilities
        ),
        operations=operations,
        dependencies=(),
        effects=(OperationEffect.READ_ONLY, OperationEffect.EXTERNAL),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id=contribution_id,
            state=ReadinessState.READY,
            summary="Post-merge commissioning diagnostics are registered.",
        ),
        exposure=exposure,
        quality=quality,
    )


__all__ = ["post_merge_commissioning_capability_contribution"]
