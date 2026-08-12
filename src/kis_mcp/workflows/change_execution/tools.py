from __future__ import annotations

import json
from typing import Protocol

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .contracts import ChangeExecutionResult
from .service import ChangeExecutionInvocationError

_PROCESS_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


class ChangeExecutionServicePort(Protocol):
    async def execute(
        self,
        *,
        project: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        task_terms: tuple[str, ...] = (),
        max_verifications: int = 20,
        verification_timeout_ms: int = 120_000,
        review_types: tuple[str, ...] = ("code-quality",),
        review_backend: str | None = None,
        review_model: str | None = None,
    ) -> ChangeExecutionResult: ...


def register_change_execution_tool(
    server: FastMCP,
    service: ChangeExecutionServicePort,
) -> None:
    @server.tool(name="execute_change_workflow", annotations=_PROCESS_ANNOTATIONS)
    async def execute_change_workflow(
        project: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        task_terms: list[str] | None = None,
        max_verifications: int = 20,
        verification_timeout_ms: int = 120_000,
        review_types: list[str] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
    ) -> dict[str, object]:
        """Execute selected verification and bounded specialist reviews for one change."""
        try:
            result = await service.execute(
                project=project,
                source=source,
                commit_ref=commit_ref,
                base_ref=base_ref,
                head_ref=head_ref,
                task_terms=tuple(task_terms or ()),
                max_verifications=max_verifications,
                verification_timeout_ms=verification_timeout_ms,
                review_types=(
                    tuple(review_types)
                    if review_types is not None
                    else ("code-quality",)
                ),
                review_backend=review_backend,
                review_model=review_model,
            )
            return result.to_json_dict()
        except ChangeExecutionInvocationError as exc:
            raise ToolError(_error_payload(exc.code, exc.reason)) from exc
        except ValueError as exc:
            raise ToolError(
                _error_payload("CHANGE_EXECUTION_REQUEST_INVALID", str(exc))
            ) from exc


def _error_payload(code: str, reason: str) -> str:
    return json.dumps(
        {
            "code": code,
            "message": "Change execution request failed.",
            "reason": reason,
            "retryable": False,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


__all__ = ["ChangeExecutionServicePort", "register_change_execution_tool"]
