from __future__ import annotations

import json
from typing import Protocol

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .contracts import AgentValidationResult
from .execution import AgentValidationError

_PROCESS_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


class AgentValidationPort(Protocol):
    async def validate(
        self,
        *,
        project: str,
        target: str = "generic",
        strict: bool = False,
        max_files: int | None = None,
    ) -> AgentValidationResult: ...


def register_agent_validation_tool(server: FastMCP, service: AgentValidationPort) -> None:
    @server.tool(name="validate_agent_configuration", annotations=_PROCESS_ANNOTATIONS)
    async def validate_agent_configuration(
        project: str,
        target: str = "generic",
        strict: bool = False,
        max_files: int | None = None,
    ) -> dict[str, object]:
        """Validate local agent configuration through pinned agnix without fix authority."""
        try:
            return (
                await service.validate(
                    project=project,
                    target=target,
                    strict=strict,
                    max_files=max_files,
                )
            ).to_json_dict()
        except AgentValidationError as exc:
            raise ToolError(
                json.dumps(
                    {
                        "code": exc.code,
                        "message": "Agent configuration validation failed.",
                        "reason": exc.reason,
                        "retryable": False,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ) from exc


__all__ = ["AgentValidationPort", "register_agent_validation_tool"]
