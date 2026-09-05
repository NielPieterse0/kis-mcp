from __future__ import annotations

from pathlib import Path

import pytest

from kis_mcp.workflows.once_through.contracts import (
    EvidenceReference,
    EvidenceValidityClass,
    PromotionReadyHandoff,
    TaskHandoffContract,
)
from kis_mcp.workflows.once_through.controller import PromotionStateStore
from kis_mcp.workflows.once_through.lifecycle import (
    LifecycleDecisionService,
    apply_operation_failure,
)
from kis_mcp.workflows.once_through.state import TaskHandoffStore

SHA = "a" * 40
TREE = "b" * 40


def _store(tmp_path: Path, *, promotion: bool = True) -> TaskHandoffStore:
    store = TaskHandoffStore(tmp_path / "once-through")
    contract = TaskHandoffContract(
        project_id="kis-mcp",
        work_id="WORK-650",
        repository="nielpieterse0/kis-mcp",
        requirements=("once-through",),        acceptance_criteria=("no redundant full verify",),
        affected_surfaces=("workflow",),
        obligations=("verification", "review_closed", "provider_proof", "completion"),
        candidate_port=47000,
        source_identity=SHA,
        change_id="621-lifecycle-decision-auto-recovery",
    )
    store.save_contract(contract)
    if not promotion:
        return store
    evidence = (
        EvidenceReference(
            evidence_id="verification",
            kind="verification",
            subject="change",
            validity_class=EvidenceValidityClass.CONTENT_STABLE,
            validity_inputs={"tree": TREE},
            receipt_ref="receipt://verification",
        ),
        EvidenceReference(
            evidence_id="review_closed",
            kind="review_closed",
            subject="change",
            validity_class=EvidenceValidityClass.CONTENT_STABLE,
            validity_inputs={"tree": TREE},
            receipt_ref="receipt://review",
        ),
    )
    store.save_promotion(PromotionReadyHandoff(
        work_id=contract.work_id,
        change_id=contract.change_id or "",
        contract_fingerprint=contract.contract_fingerprint,        source_commit_sha=SHA,
        candidate_identity={},
        execution={"contract": "change-execution-result-v2", "status": "passed"},
        evidence=evidence,
        satisfied_obligations=("verification", "review_closed"),
    ))
    return store


def _service(tmp_path: Path, *, promotion: bool = True) -> LifecycleDecisionService:
    return LifecycleDecisionService(
        _store(tmp_path, promotion=promotion),
        PromotionStateStore(tmp_path / "once-through" / "promotion-controller"),
    )


def test_promotion_ready_points_to_existing_promotion_controller(tmp_path: Path) -> None:
    decision = _service(tmp_path).decide(
        work_id="WORK-650", source_commit_sha=SHA, source_tree=TREE
    )
    assert decision["contract"] == "change-lifecycle-decision-v1"
    assert decision["state"] == "promotion_controller"
    assert decision["source_sha"] == SHA
    assert decision["source_tree"] == TREE
    assert decision["next_required_action"] == "converge_change_to_done"
    assert decision["controller"]["current_stage"] == "refresh_default"
    assert decision["lifecycle_blocked"] is False
    assert decision["canonical_evidence_owners"]["full_repository_verification"] == (
        "github_actions_exact_pr_head"
    )
    assert decision["operation_dispositions"]["run_local_full_verification"] == {
        "disposition": "redundant",
        "reason": "CANONICAL_OWNER_GITHUB_EXACT_HEAD",
    }
    assert {item["kind"] for item in decision["reusable_evidence"]} == {
        "verification", "review_closed"
    }


def test_missing_promotion_requires_existing_change_execution(tmp_path: Path) -> None:
    decision = _service(tmp_path, promotion=False).decide(
        work_id="WORK-650", source_commit_sha=SHA, source_tree=TREE
    )
    assert decision["state"] == "implementation_pending"
    assert decision["next_required_action"] == "execute_change_workflow"
    assert decision["operation_dispositions"]["execute_change_workflow"]["disposition"] == "required"
    assert decision["operation_dispositions"]["run_local_full_verification"]["disposition"] == "diagnostic_only"


def test_manual_exit_bypasses_once_through_progression_without_discarding_evidence(tmp_path: Path) -> None:
    store = TaskHandoffStore(tmp_path / "once-through")
    contract = TaskHandoffContract(
        project_id="commodity", work_id="WORK-316", repository="example/commodity",
        requirements=("preserve work",), acceptance_criteria=("manual closeout",),
        affected_surfaces=("workflow",), obligations=("verification", "review_closed", "provider_proof"),
        candidate_port=47001, source_identity=SHA, change_id=None,
    )
    store.save_contract(contract)
    store.append_evidence(contract.work_id, EvidenceReference(
        evidence_id="verification", kind="verification", subject="change",
        validity_class=EvidenceValidityClass.CONTENT_STABLE,
        validity_inputs={"tree": TREE}, receipt_ref="receipt://verification",
    ))
    store.save_manual_exit(contract.work_id)
    service = LifecycleDecisionService(
        store, PromotionStateStore(tmp_path / "once-through" / "promotion-controller")
    )

    decision = service.decide(work_id=contract.work_id, source_commit_sha=SHA, source_tree=TREE)

    assert decision["state"] == "manual_closeout"
    assert decision["change_id"] is None
    assert decision["next_required_action"] == "manual_pr_ci_closeout"
    assert decision["lifecycle_blocked"] is False
    assert decision["manual_closeout"]["retained_evidence_ids"] == ["verification"]
    assert "github_actions_exact_pr_head" in decision["manual_closeout"]["required_gates"]
    assert decision["operation_dispositions"]["execute_change_workflow"] == {
        "disposition": "prohibited", "reason": "ONCE_THROUGH_EXITED"
    }


def test_tree_change_marks_promotion_evidence_stale(tmp_path: Path) -> None:
    decision = _service(tmp_path).decide(
        work_id="WORK-650", source_commit_sha=SHA, source_tree="c" * 40
    )
    assert decision["state"] == "implementation_evidence_stale"
    assert decision["next_required_action"] == "execute_change_workflow"
    assert {item["kind"] for item in decision["stale_evidence"]} == {
        "verification", "review_closed"
    }
    assert decision["operation_dispositions"]["run_local_full_verification"]["disposition"] == "diagnostic_only"


def test_redundant_operation_failure_does_not_block_lifecycle(tmp_path: Path) -> None:
    decision = _service(tmp_path).decide(
        work_id="WORK-650", source_commit_sha=SHA, source_tree=TREE
    )
    failed = apply_operation_failure(
        decision,
        operation="run_local_full_verification",
        failure="local verifier unavailable: HTTP 502",
    )
    assert failed["operation_failed"] is True
    assert failed["lifecycle_blocked"] is False
    assert failed["next_required_action"] == "converge_change_to_done"
    assert failed["failure"] == "local verifier unavailable: HTTP 502"



def test_incomplete_done_checkpoint_is_rejected(tmp_path: Path) -> None:
    service = _service(tmp_path)
    initial = service.decide(
        work_id="WORK-650", source_commit_sha=SHA, source_tree=TREE
    )
    service.promotion_state.save(
        initial["promotion_operation_id"],
        {"state": "done", "completed": [], "observations": {}},
    )
    with pytest.raises(ValueError, match="done requires every controller stage"):
        service.decide(
            work_id="WORK-650", source_commit_sha=SHA, source_tree=TREE
        )


def test_complete_checkpoint_requires_done_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    initial = service.decide(
        work_id="WORK-650", source_commit_sha=SHA, source_tree=TREE
    )
    completed = [
        "refresh_default", "reconcile_candidate", "create_pull_request",
        "exact_head_actions", "merge_readiness", "merge_exact_head",
        "refresh_landed", "documentation_reconcile", "work_done", "cleanup",
    ]
    service.promotion_state.save(
        initial["promotion_operation_id"],
        {"state": "running", "completed": completed, "current_stage": None},
    )
    with pytest.raises(ValueError, match="requires done state"):
        service.decide(
            work_id="WORK-650", source_commit_sha=SHA, source_tree=TREE
        )
