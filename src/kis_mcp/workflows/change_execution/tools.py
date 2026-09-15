from __future__ import annotations

import json
from typing import Any, Protocol

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...mcp2026 import DURABLE_EXTERNAL_TASK_CONFIG, SYNC_FALLBACK_TASK_CONFIG
from .contracts import ChangeExecutionResult
from .service import ChangeExecutionInvocationError

_PROCESS_ANNOTATIONS = {
    "read_only_hint": False,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": False,
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
        complexity: str = "medium",
        risk_triggers: tuple[str, ...] = (),
        max_verifications: int | None = None,
        verification_timeout_ms: int = 120_000,
        review_timeout_ms: int = 120_000,
        review_types: tuple[str, ...] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
        reviewers: tuple[dict[str, object], ...] | None = None,
        review_rounds: int = 1,
        review_adjudication: bool = False,
    ) -> ChangeExecutionResult: ...


def register_change_execution_tool(
    server: FastMCP,
    service: ChangeExecutionServicePort,
) -> None:
    @server.tool(
        name="execute_change_workflow",
        annotations=_PROCESS_ANNOTATIONS,
        task=DURABLE_EXTERNAL_TASK_CONFIG,
    )
    async def execute_change_workflow(
        project: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        task_terms: list[str] | None = None,
        complexity: str = "medium",
        risk_triggers: list[str] | None = None,
        max_verifications: int | None = None,
        verification_timeout_ms: int = 120_000,
        review_timeout_ms: int = 120_000,
        review_types: list[str] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
        reviewers: list[dict[str, object]] | None = None,
        review_rounds: int = 1,
        review_adjudication: bool = False,
    ) -> dict[str, object]:
        """Execute selected verification and reviews through required MCP Tasks."""
        return await _execute_result(service, locals())

    @server.tool(
        name="execute_change_workflow_sync",
        annotations=_PROCESS_ANNOTATIONS,
        task=SYNC_FALLBACK_TASK_CONFIG,
    )
    async def execute_change_workflow_sync(
        project: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        task_terms: list[str] | None = None,
        complexity: str = "medium",
        risk_triggers: list[str] | None = None,
        max_verifications: int | None = None,
        verification_timeout_ms: int = 120_000,
        review_timeout_ms: int = 120_000,
        review_types: list[str] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
        reviewers: list[dict[str, object]] | None = None,
        review_rounds: int = 1,
        review_adjudication: bool = False,
    ) -> dict[str, object]:
        """Compatibility fallback for clients that do not implement MCP Tasks."""
        return await _execute_result(service, locals())


async def _execute_result(
    service: ChangeExecutionServicePort,
    arguments: dict[str, Any],
) -> dict[str, object]:
    try:
        result = await service.execute(
            project=arguments["project"],
            source=arguments["source"],
            commit_ref=arguments["commit_ref"],
            base_ref=arguments["base_ref"],
            head_ref=arguments["head_ref"],
            task_terms=tuple(arguments["task_terms"] or ()),
            complexity=arguments["complexity"],
            risk_triggers=tuple(arguments["risk_triggers"] or ()),
            max_verifications=arguments["max_verifications"],
            verification_timeout_ms=arguments["verification_timeout_ms"],
            review_timeout_ms=arguments["review_timeout_ms"],
            review_types=(tuple(arguments["review_types"]) if arguments["review_types"] is not None else None),
            review_backend=arguments["review_backend"],
            review_model=arguments["review_model"],
            reviewers=(tuple(arguments["reviewers"]) if arguments["reviewers"] is not None else None),
            review_rounds=arguments["review_rounds"],
            review_adjudication=arguments["review_adjudication"],
        )
        return result.to_json_dict()
    except ChangeExecutionInvocationError as exc:
        raise ToolError(_error_payload(exc.code, exc.reason)) from exc
    except (TypeError, ValueError) as exc:
        raise ToolError(_error_payload("CHANGE_EXECUTION_REQUEST_INVALID", str(exc))) from exc


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
