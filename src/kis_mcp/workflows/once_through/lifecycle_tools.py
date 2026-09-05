from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .lifecycle import LifecycleDecisionError, LifecycleDecisionService
from .state import OnceThroughStateError
from .recovery import (
    EvidenceApplicability,
    EvidenceApplicabilityRecord,
    RecoveryState,
    WorkflowCheckpoint,
    abort_state,
    recovery_state_to_json,
    revalidate_retained_evidence,
    rewind_state,
)

_READ_ONLY = {
    "read_only_hint": True,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": False,
}
_MUTATION = {
    "read_only_hint": False,
    "destructive_hint": False,
    "idempotent_hint": False,
    "open_world_hint": False,
}


def _phase_for_decision(state: str) -> str:
    if state in {"review_pending", "review_evidence_stale"}:
        return "review"
    if state in {"candidate_pending", "candidate_evidence_stale", "promotion_ready"}:
        return "candidate"
    if state in {"pull_request_pending", "ci_pending", "ci_passed", "merge_ready"}:
        return "pull_request"
    if state in {"merged", "documentation_pending", "commissioning_pending", "complete"}:
        return "post_merge"
    return "implementation"


def _default_recovery_state(service: LifecycleDecisionService, work_id: str, active_phase: str) -> RecoveryState:
    checkpoints = (
        WorkflowCheckpoint("implementation", "implementation", 0),
        WorkflowCheckpoint("review", "review", 1),
        WorkflowCheckpoint("candidate", "candidate", 2),
        WorkflowCheckpoint("pull_request", "pull_request", 3),
        WorkflowCheckpoint("post_merge", "post_merge", 4, irreversible=True),
    )
    by_phase = {item.phase: item.checkpoint_id for item in checkpoints}
    active = by_phase.get(active_phase, "implementation")
    evidence = tuple(
        EvidenceApplicabilityRecord(item.evidence_id, EvidenceApplicability.CURRENT, "lineage-0")
        for item in service.store.load_evidence(work_id)
    )
    return RecoveryState("lineage-0", active, checkpoints, evidence)


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
            recovery = service.store.load_recovery(work_id, required=False)
            if recovery is None:
                recovery = _default_recovery_state(
                    service,
                    work_id,
                    _phase_for_decision(str(decision.get("state", "implementation_pending"))),
                )
            decision["recovery"] = {
                **recovery_state_to_json(recovery),
                "available_rewinds": list(recovery.available_rewinds()),
                "supported_actions": ["inspect", "rewind", "revalidate", "resume", "abort"],
            }
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

    @server.tool(name="once_through_recovery", annotations=_MUTATION)
    def once_through_recovery(
        work_id: str,
        action: str,
        target_checkpoint: str | None = None,
        observed_inputs: dict[str, str] | None = None,
        replacements: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Inspect or mutate governed once-through recovery state without deleting retained evidence."""
        try:
            state = service.store.load_recovery(work_id, required=False)
            if state is None:
                state = _default_recovery_state(service, work_id, "implementation")
            if action == "inspect":
                pass
            elif action == "rewind":
                if not target_checkpoint:
                    raise ValueError("RECOVERY_REWIND_TARGET_REQUIRED")

                def apply_rewind(current: RecoveryState) -> RecoveryState:
                    references = {item.evidence_id: item for item in service.store.load_evidence(work_id)}
                    return rewind_state(
                        current,
                        target_checkpoint,
                        next_lineage_id=f"lineage-{uuid4().hex}",
                        references=references,
                    )

                state = service.store.update_recovery(work_id, state, apply_rewind)
            elif action == "revalidate":

                def apply_revalidation(current: RecoveryState) -> RecoveryState:
                    references = {item.evidence_id: item for item in service.store.load_evidence(work_id)}
                    return revalidate_retained_evidence(
                        current,
                        references=references,
                        observed_inputs=observed_inputs or {},
                        replacements=replacements,
                    )

                state = service.store.update_recovery(work_id, state, apply_revalidation)
            elif action == "abort":
                state = service.store.update_recovery(work_id, state, abort_state)
            elif action == "resume":
                state = service.store.update_recovery(
                    work_id,
                    state,
                    lambda current: RecoveryState(
                        current.lineage_id,
                        current.active_checkpoint,
                        current.checkpoints,
                        current.evidence,
                        False,
                    ),
                )
            else:
                raise ValueError(f"RECOVERY_ACTION_UNSUPPORTED: {action}")
            return {
                **recovery_state_to_json(state),
                "available_rewinds": list(state.available_rewinds()),
                "retained_evidence_count": len(state.evidence),
            }
        except (OnceThroughStateError, ValueError) as exc:
            code = getattr(exc, "code", "RECOVERY_OPERATION_INVALID")
            raise ToolError(json.dumps({
                "code": code,
                "message": "Once-through recovery request failed.",
                "reason": str(exc),
                "retryable": False,
            }, sort_keys=True, separators=(",", ":"))) from exc


__all__ = ["register_lifecycle_decision_tool"]
