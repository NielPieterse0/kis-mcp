from __future__ import annotations

import json
from typing import Any, Protocol

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .change_inspection_contracts import InspectChangeRequest, InspectChangeResponse
from .contracts import InspectProjectRequest, InspectProjectResponse
from .errors import DiscoverError


class InspectProjectPort(Protocol):
    def inspect(self, request: InspectProjectRequest) -> InspectProjectResponse: ...


class InspectChangePort(Protocol):
    def inspect(self, request: InspectChangeRequest) -> InspectChangeResponse: ...


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


def register_change_tools(server: FastMCP, service: InspectChangePort) -> None:
    """Register the bounded read-only change inspection surface."""

    @server.tool(
        name="inspect_change",
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def inspect_change(path: str) -> dict[str, Any]:
        """Inspect the current working-tree change for one local project."""

        try:
            request = InspectChangeRequest(path=path)
        except ValueError as exc:
            payload = {
                "code": "DISCOVER_CHANGE_REQUEST_INVALID",
                "message": "The inspect_change request is invalid.",
                "reason": str(exc),
                "field": "path",
                "corrective_actions": [
                    r"Provide a non-empty local project path beneath C:\Projects."
                ],
                "retryable": False,
            }
            raise ToolError(
                json.dumps(payload, sort_keys=True, separators=(",", ":"))
            ) from exc
        return service.inspect(request).to_json_dict()


__all__ = [
    "InspectChangePort",
    "InspectProjectPort",
    "register_change_tools",
    "register_discover_tools",
]
