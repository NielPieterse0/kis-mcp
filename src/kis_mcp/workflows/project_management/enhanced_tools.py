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
from ...work_management.results import error_json, result_envelope

_READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


def register_project_management_enhancement_tools(
    server: FastMCP,
    service: Any,
    *,
    board_bridge: WorkBoardProjectionBridge | None = None,
) -> None:
    tool_server = FastMCP("kis-mcp-project-management-enhancements")
    active_bridge = board_bridge or get_work_board_bridge()

    @tool_server.tool(annotations=_READ_ONLY)
    async def project_management_current_work(
        project_id: str,
        execution_owner: str,
        item_limit: int = 100,
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

    @tool_server.tool(annotations=_READ_ONLY)
    async def project_management_board_data(
        project_id: str,
        include_history: bool = False,
        states: list[str] | None = None,
        owner: str | None = None,
        query: str | None = None,
        group_by: str = "state",
        item_limit: int = 100,
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

    @tool_server.tool(annotations=_READ_ONLY)
    def project_management_contract() -> dict[str, Any]:
        """Describe Work Management action semantics and the normalized result/error contract."""

        return {
            "schema_version": 1,
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
                "project_management_inventory": "read",
                "project_management_next_work": "read",
                "project_management_current_work": "read",
                "project_management_board_data": "read",
                "project_management_schema_plan": "read",
                "project_management_schema_status": "read",
                "project_management_reconcile": "preview_or_idempotent_mutation",
                "project_management_take_next_work": "preview_or_idempotent_mutation",
                "project_management_claim_work": "preview_or_idempotent_mutation",
                "project_management_release_work": "preview_or_idempotent_mutation",
                "project_management_transition_work": "preview_or_idempotent_mutation",
                "project_management_hold_work": "preview_or_idempotent_mutation",
                "project_management_defer_work": "preview_or_idempotent_mutation",
                "project_management_complete_work": "preview_or_idempotent_mutation",
            },
            "mutation_rule": "apply=true requires an explicit idempotency key where the operation mutates external Project state",
        }

    server.mount(tool_server)


__all__ = ["register_project_management_enhancement_tools"]
