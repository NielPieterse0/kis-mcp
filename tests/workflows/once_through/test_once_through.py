from __future__ import annotations

import asyncio
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from kis_mcp.workflows.once_through import (
    EvidenceReference,
    EvidenceState,
    EvidenceValidityClass,
    PromotionController,
    PromotionStateStore,
    TaskHandoffContract,
    TaskHandoffStore,
    assert_candidate_port_available,
    derive_promotion_ready,
    resolve_evidence,
)
from kis_mcp.workflows.once_through.activation import WorkActivationCoordinator
from kis_mcp.state import resolve_runtime_state_path
from kis_mcp.workflows.once_through.contracts import fingerprint
from kis_mcp.workflows.once_through.tools import (
    _governed_source_binding,
    _post_land_restart_receipt,
    _owned_candidate_stop_pid,
    _promotion_reference,
)


def _contract(port: int, work_id: str = "WORK-572") -> TaskHandoffContract:
    return TaskHandoffContract(
        project_id="kis-mcp", work_id=work_id, repository="NielPieterse0/kis-mcp",
        requirements=("implement",), acceptance_criteria=("passes",),
        affected_surfaces=("mcp",),
        obligations=("verification", "review_closed", "live_candidate_verification"),
        candidate_port=port, source_identity="tree:abc", change_id="261-test",
    )


def _evidence(kind: str, **inputs: str) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=f"ev-{kind}", kind=kind, subject="tree:abc",
        validity_class=EvidenceValidityClass.CONTENT_STABLE,
        validity_inputs=inputs, receipt_ref=f"receipt:{kind}",
    )


def test_candidate_ports_are_immutable_and_never_reused(tmp_path: Path) -> None:
    store = TaskHandoffStore(tmp_path)
    first = store.candidate_port("WORK-1")
    second = store.candidate_port("WORK-2")
    assert first != second
    assert store.candidate_port("WORK-1") == first


def test_materialize_contract_is_atomic_and_idempotent_under_parallel_activation(tmp_path: Path) -> None:
    store = TaskHandoffStore(tmp_path)

    def materialize() -> TaskHandoffContract:
        return store.materialize_contract(
            project_id="kis-mcp", work_id="WORK-586", repository="NielPieterse0/kis-mcp",
            requirements=("automatic handoff",), acceptance_criteria=("stable",),
            affected_surfaces=("mcp", "work_management"),
            obligations=("verification", "review_closed", "live_candidate_verification"),
            source_identity="github-issue:NielPieterse0/kis-mcp#586",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        contracts = tuple(executor.map(lambda _: materialize(), range(16)))

    assert len({item.contract_fingerprint for item in contracts}) == 1
    assert len({item.candidate_port for item in contracts}) == 1
    assert store.load_contract("WORK-586") == contracts[0]
    assert store.candidate_port("WORK-586") == contracts[0].candidate_port


def test_evidence_lineage_extends_immutably_by_reference(tmp_path: Path) -> None:
    store = TaskHandoffStore(tmp_path)
    contract = store.materialize_contract(
        project_id="kis-mcp", work_id="WORK-586", repository="NielPieterse0/kis-mcp",
        requirements=("automatic handoff",), acceptance_criteria=("stable",),
        affected_surfaces=("repository",), obligations=("verification", "review_closed"),
        source_identity="github-issue:NielPieterse0/kis-mcp#586",
    )
    reference = EvidenceReference(
        evidence_id="verify-586", kind="verification", subject=contract.source_identity,
        validity_class=EvidenceValidityClass.CONTENT_STABLE,
        validity_inputs={"tree": "a" * 40}, receipt_ref="change-execution:586",
    )

    assert store.append_evidence(contract.work_id, reference) == (reference,)
    assert store.append_evidence(contract.work_id, reference) == (reference,)
    with pytest.raises(RuntimeError, match="EVIDENCE_ID_IMMUTABLE"):
        store.append_evidence(
            contract.work_id,
            EvidenceReference(
                evidence_id="verify-586", kind="verification", subject=contract.source_identity,
                validity_class=EvidenceValidityClass.CONTENT_STABLE,
                validity_inputs={"tree": "b" * 40}, receipt_ref="change-execution:changed",
            ),
        )


def test_work_activation_materializes_issue_contract_and_reuses_it(tmp_path: Path) -> None:
    store = TaskHandoffStore(tmp_path)

    async def load_issue(owner: str, repo: str, issue_number: int) -> dict[str, object]:
        assert (owner, repo, issue_number) == ("NielPieterse0", "kis-mcp", 586)
        return {
            "title": "Automatic Work handoff",
            "body": (
                "## Outcome\nAutomate the handoff.\n\n"
                "## Scope\n- Persist evidence lineage.\n- Manage MCP candidate lifecycle.\n\n"
                "## Acceptance criteria\n- Re-entry is idempotent.\n"
            ),
        }

    coordinator = WorkActivationCoordinator(store, load_issue)
    first = asyncio.run(coordinator.materialize("kis-mcp", "NielPieterse0/kis-mcp", 586))
    second = asyncio.run(coordinator.materialize("kis-mcp", "NielPieterse0/kis-mcp", 586))

    assert first == second
    assert first["work_id"] == "WORK-586"
    assert first["source_identity"] == "github-issue:NielPieterse0/kis-mcp#586"
    assert first["obligations"] == ["verification", "review_closed", "live_candidate_verification"]


def test_promotion_receipts_extend_canonical_evidence_lineage() -> None:
    exact = _promotion_reference(
        "exact_head_actions", work_id="WORK-586", subject="github-issue:repo#586",
        result={"status": "passed", "head_sha": "a" * 40, "reference": "github-actions:77"},
        observations={},
    )
    landed = _promotion_reference(
        "documentation_reconcile", work_id="WORK-586", subject="github-issue:repo#586",
        result={"status": "satisfied", "completion_revision": "b" * 40},
        observations={"refresh_landed": {"landed_sha": "b" * 40}},
    )

    assert exact is not None and exact.validity_class is EvidenceValidityClass.PROVIDER_EXACT_HEAD
    assert exact.receipt_ref == "github-actions:77"
    assert landed is not None and landed.validity_class is EvidenceValidityClass.POST_MERGE
    assert landed.validity_inputs == {"landed": "b" * 40}


def test_exact_candidate_cleanup_requires_owner_and_durable_live_proof() -> None:
    contract = _contract(46000, work_id="WORK-586")
    receipt = {"pid": 32123, "server_instance_id": "candidate-586"}
    identity = {
        "work_id": contract.work_id,
        "contract_fingerprint": contract.contract_fingerprint,
        "source_identity": contract.source_identity,
        "server_instance_id": "candidate-586",
        "pid": 32123,
    }
    live = EvidenceReference(
        evidence_id="live-586", kind="live_candidate_verification",
        subject=contract.source_identity,
        validity_class=EvidenceValidityClass.RUNTIME_SENSITIVE,
        validity_inputs={
            "tree": "a" * 40, "runtime": "candidate-586",
            "server_instance_id": "candidate-586",
        },
        receipt_ref="candidate:WORK-586:candidate-586",
    )

    assert _owned_candidate_stop_pid(contract, receipt, identity, (live,)) == (32123, live)
    with pytest.raises(RuntimeError, match="CANDIDATE_OWNER_MISMATCH"):
        _owned_candidate_stop_pid(contract, receipt, {**identity, "pid": 99999}, (live,))
    with pytest.raises(RuntimeError, match="CANDIDATE_EVIDENCE_NOT_DURABLE"):
        _owned_candidate_stop_pid(contract, receipt, identity, ())


def test_unexpected_candidate_port_occupant_fails_closed() -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    try:
        with pytest.raises(RuntimeError, match="CANDIDATE_PORT_OCCUPIED"):
            assert_candidate_port_available(port)
    finally:
        listener.close()


def test_evidence_invalidation_is_selective() -> None:
    refs = (
        _evidence("verification", tree="t1"),
        EvidenceReference(
            "ev-base", "integration", "tree:abc", EvidenceValidityClass.BASE_SENSITIVE,
            {"tree": "t1", "base": "b1"}, "receipt:integration",
        ),
    )
    results = resolve_evidence(refs, required_kinds=("verification", "integration"), observed_inputs={"tree": "t1", "base": "b2"})
    assert [item.state for item in results] == [EvidenceState.VALID, EvidenceState.INVALID]
    assert "base" in results[1].reason


def test_promotion_ready_requires_all_declared_evidence() -> None:
    contract = _contract(46000)
    refs = tuple(
        EvidenceReference(
            evidence_id=f"ev-{kind}", kind=kind, subject="tree:abc",
            validity_class=EvidenceValidityClass.CONTENT_STABLE,
            validity_inputs={
                "tree": "t1",
                **({
                    "source_commit": "a" * 40,
                    "server_instance_id": "candidate-1",
                    "contract_fingerprint": contract.contract_fingerprint,
                } if kind == "live_candidate_verification" else {}),
            },
            receipt_ref=f"receipt:{kind}",
        )
        for kind in contract.obligations
    )
    handoff = derive_promotion_ready(
        contract, source_commit_sha="a" * 40,
        execution={"contract": "change-execution-result-v2", "status": "passed"},
        evidence=refs, observed_inputs={
            "tree": "t1", "source_commit": "a" * 40,
            "server_instance_id": "candidate-1",
            "contract_fingerprint": contract.contract_fingerprint,
        },
        candidate_identity={
            "work_id": contract.work_id,
            "contract_fingerprint": contract.contract_fingerprint,
            "source_identity": contract.source_identity,
            "server_instance_id": "candidate-1",
        },
    )
    assert handoff.status == "promotion_ready"
    assert handoff.pending_obligations == ()


def _controller_handoff() -> dict[str, object]:
    return {
        "status": "promotion_ready",
        "work_id": "WORK-1",
        "change_id": "265-controller-test",
        "source_commit_sha": "a" * 40,
    }


def _controller_stage_result(stage: str) -> dict[str, object]:
    results: dict[str, dict[str, object]] = {
        "refresh_default": {"status": "satisfied", "github_default_sha": "b" * 40},
        "reconcile_candidate": {"status": "satisfied", "commit_sha": "c" * 40},
        "create_pull_request": {"status": "satisfied", "pull_number": 7, "head_sha": "c" * 40},
        "exact_head_actions": {"status": "passed", "run_ids": [71], "reference": "github-actions:71"},
        "merge_readiness": {"status": "satisfied", "ready": True},
        "merge_exact_head": {"status": "satisfied", "merge_commit_sha": "d" * 40},
        "refresh_landed": {"status": "satisfied", "landed_sha": "e" * 40},
        "documentation_reconcile": {
            "status": "satisfied", "completion_revision": "e" * 40,
            "event": {"event_id": "docs-controller", "completion_revision": "e" * 40},
            "record": {"record_id": "SPEC-1"},
        },
        "work_done": {
            "status": "satisfied", "record": {"record_id": "SPEC-1"},
            "work_completion": {"mode": "apply"},
            "source_close_required": True, "source_close_applied": True,
        },
        "cleanup": {"status": "satisfied", "cleaned": True},
    }
    return {**results[stage], "stage": stage}


class _PromotionInvoker:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, stage: str, handoff: dict[str, object], observations: dict[str, object]) -> dict[str, object]:
        self.calls.append(stage)
        return _controller_stage_result(stage)


class _ObservationInvoker:
    def __init__(self) -> None:
        self.received: list[tuple[str, dict[str, object]]] = []

    async def __call__(self, stage: str, handoff: dict[str, object], observations: dict[str, object]) -> dict[str, object]:
        self.received.append((stage, dict(observations)))
        return _controller_stage_result(stage)


def test_controller_passes_persisted_observations_to_later_stages(tmp_path: Path) -> None:
    invoker = _ObservationInvoker()
    handoff = _controller_handoff()
    store = PromotionStateStore(tmp_path)
    store.save("promotion-observations", {
        "handoff_fingerprint": fingerprint(handoff),
        "completed": ["refresh_default"],
        "observations": {"refresh_default": {"status": "satisfied", "github_default_sha": "a" * 40}},
    })

    result = asyncio.run(PromotionController(invoker, store).converge(
        operation_id="promotion-observations",
        promotion_handoff=handoff,
    ))

    assert result.state == "done"
    first_stage, first_observations = invoker.received[0]
    assert first_stage == "reconcile_candidate"
    assert first_observations["refresh_default"] == {
        "status": "satisfied", "github_default_sha": "a" * 40
    }
    create_pr = next(observations for stage, observations in invoker.received if stage == "create_pull_request")
    assert create_pr["reconcile_candidate"]["stage"] == "reconcile_candidate"


def test_controller_resumes_without_repeating_satisfied_stages(tmp_path: Path) -> None:
    invoker = _PromotionInvoker()
    handoff = _controller_handoff()
    store = PromotionStateStore(tmp_path)
    store.save("promotion-1", {
        "handoff_fingerprint": fingerprint(handoff),
        "completed": ["refresh_default", "reconcile_candidate"],
        "observations": {
            "refresh_default": _controller_stage_result("refresh_default"),
            "reconcile_candidate": _controller_stage_result("reconcile_candidate"),
        },
    })
    result = asyncio.run(PromotionController(invoker, store).converge(
        operation_id="promotion-1",
        promotion_handoff=handoff,
    ))
    assert result.state == "done"
    assert "refresh_default" not in invoker.calls
    assert "reconcile_candidate" not in invoker.calls
    assert invoker.calls[0] == "create_pull_request"


def test_controller_rejects_non_prefix_resume_state(tmp_path: Path) -> None:
    invoker = _PromotionInvoker()
    handoff = {"status": "promotion_ready"}
    store = PromotionStateStore(tmp_path)
    store.save("promotion-invalid", {
        "handoff_fingerprint": fingerprint(handoff),
        "completed": ["refresh_default", "create_pull_request"],
        "observations": {},
    })
    with pytest.raises(ValueError, match="ordered prefix"):
        asyncio.run(PromotionController(invoker, store).converge(
            operation_id="promotion-invalid",
            promotion_handoff=handoff,
        ))


def test_controller_persists_and_reuses_completed_prefix(tmp_path: Path) -> None:
    invoker = _PromotionInvoker()
    store = PromotionStateStore(tmp_path)
    handoff = _controller_handoff()
    first = asyncio.run(PromotionController(invoker, store).converge(
        operation_id="promotion-persisted",
        promotion_handoff=handoff,
    ))
    assert first.state == "done"
    first_calls = tuple(invoker.calls)
    second = asyncio.run(PromotionController(invoker, store).converge(
        operation_id="promotion-persisted",
        promotion_handoff=handoff,
    ))
    assert second.state == "done"
    assert tuple(invoker.calls) == first_calls


def test_work_id_paths_reject_lossy_aliases(tmp_path: Path) -> None:
    store = TaskHandoffStore(tmp_path)
    with pytest.raises(ValueError, match="canonical"):
        store.contract_path("WORK/586")
    assert store.contract_path("WORK-586").name == "WORK-586.json"


def test_governed_source_binding_requires_exact_work_and_repository(tmp_path: Path) -> None:
    contract = _contract(46000, work_id="WORK-586")
    root = tmp_path / ".work" / "worktrees" / "264-security-binding"
    (root / "src" / "kis_mcp").mkdir(parents=True)
    change = root / ".work" / "changes" / root.name
    change.mkdir(parents=True)
    scope = {
        "change_id": root.name,
        "work_management": {
            "record_id": "WORK-586",
            "source_repository": contract.repository,
        },
    }
    (change / "scope.json").write_text(json.dumps(scope), encoding="utf-8")
    source_root, change_id, observed = _governed_source_binding(contract, str(root))
    assert source_root == root.resolve()
    assert change_id == root.name
    assert observed["work_management"]["record_id"] == contract.work_id


class _TerminalPromotionInvoker:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, stage: str, handoff: dict[str, object], observations: dict[str, object]) -> dict[str, object]:
        self.calls.append(stage)
        results: dict[str, dict[str, object]] = {
            "refresh_default": {"status": "applied", "github_default_sha": "b" * 40},
            "reconcile_candidate": {"status": "applied", "commit_sha": "c" * 40},
            "create_pull_request": {"status": "applied", "pull_number": 77, "head_sha": "c" * 40},
            "exact_head_actions": {"status": "passed", "run_ids": [9001], "reference": "github-actions:9001"},
            "merge_readiness": {"status": "satisfied", "ready": True},
            "merge_exact_head": {"status": "applied", "merge_commit_sha": "d" * 40},
            "refresh_landed": {"status": "applied", "landed_sha": "e" * 40, "merge_commit_sha": "d" * 40},
            "documentation_reconcile": {
                "status": "satisfied", "completion_revision": "e" * 40,
                "phase": "post_merge_complete",
                "event": {"event_id": "docs-265", "completion_revision": "e" * 40},
                "record": {"record_id": "SPEC-592"},
            },
            "work_done": {
                "status": "applied", "source_close_required": True,
                "source_close_applied": True,
                "source_close_reconciled_after_error": False,
                "record": {"record_id": "SPEC-592"},
                "work_completion": {"mode": "apply"},
            },
            "cleanup": {
                "status": "applied", "cleaned": True,
                "post_land_restart": {
                    "schema_version": 1, "state": "launching",
                    "landed_sha": "e" * 40, "launched_sha": "e" * 40,
                },
            },
        }
        return results[stage]


def test_controller_persists_terminal_delivery_receipt_and_done_replay_is_noop(tmp_path: Path) -> None:
    invoker = _TerminalPromotionInvoker()
    store = PromotionStateStore(tmp_path)
    handoff = {
        "status": "promotion_ready", "work_id": "WORK-592",
        "change_id": "265-test", "source_commit_sha": "a" * 40,
    }
    first = asyncio.run(PromotionController(invoker, store).converge(
        operation_id="promotion-terminal", promotion_handoff=handoff,
    ))
    receipt = first.terminal_receipt
    assert receipt is not None
    assert receipt["contract"] == "promotion-terminal-receipt-v1"
    assert receipt["work_id"] == "WORK-592"
    assert receipt["change_id"] == "265-test"
    assert receipt["source_commit_sha"] == "a" * 40
    assert receipt["pull_number"] == 77
    assert receipt["head_sha"] == "c" * 40
    assert receipt["actions_run_ids"] == [9001]
    assert receipt["merge_commit_sha"] == "d" * 40
    assert receipt["landed_sha"] == "e" * 40
    assert receipt["documentation_completion_revision"] == "e" * 40
    assert receipt["typed_record_id"] == "SPEC-592"
    assert receipt["documentation_event"]["event_id"] == "docs-265"
    assert receipt["source_close"] == {
        "required": True,
        "applied": True,
        "reconciled_after_error": False,
    }
    assert receipt["post_land_restart"]["launched_sha"] == "e" * 40
    assert receipt["cleanup"]["cleaned"] is True
    checkpoint = store.load("promotion-terminal")
    assert checkpoint is not None
    assert checkpoint["terminal_receipt"] == receipt

    calls = tuple(invoker.calls)
    second = asyncio.run(PromotionController(invoker, store).converge(
        operation_id="promotion-terminal", promotion_handoff=handoff,
    ))
    assert second.state == "done"
    assert second.terminal_receipt == receipt
    assert tuple(invoker.calls) == calls


def test_post_land_restart_receipt_requires_exact_landed_and_launched_sha(tmp_path: Path) -> None:
    landed = "e" * 40
    receipt_root = resolve_runtime_state_path(
        tmp_path, runtime_instance_id="kis-dev", state_key="post-land-restart"
    )
    receipt_root.mkdir(parents=True)
    (receipt_root / "latest.json").write_text(
        json.dumps({
            "schema_version": 1,
            "state": "launching",
            "landed_sha": landed,
            "launched_sha": landed,
            "worker_pid": 1234,
            "detail": "",
            "updated_utc": "2026-08-29T11:15:33Z",
        }),
        encoding="utf-8",
    )

    receipt = _post_land_restart_receipt(tmp_path, landed)
    assert receipt["landed_sha"] == landed
    assert receipt["launched_sha"] == landed

    with pytest.raises(RuntimeError, match="POST_LAND_RESTART_RECEIPT_LANDED_MISMATCH"):
        _post_land_restart_receipt(tmp_path, "f" * 40)
