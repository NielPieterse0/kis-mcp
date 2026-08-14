from __future__ import annotations

import json
from copy import deepcopy
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult

from .contracts import PolicyEvaluator, ProviderEffectResolver
from .line_endings import RepositoryLineEndingNormalizer
from .models import DecisionKind, PolicyDecision
from .quarantine import QuarantineError
from .runtime_observability import (
    RuntimeObservability,
    boundary_request_context,
    get_runtime_observability,
)


QuarantinePaths = Callable[[Sequence[str]], Sequence[Mapping[str, Any]]]
_BOUNDARY_METHODS = frozenset({"initialize", "tools/list", "tools/call"})


class BoundaryObservabilityMiddleware(Middleware):
    """Record bounded protocol-boundary evidence without payload content."""

    def __init__(self, observability: RuntimeObservability | None = None) -> None:
        self.observability = observability or get_runtime_observability()

    async def on_message(self, context: MiddlewareContext, call_next: Any) -> Any:
        method = str(context.method)
        if method not in _BOUNDARY_METHODS:
            return await call_next(context)
        tool_name = None
        if method == "tools/call":
            candidate = getattr(context.message, "name", None)
            tool_name = str(candidate) if candidate else None
        request_id = self.observability.reserve_boundary_request_id()
        with boundary_request_context(request_id):
            try:
                result = await call_next(context)
            except Exception as exc:
                self.observability.record_boundary_request(
                    method=method,
                    outcome="error",
                    tool_name=tool_name,
                    error_type=type(exc).__name__,
                    request_id=request_id,
                )
                raise
            self.observability.record_boundary_request(
                method=method,
                outcome="success",
                tool_name=tool_name,
                request_id=request_id,
            )
            return result


class ThreeRuleMiddleware(Middleware):
    """Apply only HR-001, HR-002, and HR-003 to concrete tool calls."""

    def __init__(
        self,
        *,
        resolver: ProviderEffectResolver,
        policy: PolicyEvaluator,
        quarantine_paths: QuarantinePaths,
        observability: RuntimeObservability | None = None,
        text_normalizer: RepositoryLineEndingNormalizer | None = None,
    ) -> None:
        self.resolver = resolver
        self.policy = policy
        self.quarantine_paths = quarantine_paths
        self.observability = observability or get_runtime_observability()
        self.text_normalizer = text_normalizer

    async def on_list_tools(
        self,
        context: MiddlewareContext,
        call_next: Any,
    ) -> Sequence[Any]:
        tools = await call_next(context)
        capabilities = self.resolver.capabilities
        hidden_tools = set(capabilities.network_only_tools)
        hidden_arguments = capabilities.unexposed_tool_arguments
        configuration_tool = capabilities.configuration_tool_name
        visible: list[Any] = []
        for tool in tools:
            name = str(getattr(tool, "name", ""))
            if name in hidden_tools:
                continue
            arguments = hidden_arguments.get(name.casefold())
            visible_tool = self._without_arguments(tool, arguments) if arguments else tool
            if configuration_tool and name.casefold() == configuration_tool.casefold():
                visible_tool = self._without_config_keys(
                    visible_tool, capabilities.unexposed_config_keys
                )
            visible.append(visible_tool)
        return visible

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        tool_name = str(context.message.name)
        arguments = dict(context.message.arguments or {})
        argument_keys = tuple(arguments)
        if self.text_normalizer is not None:
            normalized_arguments = self.text_normalizer.normalize(tool_name, arguments)
            if normalized_arguments != arguments:
                arguments = normalized_arguments
                context = context.copy(
                    message=context.message.model_copy(update={"arguments": arguments})
                )
        capabilities = self.resolver.capabilities
        configuration_tool = capabilities.configuration_tool_name
        if tool_name.casefold() in capabilities.network_only_tools:
            self._record_call(
                tool_name,
                argument_keys,
                decision="unsupported",
                outcome="rejected",
                code="UNSUPPORTED_PROVIDER_TOOL",
            )
            raise ToolError(
                "UNSUPPORTED_PROVIDER_TOOL: This provider-only network capability is "
                "not exposed through Work."
            )
        if configuration_tool and tool_name.casefold() == configuration_tool.casefold():
            key = str(arguments.get("key", ""))
            hidden_keys = {
                value.casefold() for value in capabilities.unexposed_config_keys
            }
            if key.casefold() in hidden_keys:
                self._record_call(
                    tool_name,
                    argument_keys,
                    decision="unsupported",
                    outcome="rejected",
                    code="PROVIDER_CONFIGURATION_INVARIANT",
                )
                raise ToolError(
                    "PROVIDER_CONFIGURATION_INVARIANT: Desktop Commander command and "
                    "directory restriction fields are gateway-managed and remain empty."
                )
        unsupported = capabilities.unexposed_tool_arguments.get(tool_name.casefold(), ())
        supplied = sorted(set(arguments).intersection(unsupported))
        if supplied:
            self._record_call(
                tool_name,
                argument_keys,
                decision="unsupported",
                outcome="rejected",
                code="UNSUPPORTED_PROVIDER_MODE",
            )
            raise ToolError(
                "UNSUPPORTED_PROVIDER_MODE: The following provider-only network "
                f"arguments are not exposed through Work: {', '.join(supplied)}."
            )
        effects = self.resolver.resolve(tool_name, arguments)
        decision = self.policy.evaluate(effects)

        if decision.kind is DecisionKind.ALLOW:
            try:
                result = await call_next(context)
            except Exception:
                self._record_call(
                    tool_name,
                    argument_keys,
                    decision=decision.kind.value,
                    outcome="error",
                    code=decision.code,
                )
                raise
            observer = getattr(self.resolver, "observe_success", None)
            if callable(observer):
                observer(tool_name, arguments, result)
            self._record_call(
                tool_name,
                argument_keys,
                decision=decision.kind.value,
                outcome="success",
                code=decision.code,
            )
            return result

        if decision.kind is DecisionKind.BLOCK:
            self._record_call(
                tool_name,
                argument_keys,
                decision=decision.kind.value,
                outcome="rejected",
                code=decision.code,
            )
            raise ToolError(self._error_message(decision))

        if decision.kind is DecisionKind.QUARANTINE:
            if tool_name.casefold() not in capabilities.direct_delete_tools:
                self._record_call(
                    tool_name,
                    argument_keys,
                    decision=decision.kind.value,
                    outcome="rejected",
                    code="HR-003_QUARANTINE_REQUIRED",
                )
                raise ToolError(
                    "HR-003_QUARANTINE_REQUIRED: The command explicitly requests "
                    "permanent deletion. Use a filesystem delete tool or "
                    "kis_quarantine_path so the target is moved to recoverable quarantine."
                )

            try:
                records = list(self.quarantine_paths(decision.paths))
            except QuarantineError as exc:
                self._record_call(
                    tool_name,
                    argument_keys,
                    decision=decision.kind.value,
                    outcome="error",
                    code="HR-003_QUARANTINE_FAILED",
                )
                raise ToolError(f"HR-003_QUARANTINE_FAILED: {exc}") from exc
            payload = {"quarantined": records}
            rendered = json.dumps(payload, indent=2, sort_keys=True)
            self._record_call(
                tool_name,
                argument_keys,
                decision=decision.kind.value,
                outcome="success",
                code=decision.code,
            )
            return ToolResult(
                content=rendered,
                structured_content={"result": rendered},
            )

        raise RuntimeError(f"Unexpected policy decision: {decision.kind}")

    def _record_call(
        self,
        tool_name: str,
        argument_keys: Sequence[str],
        *,
        decision: str,
        outcome: str,
        code: str | None,
    ) -> None:
        self.observability.record_tool_call(
            tool_name=tool_name,
            argument_keys=tuple(argument_keys),
            decision=decision,
            outcome=outcome,
            code=code,
        )

    @staticmethod
    def _without_arguments(tool: Any, hidden: Sequence[str]) -> Any:
        field = "parameters" if hasattr(tool, "parameters") else "inputSchema"
        schema = deepcopy(getattr(tool, field, {}))
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for name in hidden:
                properties.pop(name, None)
        required = schema.get("required")
        if isinstance(required, list):
            schema["required"] = [name for name in required if name not in hidden]
        if hasattr(tool, "model_copy"):
            return tool.model_copy(update={field: schema})
        setattr(tool, field, schema)
        return tool

    @staticmethod
    def _without_config_keys(tool: Any, hidden: Sequence[str]) -> Any:
        field = "parameters" if hasattr(tool, "parameters") else "inputSchema"
        schema = deepcopy(getattr(tool, field, {}))
        properties = schema.get("properties")
        if isinstance(properties, dict) and isinstance(properties.get("key"), dict):
            properties["key"]["not"] = {"enum": sorted(hidden)}
        updates = {
            field: schema,
            "description": "Set an exposed Desktop Commander runtime preference.",
        }
        if hasattr(tool, "model_copy"):
            return tool.model_copy(update=updates)
        setattr(tool, field, schema)
        setattr(tool, "description", updates["description"])
        return tool

    @staticmethod
    def _error_message(decision: PolicyDecision) -> str:
        path_detail = f" Paths: {', '.join(decision.paths)}." if decision.paths else ""
        return f"{decision.code}: {decision.message}{path_detail}"
