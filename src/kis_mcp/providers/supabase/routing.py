from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from kis_mcp.projects import ProjectRegistry


RuntimeToolsSource = Callable[[], Sequence[Any]]
_PROJECT_REFERENCE_ARGUMENTS = {
    "get_project": "id",
}


class SupabaseProjectRoutingError(RuntimeError):
    """Raised when a Supabase call is not bound to an approved project context."""


@dataclass(slots=True)
class SupabaseCommissioningState:
    """Record bounded live-verification evidence for one provider runtime."""

    registered_project_read_verified: bool = False
    last_verified_tool: str | None = None

    def mark_registered_project_read(self, tool_name: str) -> None:
        self.registered_project_read_verified = True
        self.last_verified_tool = str(tool_name)


def _read_only_hint(tool: Any) -> bool:
    annotations = getattr(tool, "annotations", None)
    if isinstance(annotations, Mapping):
        return annotations.get("readOnlyHint") is True or annotations.get("read_only_hint") is True
    return (
        getattr(annotations, "readOnlyHint", None) is True
        or getattr(annotations, "read_only_hint", None) is True
    )


def _project_id(arguments: Mapping[str, Any]) -> str | None:
    value = arguments.get("project_id")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SupabaseProjectRoutingError("Supabase project_id must be a non-empty string")
    return value.strip()


def _project_reference(tool_name: str, arguments: Mapping[str, Any]) -> str | None:
    project_id = _project_id(arguments)
    if project_id is not None:
        return project_id
    argument_name = _PROJECT_REFERENCE_ARGUMENTS.get(tool_name)
    if argument_name is None:
        return None
    value = arguments.get(argument_name)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


class SupabaseProjectRouting:
    """Authorize explicit project calls and annotation-backed account reads."""

    def __init__(
        self,
        registry: ProjectRegistry,
        runtime_tools_source: RuntimeToolsSource,
    ) -> None:
        self.registry = registry
        self.runtime_tools_source = runtime_tools_source

    def _runtime_tool(self, tool_name: str) -> Any | None:
        return next(
            (
                item
                for item in self.runtime_tools_source()
                if str(getattr(item, "name", "")) == tool_name
            ),
            None,
        )

    def authorize(self, tool_name: str, arguments: Mapping[str, Any]) -> None:
        if tool_name == "kis_supabase_health":
            return

        project_id = _project_id(arguments)
        if project_id is not None:
            if project_id not in self.registry.supabase_project_refs:
                raise SupabaseProjectRoutingError(
                    f"Supabase project_id is not registered: {project_id}"
                )
            return

        tool = self._runtime_tool(tool_name)
        if tool is not None and _read_only_hint(tool):
            return
        raise SupabaseProjectRoutingError(
            "Supabase operation requires a registered project_id unless the "
            "upstream tool is explicitly annotated read-only"
        )

    def is_registered_project_read(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
    ) -> bool:
        project_ref = _project_reference(tool_name, arguments)
        if project_ref is None or project_ref not in self.registry.supabase_project_refs:
            return False
        tool = self._runtime_tool(tool_name)
        return tool is not None and _read_only_hint(tool)


class SupabaseProjectRoutingMiddleware(Middleware):
    def __init__(
        self,
        routing: SupabaseProjectRouting,
        commissioning_state: SupabaseCommissioningState | None = None,
    ) -> None:
        self.routing = routing
        self.commissioning_state = commissioning_state

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        tool_name = str(context.message.name)
        arguments = dict(context.message.arguments or {})
        try:
            self.routing.authorize(tool_name, arguments)
        except SupabaseProjectRoutingError as exc:
            raise ToolError(str(exc)) from exc
        result = await call_next(context)
        if (
            self.commissioning_state is not None
            and self.routing.is_registered_project_read(tool_name, arguments)
        ):
            self.commissioning_state.mark_registered_project_read(tool_name)
        return result


__all__ = [
    "RuntimeToolsSource",
    "SupabaseCommissioningState",
    "SupabaseProjectRouting",
    "SupabaseProjectRoutingError",
    "SupabaseProjectRoutingMiddleware",
]
