from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .lifecycle import LifecycleDecisionError, LifecycleDecisionService

_READ_ONLY = {
    "read_only_hint": True,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": False,
}


def register_lifecycle_decision_tool(
    server: FastMCP,
    service: LifecycleDecisionService,
    *,
    project_boundary: str,
) -> None:
    boundary = Path(project_boundary).resolve()

    def git(root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10, check=False
        )
        if result.returncode != 0:
            raise LifecycleDecisionError("LIFECYCLE_SOURCE_IDENTITY_UNAVAILABLE", result.stderr.strip() or "git identity read failed")
        return result.stdout.strip()

    @server.tool(name="change_lifecycle_decision", annotations=_READ_ONLY)
    def change_lifecycle_decision(
        work_id: str,
        project_path: str,
        source_commit_sha: str,
        source_tree: str,
    ) -> dict[str, Any]:
        """Derive the authoritative normal successor from repository-owned current source identity."""
        try:
            root = Path(project_path).resolve()
            try:
                root.relative_to(boundary)
            except ValueError as exc:
                raise LifecycleDecisionError("LIFECYCLE_PROJECT_PATH_INVALID", "project path escapes configured boundary") from exc
            if git(root, "status", "--porcelain=v1", "--untracked-files=all"):
                raise LifecycleDecisionError("LIFECYCLE_SOURCE_DIRTY", "lifecycle decision requires a clean governed worktree")
            current_sha = git(root, "rev-parse", "--verify", "HEAD").lower()
            current_tree = git(root, "rev-parse", "--verify", "HEAD^{tree}").lower()
            if current_sha != source_commit_sha.lower() or current_tree != source_tree.lower():
                raise LifecycleDecisionError("LIFECYCLE_SOURCE_ASSERTION_STALE", "caller source assertion does not match current repository identity")
            decision = service.decide(
                work_id=work_id,
                source_commit_sha=current_sha,
                source_tree=current_tree,
            )
            if decision.get("state") == "manual_closeout":
                return decision
            branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
            change_id = decision.get("change_id")
            if not isinstance(change_id, str) or not change_id.strip():
                raise LifecycleDecisionError(
                    "LIFECYCLE_CHANGE_ID_UNBOUND",
                    "task handoff has no governed change identity; bind it from the governed scope before lifecycle evaluation",
                    next_action="bind_task_handoff_change",
                )
            if branch != f"change/{change_id}":
                raise LifecycleDecisionError("LIFECYCLE_CHANGE_WORKTREE_MISMATCH", "current branch does not match governed change identity")
            return decision
        except (LifecycleDecisionError, ValueError) as exc:
            code = getattr(exc, "code", "LIFECYCLE_DECISION_INVALID")
            details = getattr(exc, "details", {})
            raise ToolError(json.dumps({
                "code": code,
                "message": "Lifecycle decision request failed.",
                "reason": str(exc),
                "details": dict(details) if isinstance(details, Mapping) else {},
                "retryable": False,
            }, sort_keys=True, separators=(",", ":"))) from exc


__all__ = ["register_lifecycle_decision_tool"]
