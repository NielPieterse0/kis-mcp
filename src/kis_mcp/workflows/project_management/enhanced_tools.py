from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...work_management.board import (
    WorkBoardProjectionBridge,
    board_field_names,
    build_work_board,
    select_current_work,
)
from ...work_management.board_bridge import get_work_board_bridge
from ...work_management.canonical_contracts import load_canonical_work_contracts
from ...work_management.results import error_json, result_envelope

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


def register_project_management_enhancement_tools(
    server: FastMCP,
    service: Any,
    *,
    board_bridge: WorkBoardProjectionBridge | None = None,
) -> None:
    tool_server = FastMCP("kis-mcp-project-management-enhancements")
    active_bridge = board_bridge or get_work_board_bridge()

    @tool_server.tool(annotations=_EXTERNAL_READ)
    async def project_management_current_work(
        project_id: str,
        execution_owner: str,
        item_limit: int = 1000,
    ) -> dict[str, Any]:
        """Resume already-claimed Active work without changing claim or lifecycle state."""

        try:
            inventory = await service.read_inventory(
                project_id,
                field_names=board_field_names(),
                item_limit=item_limit,
            )
            selection = select_current_work(
                inventory,
                project_id,
                execution_owner,
            )
            selected = selection.selected
            return result_envelope(
                selection.to_json_dict(),
                project_id,
                repository=selected.repository if selected else inventory.binding.repository,
                issue_number=selected.number if selected else None,
                complete=selection.complete,
                truncated=inventory.truncated,
                warnings=selection.reasons if not selection.complete else (),
                next_actions=selection.next_actions,
            )
        except Exception as exc:
            raise ToolError(error_json("project_management_current_work", exc)) from exc

    @tool_server.tool(annotations=_EXTERNAL_READ)
    async def project_management_board_data(
        project_id: str,
        include_history: bool = False,
        states: list[str] | None = None,
        owner: str | None = None,
        query: str | None = None,
        group_by: str = "state",
        item_limit: int = 1000,
    ) -> dict[str, Any]:
        """Read one normalized active-first Work board projection from authoritative Project inventory."""

        try:
            inventory = await service.read_inventory(
                project_id,
                field_names=board_field_names(),
                item_limit=item_limit,
            )
            snapshot = build_work_board(
                inventory,
                project_id,
                include_history=include_history,
                states=tuple(states or ()),
                owner=owner,
                query=query,
                group_by=group_by,
            )
            active_bridge.publish(snapshot)
            warnings = ("inventory_truncated",) if inventory.truncated else ()
            return result_envelope(
                snapshot.to_json_dict(),
                project_id,
                repository=inventory.binding.repository,
                complete=snapshot.complete,
                truncated=snapshot.truncated,
                warnings=warnings,
                next_actions=(
                    "project_management_current_work",
                    "project_management_next_work",
                ),
            )
        except Exception as exc:
            raise ToolError(error_json("project_management_board_data", exc)) from exc

    @tool_server.tool(annotations=_LOCAL_READ)
    def project_management_contract() -> dict[str, Any]:
        """Describe canonical Work semantics plus action/result/error contracts."""

        canonical = load_canonical_work_contracts()
        return {
            "schema_version": 1,
            "canonical_contracts": canonical.to_json_dict(),
            "result_envelope": {
                "fields": [
                    "observed_at",
                    "resolved_target",
                    "provenance",
                    "result",
                    "next_actions",
                ],
                "authority": "configured_work_management_backend",
            },
            "typed_errors": [
                "provider_unavailable",
                "project_not_commissioned",
                "inventory_incomplete",
                "conflict",
                "invalid_transition",
                "not_found",
                "invalid_request",
                "internal",
            ],
            "operations": {
                "project_management_inventory": "external_read",
                "project_management_next_work": "external_read",
                "project_management_current_work": "external_read",
                "project_management_board_data": "external_read",
                "project_management_schema_plan": "external_read",
                "project_management_schema_status": "external_read",
                "project_management_merge_readiness": "local_read",
                "project_management_documentation_reconcile": "local_read",
                "project_management_portfolio_status": "local_read",
                "project_management_verify_traceability": "local_read",
                "project_management_reconcile": "preview_or_idempotent_external_mutation",
                "project_management_take_next_work": "preview_or_idempotent_external_mutation",
                "project_management_claim_work": "preview_or_idempotent_external_mutation",
                "project_management_release_work": "preview_or_idempotent_external_mutation",
                "project_management_transition_work": "preview_or_idempotent_external_mutation",
                "project_management_hold_work": "preview_or_idempotent_external_mutation",
                "project_management_defer_work": "preview_or_idempotent_external_mutation",
                "project_management_sync_change_classification": "preview_or_idempotent_external_mutation",
                "project_management_complete_work": "preview_or_idempotent_external_mutation",
                "project_management_persist_review": "local_idempotent_persistence",
            },
            "mutation_rule": "apply=true requires an explicit idempotency key where the operation mutates external Project state",
        }

    server.mount(tool_server)


__all__ = ["register_project_management_enhancement_tools"]
