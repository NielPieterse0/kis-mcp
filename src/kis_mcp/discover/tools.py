from __future__ import annotations

import json
from typing import Any, Protocol

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .contracts import InspectProjectRequest, InspectProjectResponse
from .errors import DiscoverError


class InspectProjectPort(Protocol):
    def inspect(self, request: InspectProjectRequest) -> InspectProjectResponse: ...


def register_discover_tools(server: FastMCP, service: InspectProjectPort) -> None:
    """Register the bounded read-only Discover public surface."""

    @server.tool(
        name="inspect_project",
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def inspect_project(
        path: str,
        limits: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Inspect one local project using bounded deterministic evidence discovery."""

        try:
            response = service.inspect(InspectProjectRequest(path=path, limits=limits))
        except DiscoverError as exc:
            raise ToolError(
                json.dumps(
                    exc.to_json_dict(),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ) from exc
        return response.to_json_dict()


__all__ = ["InspectProjectPort", "register_discover_tools"]
