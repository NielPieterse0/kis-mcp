from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import pytest

from kis_mcp.workflows.once_through import (
    EvidenceReference, EvidenceState, EvidenceValidityClass,
    PromotionController, PromotionStateStore, TaskHandoffContract, TaskHandoffStore,
    assert_candidate_port_available, derive_promotion_ready, resolve_evidence,
)
from kis_mcp.workflows.once_through.contracts import fingerprint


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


class _PromotionInvoker:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, stage: str, handoff: dict[str, object]) -> dict[str, str]:
        self.calls.append(stage)
        return {"status": "satisfied"}


def test_controller_resumes_without_repeating_satisfied_stages(tmp_path: Path) -> None:
    invoker = _PromotionInvoker()
    handoff = {"status": "promotion_ready"}
    store = PromotionStateStore(tmp_path)
    store.save("promotion-1", {
        "handoff_fingerprint": fingerprint(handoff),
        "completed": ["refresh_default", "reconcile_candidate"],
        "observations": {},
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
    first = asyncio.run(PromotionController(invoker, store).converge(
        operation_id="promotion-persisted",
        promotion_handoff={"status": "promotion_ready", "work_id": "WORK-1"},
    ))
    assert first.state == "done"
    first_calls = tuple(invoker.calls)
    second = asyncio.run(PromotionController(invoker, store).converge(
        operation_id="promotion-persisted",
        promotion_handoff={"status": "promotion_ready", "work_id": "WORK-1"},
    ))
    assert second.state == "done"
    assert tuple(invoker.calls) == first_calls
