from __future__ import annotations

import re
from dataclasses import dataclass

from .catalogue import CapabilityCatalogue
from .contracts import OperationEffect, ReadinessSnapshot, ReadinessState, WorkflowDescriptor
from .eligibility import evaluate_eligibility
from .readiness import evaluate_readiness
from .scoring import intrinsic_quality_score, suitability_score
from .settings import CapabilitySettings

_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class TaskContext:
    query: str
    requested_capabilities: tuple[str, ...] = ()
    requested_effects: tuple[OperationEffect, ...] = ()
    explicit_operation: str | None = None
    credentials_available: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationRecommendation:
    operation_id: str
    operation_name: str
    score: int
    intrinsic_quality: int
    reasons: tuple[str, ...]
    components: dict[str, int]

    def to_json_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "tool": self.operation_name,
            "score": self.score,
            "intrinsic_quality": self.intrinsic_quality,
            "reasons": list(self.reasons),
            "components": dict(self.components),
        }


@dataclass(frozen=True, slots=True)
class WorkflowRecommendation:
    workflow_id: str
    title: str
    score: int
    required_steps: tuple[str, ...]
    eligible: bool
    missing_capabilities: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_json_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "title": self.title,
            "score": self.score,
            "required_steps": list(self.required_steps),
            "eligible": self.eligible,
            "missing_capabilities": list(self.missing_capabilities),
            "reasons": list(self.reasons),
        }


class CapabilityResolver:
    def __init__(self, catalogue: CapabilityCatalogue, settings: CapabilitySettings) -> None:
        self.catalogue = catalogue
        self.settings = settings
        self.readiness = evaluate_readiness(catalogue.contributions)

    def _available_capabilities(self) -> frozenset[str]:
        return frozenset(
            capability
            for contribution in self.catalogue.contributions
            if self.readiness[contribution.contribution_id].operational
            and (
                not contribution.operations
                or any(operation.enabled for operation in contribution.operations)
            )
            for capability in contribution.capabilities
        )

    def recommend_operations(self, context: TaskContext) -> tuple[OperationRecommendation, ...]:
        available = self._available_capabilities()
        requested_capabilities = frozenset(context.requested_capabilities)
        requested_effects = frozenset(context.requested_effects)
        credentials = frozenset(context.credentials_available)
        recommendations: list[OperationRecommendation] = []
        for operation in self.catalogue.operations:
            contribution = self.catalogue.contribution_for(operation)
            readiness = self.readiness[contribution.contribution_id]
            decision = evaluate_eligibility(
                operation,
                readiness=readiness,
                available_capabilities=available,
                requested_effects=requested_effects,
                credentials_available=credentials,
            )
            if not decision.eligible:
                continue
            workflow_coverage = max(
                (
                    round(100 * len(set(operation.capabilities) & set(workflow.capabilities)) / len(workflow.capabilities))
                    for workflow in self.catalogue.workflows
                    if workflow.capabilities
                ),
                default=0,
            )
            result = suitability_score(
                operation,
                settings=self.settings,
                query=context.query,
                requested_capabilities=requested_capabilities,
                readiness=readiness,
                workflow_coverage=workflow_coverage,
                prerequisites_satisfied=all(
                    requirement.optional or requirement.capability_id in available
                    for requirement in operation.dependencies
                ),
            )
            recommendations.append(
                OperationRecommendation(
                    operation_id=operation.operation_id,
                    operation_name=operation.name,
                    score=result.score,
                    intrinsic_quality=intrinsic_quality_score(operation.quality, self.settings),
                    reasons=result.reasons,
                    components=dict(result.components),
                )
            )
        recommendations.sort(key=lambda item: (-item.score, item.operation_name))
        if context.explicit_operation is not None:
            recommendations.sort(
                key=lambda item: (
                    item.operation_name != context.explicit_operation
                    and item.operation_id != context.explicit_operation,
                    -item.score,
                    item.operation_name,
                )
            )
        return tuple(recommendations)

    def recommend_workflows(self, query: str) -> tuple[WorkflowRecommendation, ...]:
        query_tokens = set(_TOKEN.findall(query.casefold()))
        available = self._available_capabilities()
        recommendations: list[WorkflowRecommendation] = []
        for workflow in self.catalogue.workflows:
            best = 0
            for term in workflow.activation_terms:
                term_tokens = set(_TOKEN.findall(term))
                if not term_tokens:
                    continue
                overlap = len(term_tokens & query_tokens)
                best = max(best, round(100 * overlap / len(term_tokens)))
            if best < 50:
                continue
            missing = tuple(
                sorted(
                    capability
                    for capability in workflow.capabilities
                    if capability not in available
                )
            )
            coverage = round(
                100
                * (len(workflow.capabilities) - len(missing))
                / len(workflow.capabilities)
            )
            score = round(0.75 * best + 0.25 * coverage)
            reasons = ["activation term match"]
            if missing:
                reasons.append(
                    f"{len(missing)} capability prerequisites unavailable"
                )
            else:
                reasons.append("all capability prerequisites available")
            recommendations.append(
                WorkflowRecommendation(
                    workflow_id=workflow.workflow_id,
                    title=workflow.title,
                    score=score,
                    required_steps=workflow.required_steps,
                    eligible=not missing,
                    missing_capabilities=missing,
                    reasons=tuple(reasons),
                )
            )
        recommendations.sort(key=lambda item: (-item.score, item.workflow_id))
        return tuple(recommendations)



__all__ = [
    "CapabilityResolver",
    "OperationRecommendation",
    "TaskContext",
    "WorkflowRecommendation",
]
