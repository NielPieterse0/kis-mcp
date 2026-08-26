from __future__ import annotations

import json

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .evidence import GovernanceEvidenceCollector
from .service import GovernanceService

_READ_ONLY = {
    "read_only_hint": True,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": False,
}


def register_governance_tools(
    server: FastMCP,
    *,
    service: GovernanceService,
    collector: GovernanceEvidenceCollector,
) -> None:
    @server.tool(name="list_governance_capabilities", annotations=_READ_ONLY)
    def list_governance_capabilities() -> dict[str, object]:
        """List enabled advisory governance rules."""
        return {
            "schema_version": 1,
            "capabilities": [item.to_json_dict() for item in service.list_capabilities()],
            "policy_effect": "advisory_only",
        }

    @server.tool(name="inspect_repository_governance", annotations=_READ_ONLY)
    def inspect_repository_governance(project: str) -> dict[str, object]:
        """Inspect declared authority and documentation drift without changing the repository."""
        try:
            return service.inspect(collector.collect(project)).to_json_dict()
        except Exception as exc:
            raise _tool_error("GOVERN_INSPECTION_FAILED", exc) from exc

    @server.tool(name="evaluate_governance_rules", annotations=_READ_ONLY)
    def evaluate_governance_rules(project: str, rule_ids: list[str]) -> dict[str, object]:
        """Evaluate an explicit subset of enabled governance rules."""
        try:
            evidence = collector.collect(project)
            return service.inspect(evidence, rule_ids=tuple(rule_ids)).to_json_dict()
        except Exception as exc:
            raise _tool_error("GOVERN_EVALUATION_FAILED", exc) from exc

    @server.tool(name="describe_governance_finding", annotations=_READ_ONLY)
    def describe_governance_finding(project: str, finding_id: str) -> dict[str, object]:
        """Describe one current deterministic governance finding by ID."""
        try:
            return service.describe_finding(
                collector.collect(project), finding_id
            ).to_json_dict()
        except Exception as exc:
            raise _tool_error("GOVERN_FINDING_NOT_AVAILABLE", exc) from exc


def _tool_error(code: str, exc: Exception) -> ToolError:
    return ToolError(
        json.dumps(
            {
                "code": code,
                "message": "Governance evaluation could not complete.",
                "reason": str(exc),
                "retryable": False,
                "policy_effect": "none",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


__all__ = ["register_governance_tools"]
