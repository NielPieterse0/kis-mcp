from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from kis_mcp.repositories import RepositorySettings

from .scope import GitHubRepositoryScope, GitHubRepositoryScopeError


RepositorySettingsSource = Callable[[], RepositorySettings]


class GitHubRepositoryRouting:
    """Authorize each GitHub call against the currently selected repository."""

    def __init__(self, settings_source: RepositorySettingsSource) -> None:
        self.settings_source = settings_source

    def authorize(self, tool_name: str, arguments: Mapping[str, Any]) -> None:
        settings = self.settings_source()
        scope = GitHubRepositoryScope(
            (settings.github_repository,),
            ("get_me", "kis_github_health"),
            tuple(
                (project.owner, project.owner_type, project.project_number)
                for project in settings.gh_projects
            ),
        )
        scope.authorize(tool_name, arguments)


class GitHubRepositoryRoutingMiddleware(Middleware):
    def __init__(self, routing: GitHubRepositoryRouting) -> None:
        self.routing = routing

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        try:
            self.routing.authorize(
                str(context.message.name),
                dict(context.message.arguments or {}),
            )
        except GitHubRepositoryScopeError as exc:
            raise ToolError(str(exc)) from exc
        return await call_next(context)


__all__ = [
    "GitHubRepositoryRouting",
    "GitHubRepositoryRoutingMiddleware",
    "RepositorySettingsSource",
]
