from __future__ import annotations

import json
from copy import deepcopy
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult

from .contracts import PolicyEvaluator, ProviderEffectResolver
from .models import DecisionKind, PolicyDecision
from .quarantine import QuarantineError


QuarantinePaths = Callable[[Sequence[str]], Sequence[Mapping[str, Any]]]


class ThreeRuleMiddleware(Middleware):
    """Apply only HR-001, HR-002, and HR-003 to concrete tool calls."""

    def __init__(
        self,
        *,
        resolver: ProviderEffectResolver,
        policy: PolicyEvaluator,
        quarantine_paths: QuarantinePaths,
    ) -> None:
        self.resolver = resolver
        self.policy = policy
        self.quarantine_paths = quarantine_paths

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
        capabilities = self.resolver.capabilities
        configuration_tool = capabilities.configuration_tool_name
        if tool_name.casefold() in capabilities.network_only_tools:
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
                raise ToolError(
                    "PROVIDER_CONFIGURATION_INVARIANT: Desktop Commander command and "
                    "directory restriction fields are gateway-managed and remain empty."
                )
        unsupported = capabilities.unexposed_tool_arguments.get(tool_name.casefold(), ())
        supplied = sorted(set(arguments).intersection(unsupported))
        if supplied:
            raise ToolError(
                "UNSUPPORTED_PROVIDER_MODE: The following provider-only network "
                f"arguments are not exposed through Work: {', '.join(supplied)}."
            )
        effects = self.resolver.resolve(tool_name, arguments)
        decision = self.policy.evaluate(effects)

        if decision.kind is DecisionKind.ALLOW:
            return await call_next(context)

        if decision.kind is DecisionKind.BLOCK:
            raise ToolError(self._error_message(decision))

        if decision.kind is DecisionKind.QUARANTINE:
            if tool_name.casefold() not in capabilities.direct_delete_tools:
                raise ToolError(
                    "HR-003_QUARANTINE_REQUIRED: The command explicitly requests "
                    "permanent deletion. Use a filesystem delete tool or "
                    "kis_quarantine_path so the target is moved to recoverable quarantine."
                )

            try:
                records = list(self.quarantine_paths(decision.paths))
            except QuarantineError as exc:
                raise ToolError(f"HR-003_QUARANTINE_FAILED: {exc}") from exc
            payload = {"quarantined": records}
            rendered = json.dumps(payload, indent=2, sort_keys=True)
            return ToolResult(
                content=rendered,
                structured_content={"result": rendered},
            )

        raise RuntimeError(f"Unexpected policy decision: {decision.kind}")

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
