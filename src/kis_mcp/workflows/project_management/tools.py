from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...work_management import (
    DocumentationMilestoneState,
    LifecycleState,
    ReviewArtifactKind,
    WorkManagementService,
    apply_documentation_reconciliation_event,
    complete_documentation_reconciliation,
    create_documentation_reconciliation_due,
    create_review_evidence_manifest,
    evaluate_merge_readiness,
    evaluate_traceability,
)
from ...work_management.results import error_json
from .parsing import (
    desired_projection_from_json,
    implementation_trace_from_json,
    observed_projection_from_json,
    traceability_stage,
    work_record_from_json,
)

_EXTERNAL_READ = {
    "read_only_hint": True,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": True,
}
_LOCAL_READ = {
    "read_only_hint": True,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": False,
}
_EXTERNAL_MUTATION = {
    "read_only_hint": False,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": True,
}
_LOCAL_MUTATION = {
    "read_only_hint": False,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": False,
}


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
    return ToolError(error_json(code, exc))


def _activation_succeeded(result: Mapping[str, Any] | None) -> bool:
    if not isinstance(result, Mapping) or result.get("phase") != "active":
        return False
    outcomes = result.get("outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        return False
    return all(isinstance(item, Mapping) and item.get("success") is True for item in outcomes)


def register_project_management_tools(
    server: FastMCP,
    service: WorkManagementService | Any,
    *,
    activation_materializer: Callable[[str, str, int], Awaitable[dict[str, Any]]] | None = None,
) -> None:
    tool_server = FastMCP("kis-mcp-project-management")

    @tool_server.tool(annotations=_EXTERNAL_READ)
    async def project_management_inventory(
        project_id: str,
        field_names: list[str] | None = None,
        item_limit: int = 1000,
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

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
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
            if apply and (
                not isinstance(idempotency_key, str) or not idempotency_key.strip()
            ):
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

    @tool_server.tool(annotations=_EXTERNAL_READ)
    async def project_management_next_work(
        project_id: str,
        item_limit: int = 1000,
    ) -> dict[str, Any]:
        """Select the next eligible Ready and unclaimed Project issue deterministically."""

        try:
            selection = await service.next_work(project_id, item_limit=item_limit)
            return selection.to_json_dict()
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_NEXT_WORK_FAILED", exc) from exc

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
    async def project_management_take_next_work(
        project_id: str,
        execution_owner: str,
        apply: bool = False,
        idempotency_key: str | None = None,
        item_limit: int = 1000,
    ) -> dict[str, Any]:
        """Select and preview/claim the next eligible Ready issue in one bounded workflow."""

        try:
            result = await service.take_next_work(
                project_id,
                execution_owner,
                apply=apply,
                idempotency_key=idempotency_key,
                item_limit=item_limit,
            )
            claim = result.get("claim")
            if apply and activation_materializer is not None and _activation_succeeded(claim):
                selected = result.get("selection", {}).get("selected")
                if isinstance(selected, Mapping):
                    repository = selected.get("repository")
                    number = selected.get("number")
                    if isinstance(repository, str) and isinstance(number, int):
                        result["task_handoff"] = await activation_materializer(project_id, repository, number)
            return result
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_TAKE_NEXT_WORK_FAILED", exc) from exc

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
    async def project_management_claim_work(
        project_id: str,
        repository: str,
        issue_number: int,
        execution_owner: str,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Preview or claim one Ready issue using a conflict-safe two-phase claim."""

        try:
            result = await service.claim_work(
                project_id,
                repository,
                issue_number,
                execution_owner,
                apply=apply,
                idempotency_key=idempotency_key,
            )
            if apply and activation_materializer is not None and _activation_succeeded(result):
                result["task_handoff"] = await activation_materializer(project_id, repository, issue_number)
            return result
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_CLAIM_WORK_FAILED", exc) from exc

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
    async def project_management_release_work(
        project_id: str,
        repository: str,
        issue_number: int,
        expected_owner: str,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Preview or release an exact execution claim back to Ready."""

        try:
            return await service.release_work(
                project_id,
                repository,
                issue_number,
                expected_owner,
                apply=apply,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_RELEASE_WORK_FAILED", exc) from exc

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
    async def project_management_transition_work(
        project_id: str,
        repository: str,
        issue_number: int,
        target: str,
        metadata: dict[str, Any] | None = None,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Preview or apply one configured command-plane Work State transition."""

        try:
            return await service.transition_work(
                project_id,
                repository,
                issue_number,
                LifecycleState(target),
                metadata=metadata,
                apply=apply,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_TRANSITION_WORK_FAILED", exc) from exc

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
    async def project_management_hold_work(
        project_id: str,
        repository: str,
        issue_number: int,
        review_trigger: str,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Preview or place work On Hold with the configured review trigger metadata."""

        try:
            return await service.transition_work(
                project_id,
                repository,
                issue_number,
                LifecycleState.ON_HOLD,
                metadata={"Review Trigger": review_trigger},
                apply=apply,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_HOLD_WORK_FAILED", exc) from exc

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
    async def project_management_defer_work(
        project_id: str,
        repository: str,
        issue_number: int,
        review_trigger: str,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Preview or defer work with the configured review trigger metadata."""

        try:
            return await service.transition_work(
                project_id,
                repository,
                issue_number,
                LifecycleState.DEFERRED,
                metadata={"Review Trigger": review_trigger},
                apply=apply,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_DEFER_WORK_FAILED", exc) from exc

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
    async def project_management_sync_change_classification(
        project_id: str,
        repository: str,
        issue_number: int,
        change_id: str,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Project authoritative schema-v4 Complexity/Risk classification from `.work` evidence."""

        try:
            return await service.sync_change_classification(
                project_id,
                repository,
                issue_number,
                change_id,
                apply=apply,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            raise _tool_error(
                "PROJECT_MANAGEMENT_CLASSIFICATION_SYNC_FAILED", exc
            ) from exc

    @tool_server.tool(annotations=_EXTERNAL_MUTATION)
    async def project_management_complete_work(
        project_id: str,
        repository: str,
        issue_number: int,
        record: dict[str, Any],
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Guard and preview/apply the terminal Work State after closeout evidence is complete."""

        try:
            return await service.complete_work(
                project_id,
                repository,
                issue_number,
                work_record_from_json(record),
                apply=apply,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_COMPLETE_WORK_FAILED", exc) from exc

    @tool_server.tool(annotations=_EXTERNAL_READ)
    async def project_management_schema_plan(
        project_id: str,
    ) -> dict[str, Any]:
        """Return a typed commissioning plan for Project schema drift and provider gaps."""

        try:
            return (await service.schema_plan(project_id)).to_json_dict()
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_SCHEMA_PLAN_FAILED", exc) from exc

    @tool_server.tool(annotations=_EXTERNAL_READ)
    async def project_management_schema_status(
        project_id: str,
    ) -> dict[str, Any]:
        """Compare one configured GitHub Project against the approved schema manifest."""

        try:
            status = await service.schema_status(project_id)
            return status.to_json_dict()
        except Exception as exc:
            raise _tool_error("PROJECT_MANAGEMENT_SCHEMA_STATUS_FAILED", exc) from exc

    @tool_server.tool(annotations=_LOCAL_READ)
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

    @tool_server.tool(annotations=_LOCAL_READ)
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
            updated_record = work_record
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
                if not matches and not required_updates:
                    due = create_documentation_reconciliation_due(
                        implementation_trace,
                        pull_request_number,
                        documentation_task_id,
                        (),
                    )
                    updated_record = apply_documentation_reconciliation_event(
                        updated_record,
                        due,
                    )
                    event = complete_documentation_reconciliation(
                        due,
                        completion_revision,
                    )
                elif len(matches) == 1:
                    event = complete_documentation_reconciliation(
                        matches[0],
                        completion_revision,
                    )
                else:
                    raise ValueError(
                        "exactly one due documentation reconciliation event is required"
                    )
                phase = "post_merge_complete"
            updated = apply_documentation_reconciliation_event(updated_record, event)
            return {
                "phase": phase,
                "event": event.to_json_dict(),
                "record": updated.to_json_dict(),
            }
        except Exception as exc:
            raise _tool_error(
                "PROJECT_MANAGEMENT_DOCUMENTATION_RECONCILE_FAILED", exc
            ) from exc

    @tool_server.tool(annotations=_LOCAL_READ)
    def project_management_portfolio_status(
        records: list[dict[str, Any]],
        traceability_gaps: dict[str, list[str]] | None = None,
        provider_failures: dict[str, str] | None = None,
        truncated_projects: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build attributable portfolio status from normalized work records."""

        try:
            status = service.portfolio_status(
                tuple(
                    work_record_from_json(item) for item in _objects(records, "records")
                ),
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

    @tool_server.tool(annotations=_LOCAL_MUTATION)
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

    @tool_server.tool(annotations=_LOCAL_READ)
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
