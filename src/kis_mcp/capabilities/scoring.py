from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from .contracts import OperationDescriptor, QualityMetadata, ReadinessSnapshot, ReadinessState
from .settings import CapabilitySettings

_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: int
    reasons: tuple[str, ...]
    components: Mapping[str, int]


def _weighted(values: Mapping[str, int], weights: Mapping[str, int]) -> int:
    return round(sum(values[key] * weights[key] for key in weights) / 100)


def intrinsic_quality_score(quality: QualityMetadata, settings: CapabilitySettings) -> int:
    values = {
        "schema_precision": quality.schema_precision,
        "description_clarity": quality.description_clarity,
        "effect_accuracy": quality.effect_accuracy,
        "bounded_output": quality.bounded_output,
        "reversibility": quality.reversibility,
        "reliability": quality.reliability,
        "workflow_integration": quality.workflow_integration,
        "context_cost": 100 - quality.context_cost,
    }
    return _weighted(values, settings.quality_weights)


def _intent_score(
    operation: OperationDescriptor,
    query: str,
    requested_capabilities: frozenset[str],
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    operation_capabilities = set(operation.capabilities)
    if requested_capabilities and requested_capabilities.issubset(operation_capabilities):
        reasons.append("exact capability match")
        return 100, reasons
    query_tokens = set(_TOKEN.findall(query.casefold()))
    haystack = " ".join((operation.name, operation.description, *operation.capabilities, *operation.tags))
    target_tokens = set(_TOKEN.findall(haystack.casefold()))
    if not query_tokens:
        return 0, reasons
    overlap = len(query_tokens & target_tokens)
    score = min(100, round(100 * overlap / max(1, min(len(query_tokens), 6))))
    if overlap:
        reasons.append("task terms match operation metadata")
    return score, reasons


def suitability_score(
    operation: OperationDescriptor,
    *,
    settings: CapabilitySettings,
    query: str,
    requested_capabilities: frozenset[str],
    readiness: ReadinessSnapshot,
    workflow_coverage: int,
    prerequisites_satisfied: bool,
) -> ScoreResult:
    intent, reasons = _intent_score(operation, query, requested_capabilities)
    readiness_score = {
        ReadinessState.READY: 100,
        ReadinessState.DEGRADED: max(0, 100 - settings.degraded_penalty),
        ReadinessState.AUTHENTICATION_REQUIRED: 25,
        ReadinessState.UNAVAILABLE: 0,
        ReadinessState.DISABLED: 0,
        ReadinessState.BUILD_FAILED: 0,
        ReadinessState.MOUNT_FAILED: 0,
    }[readiness.state]
    if readiness.state is ReadinessState.READY:
        reasons.append("runtime ready")
    elif readiness.state is ReadinessState.DEGRADED:
        reasons.append("runtime degraded")
    if prerequisites_satisfied:
        reasons.append("prerequisites satisfied")
    if operation.approval_required:
        reasons.append("approval remains required")

    components = {
        "intent_match": intent,
        "workflow_coverage": max(0, min(100, workflow_coverage)),
        "runtime_readiness": readiness_score,
        "prerequisite_satisfaction": 100 if prerequisites_satisfied else 0,
        "safety_reversibility": operation.quality.reversibility,
        "observed_reliability": operation.quality.reliability,
        "user_friction": 100 - operation.friction,
        "context_cost": 100 - operation.quality.context_cost,
    }
    return ScoreResult(
        score=_weighted(components, settings.suitability_weights),
        reasons=tuple(dict.fromkeys(reasons)),
        components=components,
    )


__all__ = ["ScoreResult", "intrinsic_quality_score", "suitability_score"]
