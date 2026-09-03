from __future__ import annotations

import json
from typing import Any, Protocol

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...mcp2026 import DURABLE_EXTERNAL_TASK_CONFIG, SYNC_FALLBACK_TASK_CONFIG
from .contracts import CompletionReceipt, CompletionResult
from .service import CompletionInvocationError

_ANNOTATIONS = {
    "read_only_hint": False,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": True,
}


class CompletionServicePort(Protocol):
    async def prepare(
        self,
        *,
        project_id: str,
        commit: str,
        source_base: str,
        branch: str,
        expected_remote_branch: str | None,
        expected_remote_default: str,
        title: str,
        body: str,
        approved: bool,
        task_terms: tuple[str, ...] = (),
        complexity: str = "medium",
        risk_triggers: tuple[str, ...] = (),
        max_verifications: int | None = None,
        verification_timeout_ms: int = 120_000,
        review_types: tuple[str, ...] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
        documentation_impact: str = "not_assessed",
        residual_state: str = "none declared",
        deadline_ms: int = 120_000,
        reconcile_only: bool = False,
        promotion_work_id: str | None = None,
    ) -> CompletionResult | CompletionReceipt: ...


def register_completion_tool(server: FastMCP, service: CompletionServicePort) -> None:
    @server.tool(
        name="prepare_reviewable_pull_request",
        annotations=_ANNOTATIONS,
        task=DURABLE_EXTERNAL_TASK_CONFIG,
    )
    async def prepare_reviewable_pull_request(
        project_id: str,
        commit: str,
        source_base: str,
        branch: str,
        expected_remote_branch: str | None,
        expected_remote_default: str,
        title: str,
        body: str,
        approved: bool,
        task_terms: list[str] | None = None,
        complexity: str = "medium",
        risk_triggers: list[str] | None = None,
        max_verifications: int | None = None,
        verification_timeout_ms: int = 120_000,
        review_types: list[str] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
        documentation_impact: str = "not_assessed",
        residual_state: str = "none declared",
        deadline_ms: int = 120_000,
        reconcile_only: bool = False,
        promotion_work_id: str | None = None,
    ) -> dict[str, object]:
        """Prepare review through a required MCP 2026 task-backed execution."""
        return await _prepare_result(service, locals())

    @server.tool(
        name="prepare_reviewable_pull_request_sync",
        annotations=_ANNOTATIONS,
        task=SYNC_FALLBACK_TASK_CONFIG,
    )
    async def prepare_reviewable_pull_request_sync(
        project_id: str,
        commit: str,
        source_base: str,
        branch: str,
        expected_remote_branch: str | None,
        expected_remote_default: str,
        title: str,
        body: str,
        approved: bool,
        task_terms: list[str] | None = None,
        complexity: str = "medium",
        risk_triggers: list[str] | None = None,
        max_verifications: int | None = None,
        verification_timeout_ms: int = 120_000,
        review_types: list[str] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
        documentation_impact: str = "not_assessed",
        residual_state: str = "none declared",
        deadline_ms: int = 120_000,
        reconcile_only: bool = False,
        promotion_work_id: str | None = None,
    ) -> dict[str, object]:
        """Compatibility fallback for clients that do not implement MCP Tasks."""
        return await _prepare_result(service, locals())


async def _prepare_result(
    service: CompletionServicePort,
    arguments: dict[str, Any],
) -> dict[str, object]:
    try:
        result = await service.prepare(
            project_id=arguments["project_id"],
            commit=arguments["commit"],
            source_base=arguments["source_base"],
            branch=arguments["branch"],
            expected_remote_branch=arguments["expected_remote_branch"],
            expected_remote_default=arguments["expected_remote_default"],
            title=arguments["title"],
            body=arguments["body"],
            approved=arguments["approved"],
            task_terms=tuple(arguments["task_terms"] or ()),
            complexity=arguments["complexity"],
            risk_triggers=tuple(arguments["risk_triggers"] or ()),
            max_verifications=arguments["max_verifications"],
            verification_timeout_ms=arguments["verification_timeout_ms"],
            review_types=(
                tuple(arguments["review_types"])
                if arguments["review_types"] is not None
                else None
            ),
            review_backend=arguments["review_backend"],
            review_model=arguments["review_model"],
            documentation_impact=arguments["documentation_impact"],
            residual_state=arguments["residual_state"],
            deadline_ms=arguments["deadline_ms"],
            reconcile_only=arguments["reconcile_only"],
            promotion_work_id=arguments["promotion_work_id"],
        )
        return result.to_json_dict()
    except CompletionInvocationError as exc:
        raise ToolError(
            _error_payload(
                exc.code,
                exc.reason,
                retryable=exc.retryable,
                stage=exc.stage,
                completed_steps=exc.completed_steps,
                operation_id=exc.operation_id,
                operation_state=exc.operation_state,
                elapsed_ms=exc.elapsed_ms,
                stage_timings_ms=exc.stage_timings_ms,
            )
        ) from exc
    except ValueError as exc:
        raise ToolError(_error_payload("COMPLETION_REQUEST_INVALID", str(exc))) from exc


def _error_payload(
    code: str,
    reason: str,
    *,
    retryable: bool = False,
    stage: str | None = None,
    completed_steps: tuple[str, ...] = (),
    operation_id: str | None = None,
    operation_state: str | None = None,
    elapsed_ms: int = 0,
    stage_timings_ms: dict[str, int] | None = None,
) -> str:
    payload: dict[str, object] = {
        "code": code,
        "message": "Completion coordination failed.",
        "reason": reason,
        "retryable": retryable,
    }
    if stage is not None:
        payload["stage"] = stage
    if completed_steps:
        payload["completed_steps"] = list(completed_steps)
    if operation_id is not None:
        payload["operation_id"] = operation_id
    if operation_state is not None:
        payload["operation_state"] = operation_state
    if operation_id is not None or operation_state is not None or elapsed_ms or stage_timings_ms:
        payload["elapsed_ms"] = elapsed_ms
    if stage_timings_ms:
        payload["stage_timings_ms"] = dict(stage_timings_ms)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


__all__ = ["CompletionServicePort", "register_completion_tool"]
