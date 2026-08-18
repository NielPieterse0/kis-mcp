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


def housekeeping_capability_contribution() -> CapabilityContribution:
    exposure = ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=88)
    read_quality = default_quality(
        context_cost=5,
        reversibility=100,
        reliability=95,
        workflow_integration=100,
    )
    apply_quality = default_quality(
        context_cost=10,
        reversibility=80,
        reliability=95,
        workflow_integration=100,
    )
    operations = (
        OperationDescriptor(
            operation_id="housekeeping-runtime.status",
            name="kis_housekeeping_status",
            description="Read unattended housekeeping host, cadence, receipt, and freshness status.",
            capabilities=("housekeeping.status.read",),
            effects=(OperationEffect.READ_ONLY,),
            dependencies=(),
            exposure=exposure,
            quality=read_quality,
        ),        OperationDescriptor(
            operation_id="housekeeping-runtime.receipt",
            name="kis_housekeeping_receipt",
            description="Read one persisted bounded housekeeping success or failure receipt.",
            capabilities=("housekeeping.receipt.read",),
            effects=(OperationEffect.READ_ONLY,),
            dependencies=(),
            exposure=exposure,
            quality=read_quality,
        ),
        OperationDescriptor(
            operation_id="housekeeping-runtime.apply-receipt",
            name="kis_housekeeping_apply_receipt",
            description="Apply one fresh unchanged housekeeping preview with deterministic idempotency.",
            capabilities=("housekeeping.receipt.apply",),
            effects=(OperationEffect.EXTERNAL,),
            dependencies=(),
            exposure=exposure,
            quality=apply_quality,
            approval_required=True,
        ),
    )
    contribution_id = "housekeeping-runtime"
    return CapabilityContribution(
        contribution_id=contribution_id,
        domain=CapabilityDomain.WORKFLOW,
        category="housekeeping",
        capabilities=tuple(
            capability
            for operation in operations
            for capability in operation.capabilities
        ),
        operations=operations,
        dependencies=(),
        effects=(OperationEffect.READ_ONLY, OperationEffect.EXTERNAL),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id=contribution_id,
            state=ReadinessState.READY,
            summary="Housekeeping runtime operations are registered.",
        ),
        exposure=exposure,
        quality=read_quality,
    )


__all__ = ["housekeeping_capability_contribution"]
