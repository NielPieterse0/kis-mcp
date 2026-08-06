from __future__ import annotations

import re
from typing import Any

from fastmcp import FastMCP

from .eligibility import evaluate_eligibility
from .execution import CapabilityExecutionRouter
from .runtime import CapabilityRuntimeState

_TOKEN = re.compile(r"[a-z0-9]+")


def _matches(query: str, values: tuple[str, ...]) -> bool:
    terms = set(_TOKEN.findall(query.casefold()))
    haystack = set(_TOKEN.findall(" ".join(values).casefold()))
    return bool(terms and terms.intersection(haystack))


def register_capability_tools(server: FastMCP, runtime: CapabilityRuntimeState) -> None:
    router = CapabilityExecutionRouter(server, runtime)

    @server.tool(name="search_capabilities")
    def search_capabilities(query: str, limit: int = 20) -> dict[str, Any]:
        bounded = max(1, min(limit, 100))
        operations: list[dict[str, Any]] = []
        for operation in runtime.catalogue.operations:
            contribution = runtime.catalogue.contribution_for(operation)
            if not _matches(
                query,
                (operation.name, operation.description, contribution.category, *operation.capabilities),
            ):
                continue
            readiness = runtime.readiness_for(operation)
            decision = evaluate_eligibility(
                operation,
                readiness=readiness,
                available_capabilities=runtime.available_capabilities,
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
                    "capabilities": list(operation.capabilities),
                    "effects": [item.value for item in operation.effects],
                    "readiness": readiness.state.value,
                    "eligible": decision.eligible,
                    "eligibility_reasons": list(decision.reasons),
                }
            )
        return {
            "schema_version": 1,
            "query": query,
            "operations": operations[:bounded],
            "truncated": len(operations) > bounded,
        }

    @server.tool(name="describe_capability")
    def describe_capability(capability_id: str) -> dict[str, Any]:
        contributions = [
            item.to_json_dict()
            for item in runtime.catalogue.contributions
            if item.contribution_id == capability_id or capability_id in item.capabilities
        ]
        operations = [
            item.to_json_dict()
            for item in runtime.catalogue.operations
            if item.operation_id == capability_id
            or item.name == capability_id
            or capability_id in item.capabilities
        ]
        workflows = [
            item.to_json_dict()
            for item in runtime.catalogue.workflows
            if item.workflow_id == capability_id or capability_id in item.capabilities
        ]
        return {
            "schema_version": 1,
            "capability_id": capability_id,
            "contributions": contributions,
            "operations": operations,
            "workflows": workflows,
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
