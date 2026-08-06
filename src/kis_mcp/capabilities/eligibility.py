from __future__ import annotations

from dataclasses import dataclass

from .contracts import OperationDescriptor, OperationEffect, ReadinessSnapshot, ReadinessState


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    eligible: bool
    reasons: tuple[str, ...]


def evaluate_eligibility(
    operation: OperationDescriptor,
    *,
    readiness: ReadinessSnapshot,
    available_capabilities: set[str] | frozenset[str],
    requested_effects: set[OperationEffect] | frozenset[OperationEffect],
    credentials_available: set[str] | frozenset[str],
) -> EligibilityDecision:
    blockers: list[str] = []
    if not operation.enabled:
        blockers.append("operation disabled")

    if readiness.state in {
        ReadinessState.UNAVAILABLE,
        ReadinessState.DISABLED,
        ReadinessState.BUILD_FAILED,
        ReadinessState.MOUNT_FAILED,
    }:
        blockers.append(f"runtime state {readiness.state.value}")
    elif (
        readiness.state is ReadinessState.AUTHENTICATION_REQUIRED
        and not operation.authentication_preflight
    ):
        blockers.append("runtime state authentication_required")

    for requirement in operation.dependencies:
        if not requirement.optional and requirement.capability_id not in available_capabilities:
            blockers.append(f"missing dependency {requirement.capability_id}")

    for credential in operation.credentials:
        if credential not in credentials_available:
            blockers.append(f"missing credential {credential}")

    if requested_effects and not set(operation.effects).issubset(requested_effects):
        blockers.append("requested effects are incompatible")

    return EligibilityDecision(eligible=not blockers, reasons=tuple(blockers))


__all__ = ["EligibilityDecision", "evaluate_eligibility"]
