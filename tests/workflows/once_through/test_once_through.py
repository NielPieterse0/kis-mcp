from __future__ import annotations

import asyncio
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastmcp import FastMCP

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
from kis_mcp.workflows.once_through.candidate_runtime import _runtime_instance_id
from kis_mcp.state import resolve_runtime_state_path
from kis_mcp.workflows.once_through.contracts import (
    LEGACY_SCHEMA_VERSION,
    ObligationPhase,
    PromotionReadyHandoff,
    TaskObligation,
    fingerprint,
)
from kis_mcp.workflows.once_through.evidence import (
    required_obligations,
    validate_effect_safe_scenarios,
    validate_mcp_tool_schemas,
)
from kis_mcp.workflows.once_through.tools import (
    _governed_source_binding,
    register_once_through_tools,
    _record_promotion_operation,
    _terminal_audit,
    _terminate_launched_process,
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


def test_candidate_runtime_instance_id_is_state_namespace_safe() -> None:
    first = _runtime_instance_id("WORK-594")
    assert first.startswith("candidate-work-594-")
    assert first == _runtime_instance_id("WORK-594")
    assert _runtime_instance_id("WORK:A") != _runtime_instance_id("WORK/A")
    assert _runtime_instance_id("WORK:A") != _runtime_instance_id("WORK-A")


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
    assert second.terminal_receipt is not None
    assert second.terminal_receipt["landed_sha"] == receipt["landed_sha"]
    assert second.terminal_receipt["merge_commit_sha"] == receipt["merge_commit_sha"]
    assert second.terminal_receipt["telemetry"]["replay_count"] == 1
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


class _AuditedTerminalInvoker(_TerminalPromotionInvoker):
    async def __call__(self, stage: str, handoff: dict[str, object], observations: dict[str, object]) -> dict[str, object]:
        result = await super().__call__(stage, handoff, observations)
        result["_audit"] = {
            "provider_reads": 1 if stage in {"refresh_default", "exact_head_actions", "refresh_landed"} else 0,
            "provider_mutations": 1 if stage in {"reconcile_candidate", "create_pull_request", "merge_exact_head"} else 0,
            "list_pages_scanned": 1 if stage == "exact_head_actions" else 0,
            "tool_calls": 1,
            "verification_invocations": 0,
            "review_invocations": 0,
            "duplicate_proof_attempts": 0,
            "proof_read_fingerprints": [f"proof-{stage}"] if stage == "work_done" else [],
            "operation_counts": {stage: 1},
        }
        return result


def test_terminal_receipt_carries_durable_metrics_and_generated_closeout(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    store = PromotionStateStore(state_root / "once-through" / "promotion-controller")
    handoff = {
        "status": "promotion_ready", "work_id": "WORK-592",
        "change_id": "265-test", "source_commit_sha": "a" * 40,
    }
    result = asyncio.run(PromotionController(_AuditedTerminalInvoker(), store).converge(
        operation_id="promotion-audited", promotion_handoff=handoff,
    ))
    receipt = result.terminal_receipt
    assert receipt is not None
    assert receipt["telemetry"]["provider_reads"] == 3
    assert receipt["telemetry"]["provider_mutations"] == 3
    assert receipt["telemetry"]["list_pages_scanned"] == 1
    assert receipt["telemetry"]["proof_read_fingerprints"] == ["proof-work_done"]
    assert receipt["closeout_projection"]["authority"] == "terminal_receipt"
    assert receipt["closeout_projection"]["tracked_change_record_role"] == "historical_pre_merge"
    assert all(receipt["closeout_projection"]["checklist"].values())
    assert store.recent_terminal_receipts(1)[0]["operation_id"] == "promotion-audited"


def test_workflow_terminal_audit_returns_one_bounded_self_contained_view(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    store = PromotionStateStore(state_root / "once-through" / "promotion-controller")
    handoff = {
        "status": "promotion_ready", "work_id": "WORK-592",
        "change_id": "265-test", "source_commit_sha": "a" * 40,
    }
    asyncio.run(PromotionController(_AuditedTerminalInvoker(), store).converge(
        operation_id="promotion-audit-tool", promotion_handoff=handoff,
    ))
    server = FastMCP("audit-test")
    register_once_through_tools(server, state_root)

    result = asyncio.run(server.call_tool(
        "workflow_terminal_audit", {"limit": 1}
    )).structured_content

    assert result is not None
    assert result["contract"] == "workflow-terminal-audit-v1"
    assert result["count"] == 1
    item = result["items"][0]
    assert item["identities"]["source_commit_sha"] == "a" * 40
    assert item["identities"]["actions_run_ids"] == [9001]
    assert item["delivery"]["post_land_restart"]["launched_sha"] == "e" * 40
    assert item["closeout"]["tracked_change_record_role"] == "historical_pre_merge"
    assert item["complexity_budget"]["meaningful_transitions"] == 8


def test_terminal_audit_distinguishes_distinct_reviews_from_duplicates() -> None:
    receipt = {
        "work_id": "WORK-594", "typed_record_id": "SPEC-594", "change_id": "267-test",
        "source_commit_sha": "a" * 40, "pull_number": 1, "head_sha": "b" * 40,
        "actions_run_ids": [2], "merge_commit_sha": "c" * 40, "landed_sha": "d" * 40,
        "documentation_completion_revision": "d" * 40, "work_completion": {"mode": "apply"},
        "source_close": {"required": True, "applied": True}, "cleanup": {"status": "applied"},
        "telemetry": {"review_invocations": 3, "duplicate_review_attempts": 0, "promotion_review_invocations": 0},
    }
    clean = _terminal_audit(receipt)
    assert "duplicate_review" not in clean["flags"]
    receipt["telemetry"] = {"review_invocations": 3, "duplicate_review_attempts": 1, "promotion_review_invocations": 1}
    flagged = _terminal_audit(receipt)
    assert "duplicate_review" in flagged["flags"]
    assert "promotion_review_ownership_regression" in flagged["flags"]

def test_terminal_audit_flags_malformed_telemetry_without_failing() -> None:
    receipt = {
        "work_id": "WORK-594", "typed_record_id": "SPEC-594", "change_id": "267-test",
        "source_commit_sha": "a" * 40, "pull_number": 1, "head_sha": "b" * 40,
        "actions_run_ids": [2], "merge_commit_sha": "c" * 40, "landed_sha": "d" * 40,
        "documentation_completion_revision": "d" * 40, "work_completion": {"mode": "apply"},
        "source_close": {"required": True, "applied": True}, "cleanup": {"status": "applied"},
        "telemetry": {"provider_reads": None, "provider_mutations": "bad", "duplicate_review_attempts": True},
    }
    audit = _terminal_audit(receipt)
    assert audit["status"] == "attention"
    assert "invalid_telemetry" in audit["flags"]
    assert set(audit["invalid_telemetry_fields"]) >= {
        "provider_reads", "provider_mutations", "duplicate_review_attempts"
    }
    assert audit["complexity_budget"]["provider_calls"] is None


def test_done_replay_does_not_change_terminal_recency_order(tmp_path: Path) -> None:
    store = PromotionStateStore(tmp_path)
    invoker = _TerminalPromotionInvoker()
    handoff_a = {"status": "promotion_ready", "work_id": "WORK-592", "change_id": "265-a", "source_commit_sha": "a" * 40}
    handoff_b = {"status": "promotion_ready", "work_id": "WORK-593", "change_id": "266-b", "source_commit_sha": "b" * 40}
    first = asyncio.run(PromotionController(invoker, store).converge(operation_id="promotion-a", promotion_handoff=handoff_a))
    second = asyncio.run(PromotionController(invoker, store).converge(operation_id="promotion-b", promotion_handoff=handoff_b))
    assert first.terminal_receipt is not None and second.terminal_receipt is not None
    assert first.terminal_receipt["completed_at_ns"] < second.terminal_receipt["completed_at_ns"]
    asyncio.run(PromotionController(invoker, store).converge(operation_id="promotion-a", promotion_handoff=handoff_a))
    recent = store.recent_terminal_receipts(2)
    assert [item["operation_id"] for item in recent] == ["promotion-b", "promotion-a"]

def test_terminal_audit_does_not_treat_missing_telemetry_as_measured_zero() -> None:
    receipt = {
        "work_id": "WORK-594", "typed_record_id": "SPEC-594", "change_id": "267-test",
        "source_commit_sha": "a" * 40, "pull_number": 1, "head_sha": "b" * 40,
        "actions_run_ids": [2], "merge_commit_sha": "c" * 40, "landed_sha": "d" * 40,
        "documentation_completion_revision": "d" * 40, "work_completion": {"mode": "apply"},
        "source_close": {"required": True, "applied": True}, "cleanup": {"status": "applied"},
    }
    audit = _terminal_audit(receipt)
    assert "invalid_telemetry" in audit["flags"]
    assert audit["invalid_telemetry_fields"] == ["telemetry"]
    assert audit["complexity_budget"]["provider_calls"] is None
    assert audit["complexity_budget"]["meets_simplification_target"] is False

def test_promotion_operation_metrics_detect_duplicate_verification_and_proof_reads() -> None:
    metrics = {
        "provider_reads": 0, "provider_mutations": 0, "list_pages_scanned": 0,
        "tool_calls": 0, "verification_invocations": 0, "review_invocations": 0,
        "duplicate_verification_attempts": 0, "promotion_review_invocations": 0,
        "duplicate_proof_attempts": 0, "operation_counts": {},
    }
    seen: set[str] = set()
    for _ in range(2):
        _record_promotion_operation(
            metrics, stage="merge_readiness", operation="run_verification",
            arguments={"source": "commit"}, proof_reads_seen=seen,
        )
        _record_promotion_operation(
            metrics, stage="work_done", operation="github_issue_read",
            arguments={"method": "get", "issue_number": 594}, proof_reads_seen=seen,
        )
    assert metrics["verification_invocations"] == 2
    assert metrics["duplicate_verification_attempts"] == 1
    assert metrics["duplicate_proof_attempts"] == 1

    established = dict(metrics)
    established.update({"verification_invocations": 0, "duplicate_verification_attempts": 0, "operation_counts": {}})
    _record_promotion_operation(
        established, stage="merge_readiness", operation="run_verification",
        arguments={"source": "commit"}, proof_reads_seen=set(),
        implementation_verification_established=True,
    )
    assert established["duplicate_verification_attempts"] == 1

def test_persisted_proof_fingerprint_detects_duplicate_after_retry() -> None:
    first = {
        "provider_reads": 0, "provider_mutations": 0, "list_pages_scanned": 0,
        "tool_calls": 0, "verification_invocations": 0, "review_invocations": 0,
        "duplicate_verification_attempts": 0, "promotion_review_invocations": 0,
        "duplicate_proof_attempts": 0, "operation_counts": {},
    }
    seen: set[str] = set()
    arguments = {"method": "get", "issue_number": 594}
    _record_promotion_operation(
        first, stage="work_done", operation="github_issue_read",
        arguments=arguments, proof_reads_seen=seen,
    )
    retry = {**first, "provider_reads": 0, "tool_calls": 0, "duplicate_proof_attempts": 0, "operation_counts": {}}
    restored = set(seen)
    _record_promotion_operation(
        retry, stage="work_done", operation="github_issue_read",
        arguments=arguments, proof_reads_seen=restored,
    )
    assert retry["duplicate_proof_attempts"] == 1

def test_terminal_audit_flags_malformed_identity_and_delivery() -> None:
    receipt = {
        "work_id": "WORK-594", "typed_record_id": "SPEC-594", "change_id": "267-test",
        "source_commit_sha": "x" * 40, "pull_number": False, "head_sha": "b" * 40,
        "actions_run_ids": {}, "merge_commit_sha": "c" * 40, "landed_sha": "d" * 40,
        "documentation_completion_revision": "d" * 40, "work_completion": {},
        "source_close": {}, "cleanup": {},
        "telemetry": {
            "provider_reads": 0, "provider_mutations": 0,
            "duplicate_verification_attempts": 0, "duplicate_review_attempts": 0,
            "promotion_review_invocations": 0, "duplicate_proof_attempts": 0,
            "operation_counts": {"github_actions_list": 1},
        },
    }
    audit = _terminal_audit(receipt)
    assert audit["status"] == "attention"
    assert "invalid_terminal_receipt" in audit["flags"]
    assert {"source_commit_sha", "pull_number", "actions_run_ids", "work_completion", "source_close", "cleanup"} <= set(audit["invalid_terminal_fields"])


def test_terminal_audit_treats_empty_telemetry_as_unknown() -> None:
    receipt = {
        "work_id": "WORK-594", "typed_record_id": "SPEC-594", "change_id": "267-test",
        "source_commit_sha": "a" * 40, "pull_number": 1, "head_sha": "b" * 40,
        "actions_run_ids": [2], "merge_commit_sha": "c" * 40, "landed_sha": "d" * 40,
        "documentation_completion_revision": "d" * 40, "work_completion": {"mode": "apply"},
        "source_close": {"required": True, "applied": True}, "cleanup": {"status": "applied"},
        "telemetry": {},
    }
    audit = _terminal_audit(receipt)
    assert "invalid_telemetry" in audit["flags"]
    assert audit["complexity_budget"]["provider_calls"] is None
    assert audit["complexity_budget"]["meets_simplification_target"] is False


def test_controller_checkpoints_failed_stage_attempt_and_inflight_audit(tmp_path: Path) -> None:
    store = PromotionStateStore(tmp_path)
    handoff = {"status": "promotion_ready", "work_id": "WORK-594", "change_id": "267-test", "source_commit_sha": "a" * 40}
    async def failing(stage, _handoff, _observations):
        checkpoint = store.load("promotion-failure") or {}
        checkpoint["inflight_audit"] = {"provider_reads": 1, "tool_calls": 1}
        store.save("promotion-failure", checkpoint)
        raise RuntimeError(stage)
    with pytest.raises(RuntimeError, match="refresh_default"):
        asyncio.run(PromotionController(failing, store).converge(operation_id="promotion-failure", promotion_handoff=handoff))
    checkpoint = store.load("promotion-failure")
    assert checkpoint is not None
    assert checkpoint["telemetry"]["stage_attempts"]["refresh_default"] == 1
    assert checkpoint["telemetry"]["provider_reads"] == 1
    assert "refresh_default" in checkpoint["telemetry"]["stage_timings_ms"]


def test_controller_suppresses_immediate_no_progress_retry_after_stage_failure(tmp_path: Path) -> None:
    store = PromotionStateStore(tmp_path)
    handoff = {
        "status": "promotion_ready",
        "work_id": "WORK-594",
        "change_id": "267-test",
        "source_commit_sha": "a" * 40,
    }
    calls: list[str] = []

    async def failing(stage, _handoff, _observations):
        calls.append(stage)
        raise RuntimeError("deterministic provider failure")

    controller = PromotionController(failing, store)
    with pytest.raises(RuntimeError, match="deterministic provider failure"):
        asyncio.run(controller.converge(operation_id="promotion-backoff", promotion_handoff=handoff))

    replay = asyncio.run(
        controller.converge(operation_id="promotion-backoff", promotion_handoff=handoff)
    )

    assert calls == ["refresh_default"]
    assert replay.state == "blocked"
    assert replay.current_stage == "refresh_default"
    assert replay.observations["refresh_default"]["reason"] == "no_progress_retry_backoff"
    checkpoint = store.load("promotion-backoff")
    assert checkpoint is not None
    assert checkpoint["telemetry"]["suppressed_no_progress_retries"] == 1


class _FakeLaunchedProcess:
    def __init__(self) -> None:
        self.running = True
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if self.running else 1

    def terminate(self):
        self.terminated = True
        self.running = False

    def wait(self, _timeout):
        return 1

    def kill(self):
        self.killed = True
        self.running = False


def test_failed_candidate_start_terminates_exact_launched_child() -> None:
    process = _FakeLaunchedProcess()
    asyncio.run(_terminate_launched_process(process))
    assert process.terminated is True
    assert process.running is False
    assert process.killed is False


class _RaceExitedProcess(_FakeLaunchedProcess):
    def terminate(self):
        self.running = False
        raise ProcessLookupError("already exited")


def test_failed_candidate_cleanup_preserves_original_failure_on_exit_race() -> None:
    process = _RaceExitedProcess()
    asyncio.run(_terminate_launched_process(process))
    assert process.running is False
    assert process.killed is False


def test_v2_handoff_exposes_typed_phase_plan_and_normalizes_strings() -> None:
    contract = _contract(46011, work_id="WORK-588")
    payload = contract.to_json_dict()
    assert contract.schema_version == 2
    assert contract.obligations == (
        TaskObligation.VERIFICATION,
        TaskObligation.REVIEW_CLOSED,
        TaskObligation.LIVE_CANDIDATE_VERIFICATION,
    )
    plan = {item["kind"]: item for item in payload["typed_obligations"]}
    assert plan["verification"] == {
        "kind": "verification", "phase": "implementation", "declared": True
    }
    assert plan["provider_proof"]["phase"] == "pull_request"
    assert plan["documentation"]["phase"] == "documentation"
    assert plan["commissioning"]["phase"] == "commissioning"
    assert plan["completion"]["phase"] == "completion"
    assert contract.obligations_through(ObligationPhase.REVIEW) == (
        TaskObligation.VERIFICATION, TaskObligation.REVIEW_CLOSED,
    )


def test_conditional_obligations_fail_closed_and_remain_phase_aware() -> None:
    obligations = tuple(TaskObligation)
    with pytest.raises(ValueError, match="OBLIGATION_CONDITION_UNRESOLVED: mcp_surface"):
        required_obligations(
            obligations, phase=ObligationPhase.CANDIDATE, conditions={}
        )
    required = required_obligations(
        obligations,
        phase=ObligationPhase.COMPLETION,
        conditions={
            "mcp_surface": True,
            "provider_required": True,
            "documentation_required": False,
            "commissioning_required": True,
        },
    )
    assert TaskObligation.LIVE_CANDIDATE_VERIFICATION in required
    assert TaskObligation.PROVIDER_PROOF in required
    assert TaskObligation.DOCUMENTATION not in required
    assert TaskObligation.COMMISSIONING in required
    assert TaskObligation.COMPLETION in required


def test_published_mcp_schema_validation_requires_exact_input_and_output() -> None:
    expected = {"mutate": {
        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
        "outputSchema": {"type": "object", "required": ["status"]},
    }}
    assert set(validate_mcp_tool_schemas(expected, expected)) == {"mutate"}
    changed = {"mutate": {
        "inputSchema": expected["mutate"]["inputSchema"],
        "outputSchema": {"type": "object", "required": ["result"]},
    }}
    with pytest.raises(ValueError, match="MCP_TOOL_SCHEMA_MISMATCH: mutate.outputSchema"):
        validate_mcp_tool_schemas(expected, changed)


def test_mutating_live_scenario_requires_disposable_cleanup_or_recovery_evidence() -> None:
    scenario = {"effect": "external", "effect_boundary": {
        "fixture_id": "fixture-588", "disposable": True,
    }}
    with pytest.raises(ValueError, match="LIVE_EFFECT_CLEANUP_EVIDENCE_REQUIRED"):
        validate_effect_safe_scenarios((scenario,), ({"status": "passed"},))
    proofs = validate_effect_safe_scenarios(
        (scenario,), ({"status": "passed", "cleanup": {"status": "applied"}},)
    )
    assert len(proofs) == 1 and len(proofs[0]) == 64


def test_schema_v1_contract_and_promotion_records_remain_loadable(tmp_path: Path) -> None:
    store = TaskHandoffStore(tmp_path)
    legacy = TaskHandoffContract(
        project_id="kis-mcp", work_id="WORK-588", repository="NielPieterse0/kis-mcp",
        requirements=("legacy",), acceptance_criteria=("loads",),
        affected_surfaces=("mcp",), obligations=("verification", "review_closed"),
        candidate_port=46011, source_identity="legacy:588", change_id="612-legacy",
        schema_version=LEGACY_SCHEMA_VERSION,
    )
    store.contracts.mkdir(parents=True)
    store.contract_path("WORK-588").write_text(
        json.dumps(legacy.to_json_dict()), encoding="utf-8"
    )
    loaded = store.load_contract("WORK-588")
    assert loaded is not None and loaded.schema_version == LEGACY_SCHEMA_VERSION
    assert loaded.obligations == (TaskObligation.VERIFICATION, TaskObligation.REVIEW_CLOSED)

    promotion = PromotionReadyHandoff(
        work_id="WORK-588", change_id="612-legacy",
        contract_fingerprint=legacy.contract_fingerprint, source_commit_sha="a" * 40,
        candidate_identity={
            "work_id": "WORK-588", "contract_fingerprint": legacy.contract_fingerprint,
            "server_instance_id": "candidate-588",
        },
        execution={"contract": "change-execution-result-v2", "status": "passed"},
        evidence=(), satisfied_obligations=("verification",),
        schema_version=LEGACY_SCHEMA_VERSION,
    )
    store.promotions.mkdir(parents=True)
    store.promotion_path("WORK-588").write_text(
        json.dumps(promotion.to_json_dict()), encoding="utf-8"
    )
    loaded_promotion = store.load_promotion("WORK-588")
    assert loaded_promotion.schema_version == LEGACY_SCHEMA_VERSION
    assert loaded_promotion.source_commit_sha == "a" * 40
    assert store.resolve_promotion("612-legacy", "a" * 40) == loaded_promotion
