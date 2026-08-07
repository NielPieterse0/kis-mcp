from __future__ import annotations

import json
from typing import Protocol

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .contracts import VerificationResult
from .execution import VerificationExecutionError

_PROCESS_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


class VerificationServicePort(Protocol):
    async def run(
        self,
        *,
        project: str,
        verification_id: str,
        timeout_ms: int = 120_000,
    ) -> VerificationResult: ...


def register_verification_tool(
    server: FastMCP,
    service: VerificationServicePort,
) -> None:
    @server.tool(name="run_verification", annotations=_PROCESS_ANNOTATIONS)
    async def run_verification(
        project: str,
        verification_id: str,
        timeout_ms: int = 120_000,
    ) -> dict[str, object]:
        """Execute one verification previously discovered for a local project."""
        try:
            return (
                await service.run(
                    project=project,
                    verification_id=verification_id,
                    timeout_ms=timeout_ms,
                )
            ).to_json_dict()
        except VerificationExecutionError as exc:
            raise ToolError(
                json.dumps(
                    {
                        "code": exc.code,
                        "message": "Verification execution request failed.",
                        "reason": exc.reason,
                        "retryable": False,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ) from exc


__all__ = ["VerificationServicePort", "register_verification_tool"]
