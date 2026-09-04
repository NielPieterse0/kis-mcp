from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...work_management.results import error_json

_EXTERNAL_MUTATION = {
    "read_only_hint": False,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": True,
}


def register_project_management_triage_tool(
    server: FastMCP,
    service: Any,
) -> None:
    tool_server = FastMCP("kis-mcp-project-management-triage")

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
    async def project_management_progress_triage(
        project_id: str,
        repository: str,
        issue_number: int,
        issue_body: str,
        previous_fingerprint: str | None = None,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate Triage inputs and deterministically progress valid work to Ready."""
        try:
            return await service.progress_triage(
                project_id,
                repository,
                issue_number,
                issue_body,
                previous_fingerprint=previous_fingerprint,
                apply=apply,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            raise ToolError(
                error_json("PROJECT_MANAGEMENT_TRIAGE_FAILED", exc)
            ) from exc

    server.mount(tool_server)


__all__ = ["register_project_management_triage_tool"]
