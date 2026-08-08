from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .contracts import OperationEffect
from .eligibility import evaluate_eligibility
from .runtime import CapabilityRuntimeState
from .settings import ResultBudgetSettings


def _json_chars(value: Any) -> int:
    return len(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    )


def _preview_value(value: Any, budget: ResultBudgetSettings, *, depth: int) -> Any:
    if depth <= 0:
        return {"truncated": True, "type": type(value).__name__}
    if isinstance(value, Mapping):
        entries = sorted(value.items(), key=lambda item: str(item[0]))
        preview = {
            str(key): _preview_value(item, budget, depth=depth - 1)
            for key, item in entries[: budget.preview_items]
        }
        omitted = len(entries) - min(len(entries), budget.preview_items)
        if omitted:
            preview["__omitted_fields__"] = omitted
        return preview
    if isinstance(value, (list, tuple)):
        selected = value[: budget.preview_items]
        return {
            "items": [
                _preview_value(item, budget, depth=depth - 1)
                for item in selected
            ],
            "omitted_items": len(value) - len(selected),
        }
    if isinstance(value, str) and len(value) > budget.preview_string_chars:
        omitted = len(value) - budget.preview_string_chars
        return value[: budget.preview_string_chars] + f"...<omitted {omitted} chars>"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _budget_result(operation: str, result: Any, budget: ResultBudgetSettings) -> Any:
    structured = getattr(result, "structured_content", None)
    if structured is None:
        return result
    original_chars = _json_chars(structured)
    if original_chars <= budget.max_chars:
        return result

    payload = {
        "truncated": True,
        "reason": "RESULT_BUDGET_EXCEEDED",
        "operation": operation,
        "original_chars": original_chars,
        "max_chars": budget.max_chars,
        "preview": _preview_value(structured, budget, depth=budget.preview_depth),
    }
    if _json_chars(payload) >= budget.max_chars:
        payload["preview"] = {
            "truncated": True,
            "type": type(structured).__name__,
        }
    return payload


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

        contribution = self.runtime.catalogue.contribution_for(operation)
        if contribution.contribution_id == "capability-control":
            raise ToolError(
                "DISPATCH_RECURSION_BLOCKED: capability control operations cannot "
                "be invoked through a generic dispatcher"
            )

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

        result = await self.server.call_tool(
            operation.name,
            dict(arguments),
            run_middleware=True,
        )
        return _budget_result(operation.name, result, self.runtime.settings.result_budget)


__all__ = ["CapabilityExecutionRouter"]
