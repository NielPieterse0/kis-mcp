from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .contracts import OperationEffect
from .eligibility import evaluate_eligibility
from .runtime import CapabilityRuntimeState


class CapabilityExecutionRouter:
    """Invoke registered operations through their original FastMCP contracts."""

    def __init__(self, server: FastMCP, runtime: CapabilityRuntimeState) -> None:
        self.server = server
        self.runtime = runtime

    async def execute_read(self, operation: str, arguments: Mapping[str, Any]) -> Any:
        return await self._execute(
            operation,
            arguments,
            required_effect=OperationEffect.READ_ONLY,
            allowed_effects=frozenset({OperationEffect.READ_ONLY}),
        )

    async def execute_change(self, operation: str, arguments: Mapping[str, Any]) -> Any:
        return await self._execute(
            operation,
            arguments,
            required_effect=None,
            allowed_effects=frozenset(
                {
                    OperationEffect.LOCAL_CHANGE,
                    OperationEffect.QUARANTINE,
                    OperationEffect.PROCESS,
                    OperationEffect.READ_ONLY,
                }
            ),
            at_least_one=frozenset(
                {
                    OperationEffect.LOCAL_CHANGE,
                    OperationEffect.QUARANTINE,
                    OperationEffect.PROCESS,
                }
            ),
        )

    async def execute_external(self, operation: str, arguments: Mapping[str, Any]) -> Any:
        return await self._execute(
            operation,
            arguments,
            required_effect=OperationEffect.EXTERNAL,
            allowed_effects=frozenset(OperationEffect),
        )

    async def _execute(
        self,
        operation_name: str,
        arguments: Mapping[str, Any],
        *,
        required_effect: OperationEffect | None,
        allowed_effects: frozenset[OperationEffect],
        at_least_one: frozenset[OperationEffect] = frozenset(),
    ) -> Any:
        if not isinstance(arguments, Mapping):
            raise ToolError("INVALID_ACTION_ARGUMENTS: arguments must be an object")
        try:
            operation = self.runtime.operation(operation_name)
        except KeyError as exc:
            raise ToolError(f"UNKNOWN_CAPABILITY_OPERATION: {operation_name}") from exc

        effects = frozenset(operation.effects)
        if required_effect is not None and required_effect not in effects:
            raise ToolError(
                f"EFFECT_MISMATCH: {operation.name} is not a {required_effect.value} action"
            )
        if at_least_one and not effects.intersection(at_least_one):
            raise ToolError(
                f"EFFECT_MISMATCH: {operation.name} is not a change action"
            )
        if not effects.issubset(allowed_effects):
            raise ToolError(
                f"EFFECT_MISMATCH: {operation.name} has incompatible effects"
            )
        if operation.approval_required:
            raise ToolError(
                "APPROVAL_REQUIRED: this registered operation requires its original "
                "approval workflow and cannot be dispatched generically"
            )

        decision = evaluate_eligibility(
            operation,
            readiness=self.runtime.readiness_for(operation),
            available_capabilities=self.runtime.available_capabilities,
            requested_effects=effects,
            credentials_available=frozenset(),
        )
        if not decision.eligible:
            raise ToolError(
                "OPERATION_INELIGIBLE: " + "; ".join(decision.reasons)
            )

        return await self.server.call_tool(
            operation.name,
            dict(arguments),
            run_middleware=True,
        )


__all__ = ["CapabilityExecutionRouter"]
