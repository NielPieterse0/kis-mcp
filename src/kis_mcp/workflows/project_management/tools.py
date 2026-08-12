from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...work_management import (
    DocumentationMilestoneState,
    ReviewArtifactKind,
    WorkManagementService,
    apply_documentation_reconciliation_event,
    complete_documentation_reconciliation,
    create_documentation_reconciliation_due,
    create_review_evidence_manifest,
    evaluate_merge_readiness,
    evaluate_traceability,
)
from .parsing import (
    desired_projection_from_json,
    implementation_trace_from_json,
    observed_projection_from_json,
    traceability_stage,
    work_record_from_json,
)


def _objects(value: Sequence[Mapping[str, Any]], label: str) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{label} must be an array")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{label} must contain objects")
        result.append(dict(item))
    return result


def _tool_error(code: str, exc: Exception) -> ToolError:
    return ToolError(f"{code}:{type(exc).__name__}")


def register_project_management_tools(
    server: FastMCP,
    service: WorkManagementService | Any,
) -> None:
    tool_server = FastMCP("kis-mcp-project-management")

    @tool_server.tool
    async def project_management_inventory(
        project_id: str,
        field_names: list[str] | None = None,
        item_limit: int = 100,
    ) -> dict[str, Any]:
        """Read one configured Project inventory with bounded fields and items."""

        try:
            inventory = await service.read_inventory(
                project_id,
                field_names=tuple(field_names or ()),
                item_limit=item_limit,
            )
            return inventory.to_json_dict()
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_INVENTORY_FAILED", exc) from exc

    @tool_server.tool
    async def project_management_reconcile(
        project_id: str,
        desired: list[dict[str, Any]],
        observed: list[dict[str, Any]],
        supported_fields: list[str],
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Preview or explicitly apply deterministic Project reconciliation."""

        try:
            if apply and (not isinstance(idempotency_key, str) or not idempotency_key.strip()):
                raise ValueError("idempotency_key is required when apply is true")
            desired_values = tuple(
                desired_projection_from_json(item, default_project_id=project_id)
                for item in _objects(desired, "desired")
            )
            observed_values = tuple(
                observed_projection_from_json(item, default_project_id=project_id)
                for item in _objects(observed, "observed")
            )
            outcomes = await service.reconcile(
                project_id,
                desired_values,
                observed_values,
                supported_fields=tuple(supported_fields),
                apply=apply,
                idempotency_key=idempotency_key,
            )
            return {
                "mode": "apply" if apply else "preview",
                "outcomes": [item.to_json_dict() for item in outcomes],
            }
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_RECONCILE_FAILED", exc) from exc

    @tool_server.tool
    async def project_management_schema_status(
        project_id: str,
    ) -> dict[str, Any]:
        """Compare one configured GitHub Project against the approved schema manifest."""

        try:
            status = await service.schema_status(project_id)
            return status.to_json_dict()
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_SCHEMA_STATUS_FAILED", exc) from exc

    @tool_server.tool
    def project_management_merge_readiness(
        record: dict[str, Any],
        trace: dict[str, Any],
        pull_request_number: int,
    ) -> dict[str, Any]:
        """Evaluate exact-head traceability and pre-merge documentation readiness."""

        try:
            readiness = evaluate_merge_readiness(
                work_record_from_json(record),
                implementation_trace_from_json(trace),
                pull_request_number,
            )
            return readiness.to_json_dict()
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_MERGE_READINESS_FAILED", exc) from exc

    @tool_server.tool
    def project_management_documentation_reconcile(
        record: dict[str, Any],
        trace: dict[str, Any],
        pull_request_number: int,
        documentation_task_id: str,
        required_updates: list[str],
        completion_revision: str | None = None,
    ) -> dict[str, Any]:
        """Create or complete the post-merge documentation reconciliation milestone."""

        try:
            work_record = work_record_from_json(record)
            implementation_trace = implementation_trace_from_json(trace)
            if completion_revision is None:
                event = create_documentation_reconciliation_due(
                    implementation_trace,
                    pull_request_number,
                    documentation_task_id,
                    tuple(required_updates),
                )
                phase = "documentation_reconciliation_due"
            else:
                matches = tuple(
                    event
                    for event in implementation_trace.documentation_events
                    if event.pull_request_number == pull_request_number
                    and event.state
                    is DocumentationMilestoneState.DOCUMENTATION_RECONCILIATION_DUE
                )
                if len(matches) != 1:
                    raise ValueError(
                        "exactly one due documentation reconciliation event is required"
                    )
                event = complete_documentation_reconciliation(
                    matches[0],
                    completion_revision,
                )
                phase = "post_merge_complete"
            updated = apply_documentation_reconciliation_event(work_record, event)
            return {
                "phase": phase,
                "event": event.to_json_dict(),
                "record": updated.to_json_dict(),
            }
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_DOCUMENTATION_RECONCILE_FAILED", exc) from exc

    @tool_server.tool
    def project_management_portfolio_status(
        records: list[dict[str, Any]],
        traceability_gaps: dict[str, list[str]] | None = None,
        provider_failures: dict[str, str] | None = None,
        truncated_projects: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build attributable portfolio status from normalized work records."""

        try:
            status = service.portfolio_status(
                tuple(work_record_from_json(item) for item in _objects(records, "records")),
                traceability_gaps={
                    key: tuple(value)
                    for key, value in (traceability_gaps or {}).items()
                },
                provider_failures=provider_failures or {},
                truncated_projects=tuple(truncated_projects or ()),
            )
            return status.to_json_dict()
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_STATUS_FAILED", exc) from exc

    @tool_server.tool
    def project_management_persist_review(
        project_id: str,
        review_id: str,
        kind: str,
        content: str,
        expected_sha256: str | None = None,
    ) -> dict[str, Any]:
        """Persist one canonical review artifact atomically without delete capability."""

        try:
            artifact_kind = ReviewArtifactKind(kind)
            manifest = create_review_evidence_manifest(review_id)
            result = service.persist_review_artifact(
                project_id,
                manifest,
                artifact_kind,
                content,
                expected_sha256=expected_sha256,
            )
            return result.to_json_dict()
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_EVIDENCE_FAILED", exc) from exc

    @tool_server.tool
    def project_management_verify_traceability(
        trace: dict[str, Any],
        stage: str,
        pull_request_number: int | None = None,
    ) -> dict[str, Any]:
        """Evaluate one implementation trace at an explicit lifecycle stage."""

        try:
            report = evaluate_traceability(
                implementation_trace_from_json(trace),
                traceability_stage(stage),
                pull_request_number=pull_request_number,
            )
            return report.to_json_dict()
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_TRACEABILITY_FAILED", exc) from exc

    server.mount(tool_server)


__all__ = ["register_project_management_tools"]
