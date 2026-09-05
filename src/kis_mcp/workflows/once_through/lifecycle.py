from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .contracts import EvidenceReference, EvidenceState, TaskObligation
from .controller import PromotionStateStore, project_promotion_checkpoint, promotion_operation_id
from .state import OnceThroughStateError, TaskHandoffStore

CONTRACT = "change-lifecycle-decision-v1"
_DISPOSITIONS = frozenset({"required", "allowed", "diagnostic_only", "redundant", "prohibited"})
_SHA = re.compile(r"^[0-9a-f]{40}$")

CANONICAL_EVIDENCE_OWNERS = {
    "development_correctness": "affected_focused_local_verification",
    "architecture_api_security_review": "review_closure",
    "change_governance": "change_workflow_check",
    "full_repository_verification": "github_actions_exact_pr_head",
    "merge_admissibility": "merge_readiness",
    "landed_runtime_correctness": "post_merge_commissioning",
}


class LifecycleDecisionError(ValueError):
    def __init__(self, code: str, message: str, **details: str) -> None:
        self.code = code
        self.details = dict(details)
        super().__init__(f"{code}: {message}")


def _validate_sha(value: str, label: str) -> str:
    normalized = str(value).strip().lower()
    if _SHA.fullmatch(normalized) is None:
        raise LifecycleDecisionError("LIFECYCLE_SOURCE_IDENTITY_INVALID", f"{label} must be a full lowercase SHA")
    return normalized


def _evidence_projection(
    reference: EvidenceReference, observed_inputs: Mapping[str, str]
) -> dict[str, Any]:
    changed = {
        key
        for key, expected in reference.validity_inputs.items()
        if observed_inputs.get(key) != expected
    }
    if reference.kind in {"verification", "review_closed"}:
        expected_tree = reference.validity_inputs.get("tree")
        if not isinstance(expected_tree, str) or _SHA.fullmatch(expected_tree) is None:
            changed.add("tree")
        elif observed_inputs.get("tree") != expected_tree:
            changed.add("tree")
    changed = sorted(changed)
    state = EvidenceState.INVALID if changed else EvidenceState.VALID
    return {
        "evidence_id": reference.evidence_id,
        "kind": reference.kind,
        "state": state.value,
        "reason": (
            "validity inputs changed: " + ", ".join(changed)
            if changed
            else "all declared validity inputs match"
        ),
        "receipt_ref": reference.receipt_ref,
    }


def _disposition(value: str, reason: str | None = None) -> dict[str, str]:
    if value not in _DISPOSITIONS:
        raise ValueError(f"unsupported lifecycle operation disposition: {value}")
    payload = {"disposition": value}
    if reason:
        payload["reason"] = reason
    return payload


def _operation_dispositions(state: str) -> dict[str, dict[str, str]]:
    if state == "implementation_pending" or state == "implementation_evidence_stale":
        return {
            "execute_change_workflow": _disposition("required"),
            "run_local_full_verification": _disposition("diagnostic_only", "CANONICAL_OWNER_GITHUB_EXACT_HEAD"),
            "converge_change_to_done": _disposition("prohibited", "PROMOTION_READY_REQUIRED"),
        }
    if state == "done":
        return {
            "execute_change_workflow": _disposition("redundant", "CHANGE_ALREADY_DONE"),
            "run_local_full_verification": _disposition("redundant", "CHANGE_ALREADY_DONE"),
            "converge_change_to_done": _disposition("redundant", "CHANGE_ALREADY_DONE"),
        }
    return {
        "execute_change_workflow": _disposition("redundant", "PROMOTION_READY_REUSES_IMPLEMENTATION_EVIDENCE"),
        "run_local_full_verification": _disposition("redundant", "CANONICAL_OWNER_GITHUB_EXACT_HEAD"),
        "converge_change_to_done": _disposition("required"),
    }


def _obligation_projection(contract: Any, satisfied: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for obligation in contract.obligations:
        kind = TaskObligation(obligation).value
        if kind in satisfied:
            result[kind] = "satisfied"
        elif kind == TaskObligation.PROVIDER_PROOF.value:
            result[kind] = "pending_after_publication"
        elif TaskObligation(obligation).phase.value in {"documentation", "commissioning", "completion"}:
            result[kind] = "pending_post_merge"
        else:
            result[kind] = "unsatisfied"
    return result


class LifecycleDecisionService:
    def __init__(self, store: TaskHandoffStore, promotion_state: PromotionStateStore) -> None:
        self.store = store
        self.promotion_state = promotion_state

    def decide(
        self,
        *,
        work_id: str,
        source_commit_sha: str,
        source_tree: str,
    ) -> dict[str, Any]:
        source_sha = _validate_sha(source_commit_sha, "source_commit_sha")
        tree = _validate_sha(source_tree, "source_tree")
        contract = self.store.load_contract(work_id)
        assert contract is not None
        observed = {"tree": tree}
        evidence: tuple[EvidenceReference, ...] = self.store.load_evidence(work_id)
        manual_exit = self.store.load_manual_exit(work_id, required=False)
        if manual_exit is not None:
            projected = tuple(_evidence_projection(item, observed) for item in evidence)
            stale = tuple(item for item in projected if item["state"] == EvidenceState.INVALID.value)
            reusable = tuple(item for item in projected if item["state"] == EvidenceState.VALID.value)
            dispositions = {
                "execute_change_workflow": _disposition("prohibited", "ONCE_THROUGH_EXITED"),
                "run_local_full_verification": _disposition("diagnostic_only", "MANUAL_CLOSEOUT"),
                "converge_change_to_done": _disposition("prohibited", "ONCE_THROUGH_EXITED"),
                "manual_governed_change_closeout": _disposition("required"),
            }
            return {
                "schema_version": 1,
                "contract": CONTRACT,
                "state": "manual_closeout",
                "work_id": work_id,
                "change_id": contract.change_id,
                "source_sha": source_sha,
                "source_tree": tree,
                "obligations": _obligation_projection(contract, set()),
                "canonical_evidence_owners": dict(CANONICAL_EVIDENCE_OWNERS),
                "promotion_operation_id": None,
                "controller": None,
                "reusable_evidence": list(reusable),
                "stale_evidence": list(stale),
                "next_required_action": "manual_governed_change_closeout",
                "operation_dispositions": dispositions,
                "lifecycle_blocked": False,
                "manual_closeout": {
                    **manual_exit,
                    "meaning": "once-through progression is disabled; continue with the standard governed repository change workflow",
                    "current_required_step": (
                        "resume_governed_change" if contract.change_id else "create_governed_change"
                    ),
                    "required_sequence": [
                        "create_or_resume_governed_change",
                        "implement_requested_outcome",
                        "change_governance_check",
                        "github_pull_request",
                        "github_actions_exact_pr_head",
                        "merge_readiness",
                        "merge",
                        "refresh_main_and_cleanup",
                    ],
                    "required_gates": [
                        "change_governance",
                        "github_pull_request",
                        "github_actions_exact_pr_head",
                        "merge_readiness",
                    ],
                    "not_ready_for_pr_without_implementation": True,
                    "do_not_reenter_once_through": True,
                },
                "telemetry": {
                    "prevented_operations": ["execute_change_workflow", "converge_change_to_done"],
                    "reused_evidence_ids": [item["evidence_id"] for item in reusable],
                    "stale_evidence_ids": [item["evidence_id"] for item in stale],
                },
            }
        satisfied: set[str] = set()
        promotion = None
        try:
            promotion = self.store.load_promotion(work_id)
        except OnceThroughStateError as exc:
            if exc.code != "PROMOTION_HANDOFF_MISSING":
                raise
        if promotion is not None:
            evidence = promotion.evidence
            satisfied = set(promotion.satisfied_obligations)

        projected = tuple(_evidence_projection(item, observed) for item in evidence)
        stale = tuple(item for item in projected if item["state"] == EvidenceState.INVALID.value)
        reusable = tuple(item for item in projected if item["state"] == EvidenceState.VALID.value)
        reusable_kinds = {item["kind"] for item in reusable}
        implementation_tree_bound = {"verification", "review_closed"}.issubset(reusable_kinds)
        promotion_matches = promotion is not None and promotion.source_commit_sha == source_sha
        controller = None
        operation_id = None
        if promotion_matches and implementation_tree_bound and not stale and promotion is not None:
            handoff = promotion.to_json_dict()
            operation_id = promotion_operation_id(handoff)
            controller = project_promotion_checkpoint(self.promotion_state.load(operation_id))
            state = "done" if controller["state"] == "done" else "promotion_controller"
        elif promotion is not None:
            state = "implementation_evidence_stale"
        else:
            state = "implementation_pending"
        next_action = None if state == "done" else (
            "converge_change_to_done" if state == "promotion_controller" else "execute_change_workflow"
        )
        dispositions = _operation_dispositions(state)
        return {
            "schema_version": 1,
            "contract": CONTRACT,
            "state": state,
            "work_id": work_id,
            "change_id": contract.change_id,
            "source_sha": source_sha,
            "source_tree": tree,
            "obligations": _obligation_projection(contract, satisfied if promotion_matches and not stale else set()),
            "canonical_evidence_owners": dict(CANONICAL_EVIDENCE_OWNERS),
            "promotion_operation_id": operation_id,
            "controller": controller,
            "reusable_evidence": list(reusable),
            "stale_evidence": list(stale),
            "next_required_action": next_action,
            "operation_dispositions": dispositions,
            "lifecycle_blocked": False,
            "telemetry": {
                "prevented_operations": [
                    name for name, item in dispositions.items()
                    if item["disposition"] in {"redundant", "prohibited"}
                ],
                "reused_evidence_ids": [item["evidence_id"] for item in reusable],
                "stale_evidence_ids": [item["evidence_id"] for item in stale],
            },
        }


def apply_operation_failure(
    decision: Mapping[str, Any], *, operation: str, failure: str
) -> dict[str, Any]:
    result = dict(decision)
    dispositions = decision.get("operation_dispositions", {})
    item = dispositions.get(operation, {}) if isinstance(dispositions, Mapping) else {}
    disposition = item.get("disposition") if isinstance(item, Mapping) else None
    next_action = decision.get("next_required_action")
    lifecycle_blocked = bool(
        disposition == "required" or operation == next_action
    )
    if disposition in {"redundant", "diagnostic_only", "allowed", "prohibited"}:
        lifecycle_blocked = False
    result.update({
        "operation_failed": True,
        "failed_operation": operation,
        "failure": str(failure),
        "lifecycle_blocked": lifecycle_blocked,
    })
    return result


__all__ = [
    "CANONICAL_EVIDENCE_OWNERS",
    "CONTRACT",
    "LifecycleDecisionError",
    "LifecycleDecisionService",
    "apply_operation_failure",
]
