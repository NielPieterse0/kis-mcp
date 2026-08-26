from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from .contracts import OperationDescriptor, OperationEffect
from .eligibility import evaluate_eligibility
from .execution import CapabilityExecutionRouter
from .result_resources import ResultResourceStore, register_result_resources
from .runtime import CapabilityRuntimeState

_TOKEN = re.compile(r"[a-z0-9]+")
_SEARCH_CAPABILITY_LIMIT = 8


def _terms(value: str) -> frozenset[str]:
    return frozenset(_TOKEN.findall(value.casefold()))


def _match_score(
    query: str,
    *,
    identities: Iterable[str] = (),
    capabilities: Iterable[str] = (),
    text: Iterable[str] = (),
) -> int:
    normalized_query = query.casefold().strip()
    if not normalized_query:
        return 0
    identity_values = tuple(value.casefold().strip() for value in identities if value)
    capability_values = tuple(value.casefold().strip() for value in capabilities if value)
    if normalized_query in identity_values:
        return 10_000
    if normalized_query in capability_values:
        return 9_000
    if any(normalized_query in value for value in identity_values):
        return 8_000

    query_terms = _terms(query)
    if not query_terms:
        return 0
    identity_terms = _terms(" ".join(identity_values))
    capability_terms = _terms(" ".join(capability_values))
    text_terms = _terms(" ".join(value for value in text if value))
    identity_overlap = len(query_terms.intersection(identity_terms))
    capability_overlap = len(query_terms.intersection(capability_terms))
    text_overlap = len(query_terms.intersection(text_terms))
    if not any((identity_overlap, capability_overlap, text_overlap)):
        return 0
    return 500 + (identity_overlap * 120) + (capability_overlap * 45) + (text_overlap * 15)


def _bounded_capabilities(query: str, capabilities: tuple[str, ...]) -> list[str]:
    query_terms = _terms(query)
    ranked = sorted(
        capabilities,
        key=lambda value: (
            -len(query_terms.intersection(_terms(value))),
            value,
        ),
    )
    return ranked[:_SEARCH_CAPABILITY_LIMIT]


def _execution_surface(operation: OperationDescriptor) -> str:
    effects = set(operation.effects)
    if OperationEffect.EXTERNAL in effects:
        return "execute_external_action"
    if effects.intersection(
        {
            OperationEffect.LOCAL_CHANGE,
            OperationEffect.QUARANTINE,
            OperationEffect.PROCESS,
        }
    ):
        return "execute_change_action"
    return "execute_read_action"


def register_capability_tools(
    server: FastMCP,
    runtime: CapabilityRuntimeState,
    *,
    state_root: Path | str | None = None,
    quarantine_expired: Callable[[str], Any] | None = None,
) -> None:
    result_store = (
        ResultResourceStore(
            Path(state_root),
            runtime.settings.result_budget,
            quarantine_expired=quarantine_expired,
        )
        if state_root is not None
        else None
    )
    if result_store is not None:
        register_result_resources(server, result_store)
    router = CapabilityExecutionRouter(server, runtime, result_store=result_store)

    @server.tool(name="search_capabilities")
    def search_capabilities(query: str, limit: int = 20) -> dict[str, Any]:
        bounded = max(1, min(limit, 100))
        catalogue = runtime.catalogue
        readiness_by_id = runtime.readiness
        available_capabilities = runtime.available_capabilities
        contributions: list[dict[str, Any]] = []
        operations: list[dict[str, Any]] = []
        workflows: list[dict[str, Any]] = []

        for contribution in catalogue.contributions:
            score = _match_score(
                query,
                identities=(contribution.contribution_id, contribution.category),
                capabilities=contribution.capabilities,
            )
            if score <= 0:
                continue
            readiness = readiness_by_id[contribution.contribution_id]
            contributions.append(
                {
                    "contribution_id": contribution.contribution_id,
                    "domain": contribution.domain.value,
                    "category": contribution.category,
                    "capabilities": _bounded_capabilities(query, contribution.capabilities),
                    "capability_count": len(contribution.capabilities),
                    "readiness": readiness.state.value,
                    "readiness_summary": readiness.summary,
                    "match_score": score,
                }
            )

        for operation in catalogue.operations:
            contribution = catalogue.contribution_for(operation)
            score = _match_score(
                query,
                identities=(operation.operation_id, operation.name),
                capabilities=operation.capabilities,
                text=(operation.description, contribution.category, contribution.domain.value),
            )
            if score <= 0:
                continue
            readiness = readiness_by_id[contribution.contribution_id]
            decision = evaluate_eligibility(
                operation,
                readiness=readiness,
                available_capabilities=available_capabilities,
                requested_effects=frozenset(),
                credentials_available=frozenset(),
            )
            operations.append(
                {
                    "operation_id": operation.operation_id,
                    "operation_name": operation.name,
                    "contribution_id": contribution.contribution_id,
                    "domain": contribution.domain.value,
                    "category": contribution.category,
                    "capabilities": _bounded_capabilities(query, operation.capabilities),
                    "capability_count": len(operation.capabilities),
                    "effects": [item.value for item in operation.effects],
                    "readiness": readiness.state.value,
                    "eligible": decision.eligible,
                    "eligibility_reasons": list(decision.reasons),
                    "match_score": score,
                }
            )

        for workflow in catalogue.workflows:
            score = _match_score(
                query,
                identities=(workflow.workflow_id, workflow.title),
                capabilities=workflow.capabilities,
                text=(workflow.description, *workflow.activation_terms),
            )
            if score <= 0:
                continue
            payload = workflow.to_json_dict()
            payload["match_score"] = score
            workflows.append(payload)

        contributions.sort(key=lambda item: (-item["match_score"], item["contribution_id"]))
        operations.sort(key=lambda item: (-item["match_score"], item["operation_id"]))
        workflows.sort(key=lambda item: (-item["match_score"], item["workflow_id"]))
        truncated = any(
            len(items) > bounded
            for items in (contributions, operations, workflows)
        )
        return {
            "schema_version": 1,
            "query": query,
            "contributions": contributions[:bounded],
            "operations": operations[:bounded],
            "workflows": workflows[:bounded],
            "truncated": truncated,
        }

    @server.tool(name="describe_capability")
    def describe_capability(capability_id: str) -> dict[str, Any]:
        catalogue = runtime.catalogue
        readiness_by_id = runtime.readiness
        available_capabilities = runtime.available_capabilities
        exact_contributions = [
            item for item in catalogue.contributions if item.contribution_id == capability_id
        ]
        exact_operations = [
            item
            for item in catalogue.operations
            if item.operation_id == capability_id or item.name == capability_id
        ]
        exact_workflows = [
            item for item in catalogue.workflows if item.workflow_id == capability_id
        ]

        if exact_contributions or exact_operations or exact_workflows:
            contribution_matches = exact_contributions
            operation_matches = exact_operations
            workflow_matches = exact_workflows
        else:
            operation_matches = [
                item for item in catalogue.operations if capability_id in item.capabilities
            ]
            workflow_matches = [
                item for item in catalogue.workflows if capability_id in item.capabilities
            ]
            contribution_matches = [] if (operation_matches or workflow_matches) else [
                item
                for item in catalogue.contributions
                if capability_id in item.capabilities
            ]

        operations: list[dict[str, Any]] = []
        for operation in operation_matches:
            contribution = catalogue.contribution_for(operation)
            readiness = readiness_by_id[contribution.contribution_id]
            decision = evaluate_eligibility(
                operation,
                readiness=readiness,
                available_capabilities=available_capabilities,
                requested_effects=frozenset(),
                credentials_available=frozenset(),
            )
            payload = operation.to_json_dict()
            payload.update(
                {
                    "contribution_id": contribution.contribution_id,
                    "domain": contribution.domain.value,
                    "category": contribution.category,
                    "readiness": readiness.state.value,
                    "readiness_summary": readiness.summary,
                    "eligible": decision.eligible,
                    "eligibility_reasons": list(decision.reasons),
                    "execution_surface": _execution_surface(operation),
                }
            )
            operations.append(payload)

        return {
            "schema_version": 1,
            "capability_id": capability_id,
            "contributions": [item.to_json_dict() for item in contribution_matches],
            "operations": operations,
            "workflows": [item.to_json_dict() for item in workflow_matches],
        }

    @server.tool(name="recommend_workflow")
    def recommend_workflow(task: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "task": task,
            "recommendations": [
                item.to_json_dict() for item in runtime.resolver.recommend_workflows(task)
            ],
        }

    @server.tool(name="execute_read_action")
    async def execute_read_action(operation: str, arguments: dict[str, Any]) -> Any:
        return await router.execute_read(operation, arguments)

    @server.tool(name="execute_change_action")
    async def execute_change_action(operation: str, arguments: dict[str, Any]) -> Any:
        return await router.execute_change(operation, arguments)

    @server.tool(name="execute_external_action")
    async def execute_external_action(operation: str, arguments: dict[str, Any]) -> Any:
        return await router.execute_external(operation, arguments)


__all__ = ["register_capability_tools"]
