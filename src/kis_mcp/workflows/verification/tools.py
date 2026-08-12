from __future__ import annotations

import json
from typing import Protocol

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .contracts import VerificationResult, VerificationSelectionResult
from .execution import VerificationExecutionError
from .selection import VerificationSelectionError

_PROCESS_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
_READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
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


class VerificationSelectionServicePort(Protocol):
    def select(
        self,
        *,
        project: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        task_terms: tuple[str, ...] = (),
        max_verifications: int = 20,
    ) -> VerificationSelectionResult: ...


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


def register_verification_selection_tool(
    server: FastMCP,
    service: VerificationSelectionServicePort,
) -> None:
    @server.tool(name="select_change_verification", annotations=_READ_ONLY_ANNOTATIONS)
    def select_change_verification(
        project: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        task_terms: list[str] | None = None,
        max_verifications: int = 20,
    ) -> dict[str, object]:
        """Select current executable verification handoffs without running them."""
        try:
            return service.select(
                project=project,
                source=source,
                commit_ref=commit_ref,
                base_ref=base_ref,
                head_ref=head_ref,
                task_terms=tuple(task_terms or ()),
                max_verifications=max_verifications,
            ).to_json_dict()
        except VerificationSelectionError as exc:
            raise ToolError(json.dumps({
                "code": exc.code,
                "message": "Verification selection request failed.",
                "reason": exc.reason,
                "retryable": False,
            }, sort_keys=True, separators=(",", ":"))) from exc
        except ValueError as exc:
            raise ToolError(json.dumps({
                "code": "VERIFICATION_SELECTION_REQUEST_INVALID",
                "message": "Verification selection request failed.",
                "reason": str(exc),
                "retryable": False,
            }, sort_keys=True, separators=(",", ":"))) from exc


__all__ = [
    "VerificationSelectionServicePort",
    "VerificationServicePort",
    "register_verification_selection_tool",
    "register_verification_tool",
]
