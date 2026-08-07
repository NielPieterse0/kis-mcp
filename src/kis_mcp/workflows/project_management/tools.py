from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...work_management import (
    ReviewArtifactKind,
    WorkManagementService,
    create_review_evidence_manifest,
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
