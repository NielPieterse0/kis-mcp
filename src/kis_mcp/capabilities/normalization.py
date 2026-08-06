from __future__ import annotations

from collections.abc import Iterable

from .contracts import OperationEffect, QualityMetadata


def normalize_effects(values: Iterable[str]) -> tuple[OperationEffect, ...]:
    effects: set[OperationEffect] = set()
    for raw in values:
        value = raw.casefold()
        if "delete" in value or "quarantine" in value:
            effects.add(OperationEffect.QUARANTINE)
        if "external" in value or "network" in value or "web" in value:
            effects.add(OperationEffect.EXTERNAL)
        if "process" in value or "command" in value or "execute" in value:
            effects.add(OperationEffect.PROCESS)
        if "write" in value or "change" in value or "mutate" in value or "manage" in value:
            effects.add(OperationEffect.LOCAL_CHANGE)
        if "read" in value or "inspect" in value or "search" in value or "status" in value or "research" in value:
            effects.add(OperationEffect.READ_ONLY)
    if not effects:
        effects.add(OperationEffect.READ_ONLY)
    return tuple(sorted(effects, key=lambda item: item.value))


def default_quality(
    *,
    context_cost: int = 30,
    reversibility: int = 85,
    reliability: int = 80,
    workflow_integration: int = 70,
) -> QualityMetadata:
    return QualityMetadata(
        schema_precision=85,
        description_clarity=85,
        effect_accuracy=90,
        bounded_output=80,
        reversibility=reversibility,
        reliability=reliability,
        workflow_integration=workflow_integration,
        context_cost=context_cost,
    )


__all__ = ["default_quality", "normalize_effects"]
