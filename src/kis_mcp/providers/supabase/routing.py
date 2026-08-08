from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from kis_mcp.projects import ProjectRegistry


RuntimeToolsSource = Callable[[], Sequence[Any]]


class SupabaseProjectRoutingError(RuntimeError):
    """Raised when a Supabase call is not bound to an approved project context."""


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


class SupabaseProjectRouting:
    """Authorize explicit project calls and annotation-backed account reads."""

    def __init__(
        self,
        registry: ProjectRegistry,
        runtime_tools_source: RuntimeToolsSource,
    ) -> None:
        self.registry = registry
        self.runtime_tools_source = runtime_tools_source

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

        tool = next(
            (
                item
                for item in self.runtime_tools_source()
                if str(getattr(item, "name", "")) == tool_name
            ),
            None,
        )
        if tool is not None and _read_only_hint(tool):
            return
        raise SupabaseProjectRoutingError(
            "Supabase operation requires a registered project_id unless the "
            "upstream tool is explicitly annotated read-only"
        )


class SupabaseProjectRoutingMiddleware(Middleware):
    def __init__(self, routing: SupabaseProjectRouting) -> None:
        self.routing = routing

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        try:
            self.routing.authorize(
                str(context.message.name),
                dict(context.message.arguments or {}),
            )
        except SupabaseProjectRoutingError as exc:
            raise ToolError(str(exc)) from exc
        return await call_next(context)


__all__ = [
    "RuntimeToolsSource",
    "SupabaseProjectRouting",
    "SupabaseProjectRoutingError",
    "SupabaseProjectRoutingMiddleware",
]
