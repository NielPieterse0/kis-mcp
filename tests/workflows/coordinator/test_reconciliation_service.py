import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.state import StateOwnershipClass
from kis_mcp.workflows.coordinator.models import ReservationAdmissionError
from kis_mcp.workflows.coordinator.reconciliation import (
    IntegrationQueueService,
    ReconciliationService,
    VerificationRequirementService,
)


BASE = {"commit_sha": "a" * 40, "tree_sha": "b" * 40}
HEAD = {"commit_sha": "c" * 40, "tree_sha": "d" * 40}
RUNTIME = {"binding_id": "runtime-1", "binding_fingerprint": "e" * 64}
KEY = "assignment-secret"


class _Namespace:
    def __init__(self, path: Path) -> None:
        self.path = str(path)


class _Resolver:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.requests: list[object] = []

    def resolve(self, request: object) -> _Namespace:
        self.requests.append(request)
        state_key = getattr(request, "state_key")
        return _Namespace(self.root / str(state_key))


class _Authority:
    def __init__(self, reservation: dict[str, object]) -> None:
        self.reservation = reservation

    def current_reservation(self, reservation_id: str) -> dict[str, object]:
        assert reservation_id == self.reservation["reservation_id"]
        return dict(self.reservation)


def _packet_root(root: Path, packet_id: str) -> Path:
    return root / "coordinator" / "packets" / packet_id


def _packet(
    root: Path,
    *,
    packet_id: str = "packet-1",
    dependencies: tuple[str, ...] = (),
) -> dict[str, object]:
    packet = {
        "schema_version": 2,
        "contract": "coordinator-work-packet-v2",
        "packet_id": packet_id,
        "work_id": "work-1",
        "project_id": "kis-mcp",
        "change_id": "150-parallel-agent-coordinator",
        "slice_id": "252",
        "task_id": "reconcile",
        "outcome": "reconcile worker handoff",
        "required_capabilities": [],
        "scope": {
            "owned_paths": ["src/kis_mcp/workflows/coordinator/**"],
            "shared_paths": [],
            "integration_owner": None,
        },
        "dependencies": list(dependencies),
        "acceptance_checks": ["reconciliation passes"],
        "exact_base": BASE,
        "authority": {
            "reservation_id": "reservation-1",
            "authority_revision": 3,
            "lease_id": "lease-1",
            "fence_token": 7,
        },
        "runtime_binding": RUNTIME,
        "verification_requirement_ids": [],
        "required_handoff_fields": ["handoff_id"],
        "assignment": {"generation": 1, "key": KEY},
        "issued_at": "2026-08-17T12:00:00Z",
    }
    issued = {
        "schema_version": 1,
        "contract": "coordinator-work-packet-issued-v1",
        "packet_id": packet_id,
        "packet": {key: value for key, value in packet.items() if key != "assignment"},
        "assignment": {
            "generation": 1,
            "key_sha256": hashlib.sha256(KEY.encode()).hexdigest(),
            "state": "active",
        },
        "issued_at": packet["issued_at"],
    }
    path = _packet_root(root, packet_id) / "001-issued.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(issued), encoding="utf-8")
    return packet


def _reservation() -> dict[str, object]:
    return {
        "reservation_id": "reservation-1",
        "project_id": "kis-mcp",
        "change_id": "150-parallel-agent-coordinator",
        "authority_revision": 3,
        "fence_token": 7,
        "status": "active",
        "owned_paths": ["src/kis_mcp/workflows/coordinator/**"],
        "shared_paths": [],
        "dependencies": [],
        "integration_owner": None,
    }


def _claims() -> list[dict[str, object]]:
    return [
        {
            "change_id": "150-parallel-agent-coordinator",
            "outcome": "coordinator",
            "owned_paths": ["src/kis_mcp/workflows/coordinator/**"],
            "shared_paths": [],
            "excluded_paths": [],
            "dependencies": [],
            "integration_owner": None,
        }
    ]


def _handoff(*, handoff_id: str = "handoff-1") -> dict[str, object]:
    return {
        "schema_version": 2,
        "contract": "coordinator-worker-handoff-v2",
        "handoff_id": handoff_id,
        "execution_id": "execution-1",
        "attempt_id": "attempt-1",
        "packet_id": "packet-1",
        "task_id": "reconcile",
        "assignment_generation": 1,
        "reservation_id": "reservation-1",
        "authority_revision": 3,
        "fence_token": 7,
        "worker_id": "worker-1",
        "runtime_binding": RUNTIME,
        "result_id": "result-1",
        "exact_head": HEAD,
        "changed_paths": ["src/kis_mcp/workflows/coordinator/reconciliation.py"],
        "evidence": [
            {"kind": "test", "reference": "pytest", "digest": "f" * 64}
        ],
        "residual_state": [],
        "status": "worker_done",
        "observed_at": "2026-08-17T12:10:00Z",
    }


def _observed() -> dict[str, object]:
    return {
        "exact_base": BASE,
        "exact_head": HEAD,
        "changed_paths": ["src/kis_mcp/workflows/coordinator/reconciliation.py"],
    }


def _execution(*, residual_state: tuple[str, ...] = ()) -> dict[str, object]:
    return {
        "schema_version": 2,
        "contract": "coordinator-worker-execution-v2",
        "identity": {
            "execution_id": "execution-1",
            "packet_id": "packet-1",
            "task_id": "reconcile",
            "assignment_generation": 1,
            "reservation_id": "reservation-1",
            "authority_revision": 3,
            "lease_id": "lease-1",
            "fence_token": 7,
            "worker_id": "worker-1",
            "runtime_binding": RUNTIME,
            "attempt_id": "attempt-1",
        },
        "state": "completed",
        "sequence": 1,
        "observed_at": "2026-08-17T12:09:00Z",
        "progress_id": "progress-1",
        "result_id": "result-1",
        "residual_state": list(residual_state),
        "accepted_events": {"event-1": "a" * 64},
        "last_event": {"event_id": "event-1", "digest": "a" * 64},
    }


def _service(
    root: Path,
    claims=_claims,
    execution: dict[str, object] | None = None,
) -> ReconciliationService:
    durable_execution = execution if execution is not None else _execution()
    return ReconciliationService(
        state_root=root,
        project_boundary=root.parent,
        authority=_Authority(_reservation()),
        list_claims=claims,
        load_execution=lambda execution_id: (
            durable_execution if execution_id == "execution-1" else None
        ),
        namespace_resolver=_Resolver(root / "evidence"),
    )


def test_accepts_exact_handoff_consumes_key_and_replays_idempotently(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    service = _service(tmp_path)
    first = service.reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        completed_dependency_ids=(),
        complexity="large",
        risk_triggers=("architecture_boundary", "public_contract"),
        verification_ids=("repository-full",),
    )
    second = service.reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        completed_dependency_ids=(),
        complexity="large",
        risk_triggers=("architecture_boundary", "public_contract"),
        verification_ids=("repository-full",),
    )
    assert first == second
    assert first["reconciliation"]["status"] == "accepted"
    assert first["reconciliation"]["integration"]["queue_state"] == "queued"
    reconciliation_schema = json.loads(
        (Path(__file__).parents[3] / "contracts/coordinator/reconciliation-result.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(reconciliation_schema).validate(first["reconciliation"])
    assert first["verification_requirements"]["verification_authority"] == "github_actions_exact_head"
    assert set(first["verification_requirements"]["review_types"]) >= {
        "code-quality",
        "architecture",
        "api-contracts",
    }
    consumed = _packet_root(tmp_path, "packet-1") / "002-assignment-consumed.json"
    assert json.loads(consumed.read_text(encoding="utf-8"))["handoff_id"] == "handoff-1"


def test_accepted_replay_rechecks_current_authority(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    reservation = _reservation()
    authority = _Authority(reservation)
    service = ReconciliationService(
        state_root=tmp_path,
        project_boundary=tmp_path.parent,
        authority=authority,
        list_claims=_claims,
        load_execution=lambda execution_id: (
            _execution() if execution_id == "execution-1" else None
        ),
        namespace_resolver=_Resolver(tmp_path / "evidence"),
    )
    service.reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    reservation["fence_token"] = 8
    with pytest.raises(ReservationAdmissionError, match="INTEGRATION_AUTHORITY_STALE"):
        service.reconcile(
            packet=packet,
            handoff=_handoff(),
            assignment_key=KEY,
            observed_change=_observed(),
            complexity="large",
        )


def test_rejects_stale_fence_without_consuming_assignment(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    handoff = _handoff()
    handoff["fence_token"] = 6
    result = _service(tmp_path).reconcile(
        packet=packet,
        handoff=handoff,
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    assert result["reconciliation"]["status"] == "rejected"
    assert any(item["code"] == "STALE_FENCE_TOKEN" for item in result["reconciliation"]["violations"])
    assert not (_packet_root(tmp_path, "packet-1") / "002-assignment-consumed.json").exists()


def test_rejects_observed_changed_path_outside_packet_scope(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    observed = _observed()
    observed["changed_paths"] = ["src/kis_mcp/other.py"]
    handoff = _handoff()
    handoff["changed_paths"] = ["src/kis_mcp/other.py"]
    result = _service(tmp_path).reconcile(
        packet=packet,
        handoff=handoff,
        assignment_key=KEY,
        observed_change=observed,
        complexity="large",
    )
    assert result["reconciliation"]["status"] == "rejected"
    assert result["reconciliation"]["validations"]["local_scope"] == "failed"


def test_unsatisfied_dependency_is_incomplete_and_does_not_consume_key(tmp_path: Path) -> None:
    packet = _packet(tmp_path, dependencies=("task-before",))
    result = _service(tmp_path).reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        completed_dependency_ids=(),
        complexity="large",
    )
    assert result["reconciliation"]["status"] == "incomplete"
    assert not (_packet_root(tmp_path, "packet-1") / "002-assignment-consumed.json").exists()


def test_conflicting_global_claim_blocks_reconciliation(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    claims = _claims() + [
        {
            "change_id": "999-conflict",
            "outcome": "conflict",
            "owned_paths": ["src/kis_mcp/workflows/coordinator/reconciliation.py"],
            "shared_paths": [],
            "excluded_paths": [],
            "dependencies": [],
            "integration_owner": None,
        }
    ]
    result = _service(tmp_path, claims=lambda: claims).reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    assert result["reconciliation"]["status"] == "rejected"
    assert result["reconciliation"]["validations"]["global_claims"] == "failed"


def test_consumed_key_cannot_authorize_different_handoff(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    service = _service(tmp_path)
    service.reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    with pytest.raises(ReservationAdmissionError, match="ASSIGNMENT_ALREADY_CONSUMED"):
        service.reconcile(
            packet=packet,
            handoff=_handoff(handoff_id="handoff-2"),
            assignment_key=KEY,
            observed_change=_observed(),
            complexity="large",
        )


def test_verification_requirements_use_github_actions_exact_head_contract(tmp_path: Path) -> None:
    requirement = VerificationRequirementService().derive(
        project_id="kis-mcp",
        change_id="150-parallel-agent-coordinator",
        authority_revision=3,
        changed_paths=(
            "src/kis_mcp/workflows/coordinator/reconciliation.py",
            "contracts/coordinator/verification-requirements.schema.json",
            "docs/COORDINATOR-MODULE-PRODUCT-SPEC.md",
        ),
        complexity="large",
        risk_triggers=("architecture_boundary", "public_contract", "security"),
        verification_ids=("repository-full",),
    )
    schema = json.loads(
        (Path(__file__).parents[3] / "contracts/coordinator/verification-requirements.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(requirement)
    assert requirement["schema_version"] == 3
    assert requirement["contract"] == "coordinator-verification-requirements-v3"
    assert requirement["verification_authority"] == "github_actions_exact_head"
    assert requirement["exact_head_required"] is True
    assert "provider_native_required" not in requirement
    assert {item["check_id"] for item in requirement["checks"]} >= {
        "repository-full",
        "python-affected",
        "contract-validation",
        "documentation-validation",
        "integration-preflight",
    }
    assert set(requirement["review_types"]) >= {
        "code-quality",
        "architecture",
        "api-contracts",
        "safety-security",
    }


def _accepted_reconciliation(reconciliation_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "contract": "coordinator-reconciliation-result-v1",
        "reconciliation_id": reconciliation_id,
        "handoff_id": f"handoff-{reconciliation_id}",
        "reservation_id": "reservation-1",
        "authority_revision": 3,
        "fence_token": 7,
        "runtime_binding": RUNTIME,
        "validations": {
            "reservation": "passed",
            "runtime_binding": "passed",
            "fence": "passed",
            "global_claims": "passed",
            "local_scope": "passed",
            "exact_head": "passed",
        },
        "status": "accepted",
        "violations": [],
        "verification_requirement_ids": ["verification-1"],
        "integration": {
            "owner_change_id": "150-parallel-agent-coordinator",
            "queue_state": "queued",
            "merge_authority_granted": False,
        },
    }


def test_integration_queue_requires_exact_github_actions_verification(tmp_path: Path) -> None:
    queue = IntegrationQueueService(
        project_id="kis-mcp",
        change_id="150-parallel-agent-coordinator",
        authority_preflight=lambda: None,
        namespace_resolver=_Resolver(tmp_path / "evidence"),
    )
    item = queue.enqueue(
        reconciliation=_accepted_reconciliation("r1"),
        candidate_head=HEAD["commit_sha"],
    )
    with pytest.raises(ReservationAdmissionError, match="GITHUB_ACTIONS_EXACT_HEAD_VERIFICATION_REQUIRED"):
        queue.authorize_delivery(
            item["queue_item_id"],
            verification={
                "revision": "9" * 40,
                "status": "passed",
                "source": "github_actions",
                "reference": "actions:run-9",
            },
        )
    with pytest.raises(ReservationAdmissionError, match="GITHUB_ACTIONS_EXACT_HEAD_VERIFICATION_REQUIRED"):
        queue.authorize_delivery(
            item["queue_item_id"],
            verification={
                "revision": HEAD["commit_sha"],
                "status": "passed",
                "source": "local",
                "reference": "local:verify@head",
            },
        )
    with pytest.raises(ReservationAdmissionError, match="GITHUB_ACTIONS_EXACT_HEAD_VERIFICATION_REQUIRED"):
        queue.authorize_delivery(
            item["queue_item_id"],
            verification={
                "revision": HEAD["commit_sha"],
                "status": "passed",
                "source": "github_actions",
                "reference": "",
            },
        )
    authorized = queue.authorize_delivery(
        item["queue_item_id"],
        verification={
            "revision": HEAD["commit_sha"],
            "status": "passed",
            "source": "github_actions",
            "reference": "actions:run-123",
        },
    )
    assert authorized["state"] == "delivery_authorized"
    delivered = queue.mark_delivered(item["queue_item_id"], merged_revision="1" * 40)
    assert delivered["state"] == "delivered"
    with pytest.raises(ReservationAdmissionError, match="INTEGRATION_OWNER_BUSY"):
        queue.enqueue(
            reconciliation=_accepted_reconciliation("r2"),
            candidate_head="2" * 40,
        )
    with pytest.raises(ReservationAdmissionError, match="INTEGRATION_CLEANUP_NOT_READY"):
        queue.complete_cleanup(
            item["queue_item_id"],
            cleanup={
                "status": "passed",
                "worktree_clean": False,
                "merged": True,
                "recoverable": True,
                "reference": "cleanup:dirty",
            },
        )
    cleaned = queue.complete_cleanup(
        item["queue_item_id"],
        cleanup={
            "status": "passed",
            "worktree_clean": True,
            "merged": True,
            "recoverable": True,
            "reference": "cleanup:governed",
        },
    )
    assert cleaned["state"] == "cleanup_complete"
    next_item = queue.enqueue(
        reconciliation=_accepted_reconciliation("r2"),
        candidate_head="2" * 40,
    )
    assert next_item["state"] == "queued"


def test_integration_queue_rechecks_authority_before_admission_and_delivery(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def preflight() -> None:
        calls.append("checked")

    queue = IntegrationQueueService(
        project_id="kis-mcp",
        change_id="150-parallel-agent-coordinator",
        authority_preflight=preflight,
        namespace_resolver=_Resolver(tmp_path / "evidence"),
    )
    item = queue.enqueue(
        reconciliation=_accepted_reconciliation("authority-check"),
        candidate_head=HEAD["commit_sha"],
    )
    assert calls == ["checked"]
    queue.authorize_delivery(
        item["queue_item_id"],
        verification={
            "revision": HEAD["commit_sha"],
            "status": "passed",
            "source": "github_actions",
            "reference": "actions:run-authority-check",
        },
    )
    assert calls == ["checked", "checked"]


def test_integration_queue_serializes_same_owner_key(tmp_path: Path) -> None:
    queue = IntegrationQueueService(
        project_id="kis-mcp",
        change_id="150-parallel-agent-coordinator",
        authority_preflight=lambda: None,
        namespace_resolver=_Resolver(tmp_path / "evidence"),
    )

    def enqueue(index: int) -> str:
        try:
            item = queue.enqueue(
                reconciliation=_accepted_reconciliation(f"r{index}"),
                candidate_head=(f"{index:x}" * 40)[:40],
            )
            return str(item["queue_item_id"])
        except ReservationAdmissionError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(enqueue, (1, 2)))
    assert sum(result.startswith("integration-") for result in results) == 1
    assert results.count("INTEGRATION_OWNER_BUSY") == 1


def test_tampered_packet_scope_is_rejected_against_durable_issuance(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    packet["scope"] = {
        "owned_paths": ["src/kis_mcp/**"],
        "shared_paths": [],
        "integration_owner": None,
    }
    result = _service(tmp_path).reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    assert result["reconciliation"]["status"] == "rejected"
    assert any(
        item["code"] == "WORK_PACKET_EVIDENCE_MISMATCH"
        for item in result["reconciliation"]["violations"]
    )


def test_slice_six_evidence_uses_typed_durable_namespace(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    resolver = _Resolver(tmp_path / "evidence")
    service = ReconciliationService(
        state_root=tmp_path,
        project_boundary=tmp_path.parent,
        authority=_Authority(_reservation()),
        list_claims=_claims,
        load_execution=lambda execution_id: (
            _execution() if execution_id == "execution-1" else None
        ),
        namespace_resolver=resolver,
    )
    service.reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    keys = {getattr(request, "state_key") for request in resolver.requests}
    assert keys == {"coordinator-reconciliation", "coordinator-integration"}
    for request in resolver.requests:
        assert getattr(request, "ownership") is StateOwnershipClass.DURABLE_EVIDENCE
        assert getattr(request, "identities")["project_id"] == "kis-mcp"
        assert getattr(request, "identities")["source_id"] == (
            "change-150-parallel-agent-coordinator"
        )


def test_busy_integration_owner_does_not_consume_assignment(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    resolver = _Resolver(tmp_path / "evidence")
    queue = IntegrationQueueService(
        project_id="kis-mcp",
        change_id="150-parallel-agent-coordinator",
        authority_preflight=lambda: None,
        namespace_resolver=resolver,
    )
    queue.enqueue(
        reconciliation=_accepted_reconciliation("already-active"),
        candidate_head="1" * 40,
    )
    service = ReconciliationService(
        state_root=tmp_path,
        project_boundary=tmp_path.parent,
        authority=_Authority(_reservation()),
        list_claims=_claims,
        load_execution=lambda execution_id: (
            _execution() if execution_id == "execution-1" else None
        ),
        namespace_resolver=resolver,
    )
    with pytest.raises(ReservationAdmissionError, match="INTEGRATION_OWNER_BUSY"):
        service.reconcile(
            packet=packet,
            handoff=_handoff(),
            assignment_key=KEY,
            observed_change=_observed(),
            complexity="large",
        )
    assert not (_packet_root(tmp_path, "packet-1") / "002-assignment-consumed.json").exists()


def test_revoked_assignment_cannot_reconcile(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    service = _service(tmp_path)
    revoked = service.revoke_assignment(
        "packet-1", generation=1, reason="worker replaced"
    )
    assert revoked["state"] == "revoked"
    assert service.revoke_assignment(
        "packet-1", generation=1, reason="worker replaced"
    ) == revoked
    with pytest.raises(ReservationAdmissionError, match="ASSIGNMENT_REVOKED"):
        service.reconcile(
            packet=packet,
            handoff=_handoff(),
            assignment_key=KEY,
            observed_change=_observed(),
            complexity="large",
        )


def test_reconcile_recovers_after_crash_between_consumption_and_persist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packet = _packet(tmp_path)
    service = _service(tmp_path)

    def crash_after_consume(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(service, "_persist_reconciliation", crash_after_consume)
    with pytest.raises(RuntimeError, match="simulated crash"):
        service.reconcile(
            packet=packet,
            handoff=_handoff(),
            assignment_key=KEY,
            observed_change=_observed(),
            complexity="large",
        )
    consumed = _packet_root(tmp_path, "packet-1") / "002-assignment-consumed.json"
    assert consumed.is_file()

    recovered = _service(tmp_path).reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    assert recovered["reconciliation"]["status"] == "accepted"
    queue_root = tmp_path / "evidence" / "coordinator-integration"
    assert len([path for path in queue_root.iterdir() if path.is_dir()]) == 1


def test_current_governed_claim_divergence_blocks_reconciliation(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    claims = _claims()
    claims[0]["owned_paths"] = ["src/kis_mcp/workflows/coordinator/planner.py"]
    result = _service(tmp_path, claims=lambda: claims).reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    assert result["reconciliation"]["status"] == "rejected"
    assert result["reconciliation"]["validations"]["global_claims"] == "failed"
    assert any(
        item["code"] == "GOVERNED_SCOPE_DIVERGED"
        for item in result["reconciliation"]["violations"]
    )


def test_dependency_ids_are_identifiers_not_repository_paths(tmp_path: Path) -> None:
    packet = _packet(tmp_path, dependencies=("task:before",))
    result = _service(tmp_path).reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        completed_dependency_ids=("task:before",),
        complexity="large",
    )
    assert result["reconciliation"]["status"] == "accepted"


def test_residual_state_blocks_reviewability_without_consuming_key(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    handoff = _handoff()
    residual = ("integration repair still required",)
    handoff["residual_state"] = list(residual)
    result = _service(tmp_path, execution=_execution(residual_state=residual)).reconcile(
        packet=packet,
        handoff=handoff,
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    assert result["reconciliation"]["status"] == "incomplete"
    assert any(
        item["code"] == "RESIDUAL_STATE_REQUIRES_RESOLUTION"
        for item in result["reconciliation"]["violations"]
    )
    assert not (_packet_root(tmp_path, "packet-1") / "002-assignment-consumed.json").exists()


def test_durable_worker_execution_identity_mismatch_is_rejected(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    execution = _execution()
    identity = dict(execution["identity"])
    identity["attempt_id"] = "attempt-stale"
    execution["identity"] = identity
    result = _service(tmp_path, execution=execution).reconcile(
        packet=packet,
        handoff=_handoff(),
        assignment_key=KEY,
        observed_change=_observed(),
        complexity="large",
    )
    assert result["reconciliation"]["status"] == "rejected"
    assert any(
        item["code"] == "WORKER_EXECUTION_MISMATCH"
        for item in result["reconciliation"]["violations"]
    )
