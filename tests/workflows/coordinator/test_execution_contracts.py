from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parents[3]
SHA = "b" * 40


def _schema(name: str) -> dict[str, object]:
    path = ROOT / "contracts" / "coordinator" / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _errors(name: str, payload: dict[str, object]) -> list[object]:
    return list(Draft202012Validator(_schema(name)).iter_errors(payload))


def test_worker_handoff_can_report_only_worker_completion() -> None:
    payload = {
        "schema_version": 1,
        "contract": "coordinator-worker-handoff-v1",
        "handoff_id": "handoff-1",
        "packet_id": "packet-247-1",
        "reservation_id": "reservation-150-1",
        "authority_revision": 1,
        "fence_token": 1,
        "worker_id": "agent-4",
        "runtime_binding": {
            "binding_id": "runtime-binding-1",
            "binding_fingerprint": "d" * 64,
        },
        "exact_head": {"commit_sha": SHA, "tree_sha": SHA},
        "changed_paths": ["contracts/coordinator/work-packet.schema.json"],
        "evidence": [
            {"kind": "test", "reference": "pytest:coordinator", "digest": "c" * 64}
        ],
        "residual_state": ["#248 atomic reservation remains deferred"],
        "status": "worker_done",
        "observed_at": "2026-08-14T19:50:00Z",
    }
    assert _errors("worker-handoff", payload) == []
    payload["runtime_binding"].pop("binding_fingerprint")
    assert _errors("worker-handoff", payload)
    payload["runtime_binding"]["binding_fingerprint"] = "d" * 64
    payload["status"] = "reviewable"
    assert _errors("worker-handoff", payload)


def test_work_packet_freezes_authority_and_runtime_identity() -> None:
    payload = {
        "schema_version": 1,
        "contract": "coordinator-work-packet-v1",
        "packet_id": "packet-247-1",
        "work_id": "issue-247",
        "project_id": "kis-mcp",
        "change_id": "150-parallel-agent-coordinator",
        "slice_id": "247",
        "outcome": "Define executable coordinator contracts",
        "scope": {
            "owned_paths": ["contracts/coordinator/**"],
            "shared_paths": [],
            "integration_owner": None,
        },
        "dependencies": [],
        "acceptance_checks": ["all coordinator schemas validate"],
        "exact_base": {"commit_sha": SHA, "tree_sha": SHA},
        "authority": {
            "reservation_id": "reservation-150-1",
            "authority_revision": 1,
            "lease_id": "lease-150-1",
            "fence_token": 1,
        },
        "runtime_binding": {
            "binding_id": "runtime-binding-1",
            "binding_fingerprint": "d" * 64,
        },
        "verification_requirement_ids": ["coordinator-contract-tests"],
        "required_handoff_fields": ["packet_id"],
        "assignment": {"generation": 1, "key": "opaque-assignment-key"},
        "issued_at": "2026-08-14T19:45:00Z",
    }
    assert _errors("work-packet", payload) == []
    payload["authority"].pop("fence_token")
    assert _errors("work-packet", payload)


def test_reconciliation_acceptance_does_not_grant_merge_authority() -> None:
    payload = {
        "schema_version": 1,
        "contract": "coordinator-reconciliation-result-v1",
        "reconciliation_id": "reconcile-1",
        "handoff_id": "handoff-1",
        "reservation_id": "reservation-150-1",
        "authority_revision": 1,
        "fence_token": 1,
        "runtime_binding": {
            "binding_id": "runtime-binding-1",
            "binding_fingerprint": "d" * 64,
        },
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
        "verification_requirement_ids": ["coordinator-contract-tests"],
        "integration": {
            "owner_change_id": "150-parallel-agent-coordinator",
            "queue_state": "not_queued",
            "merge_authority_granted": False,
        },
    }
    assert _errors("reconciliation-result", payload) == []
    payload["integration"]["queue_state"] = "integrated"
    assert _errors("reconciliation-result", payload)
    payload["integration"]["queue_state"] = "not_queued"
    payload["verification_requirement_ids"] = []
    assert _errors("reconciliation-result", payload)
    payload["verification_requirement_ids"] = ["coordinator-contract-tests"]
    payload["integration"]["merge_authority_granted"] = True
    assert _errors("reconciliation-result", payload)
    payload["integration"]["merge_authority_granted"] = False
    payload["validations"]["fence"] = "failed"
    assert _errors("reconciliation-result", payload)
    payload["validations"]["fence"] = "incomplete"
    assert _errors("reconciliation-result", payload)


def test_rejected_reconciliation_requires_a_violation() -> None:
    payload = {
        "schema_version": 1,
        "contract": "coordinator-reconciliation-result-v1",
        "reconciliation_id": "reconcile-2",
        "handoff_id": "handoff-2",
        "reservation_id": "reservation-150-1",
        "authority_revision": 1,
        "fence_token": 1,
        "runtime_binding": {
            "binding_id": "runtime-binding-1",
            "binding_fingerprint": "d" * 64,
        },
        "validations": {
            "reservation": "passed",
            "runtime_binding": "passed",
            "fence": "failed",
            "global_claims": "passed",
            "local_scope": "passed",
            "exact_head": "passed",
        },
        "status": "rejected",
        "violations": [{"code": "STALE_FENCE", "reason": "worker fence is stale"}],
        "verification_requirement_ids": [],
        "integration": {
            "owner_change_id": "150-parallel-agent-coordinator",
            "queue_state": "blocked",
            "merge_authority_granted": False,
        },
    }
    assert _errors("reconciliation-result", payload) == []
    payload["integration"]["queue_state"] = "queued"
    assert _errors("reconciliation-result", payload)
    payload["integration"]["queue_state"] = "blocked"
    payload["status"] = "incomplete"
    payload["integration"]["queue_state"] = "queued"
    assert _errors("reconciliation-result", payload)
    payload["status"] = "rejected"
    payload["integration"]["queue_state"] = "blocked"
    payload["violations"] = []
    assert _errors("reconciliation-result", payload)


def test_historical_degraded_overlap_and_disjoint_admission_examples_validate() -> None:
    schema = _schema("coordinator-state")
    validator = Draft202012Validator(schema)
    examples = ROOT / "contracts" / "coordinator" / "examples"
    degraded = json.loads((examples / "degraded-overlap.json").read_text(encoding="utf-8"))
    disjoint = json.loads((examples / "disjoint-admission.json").read_text(encoding="utf-8"))
    assert list(validator.iter_errors(degraded)) == []
    assert list(validator.iter_errors(disjoint)) == []
    component_id = "exclusive-claim-overlap-140-145"
    component = degraded["degraded_components"][component_id]
    assert component["disjoint_admission"] == "allowed"
    assert disjoint["degraded_components"][component_id]["reservation_checks"][-1] == {
        "reservation_id": "148-project-created-field-read",
        "intersects_degraded_component": False,
        "component_result": "clear_of_component",
    }

    contradictory_check = json.loads(json.dumps(disjoint))
    check = contradictory_check["degraded_components"][component_id]["reservation_checks"][-1]
    check["intersects_degraded_component"] = True
    assert list(validator.iter_errors(contradictory_check))

    degraded_without_component = json.loads(json.dumps(degraded))
    degraded_without_component["degraded_components"] = {}
    assert list(validator.iter_errors(degraded_without_component))

    degraded_without_paths = json.loads(json.dumps(degraded))
    degraded_without_paths["degraded_components"][component_id]["affected_paths"] = []
    assert list(validator.iter_errors(degraded_without_paths))

    degraded_without_intersection = json.loads(json.dumps(degraded))
    for item in degraded_without_intersection["degraded_components"][component_id]["reservation_checks"]:
        item["intersects_degraded_component"] = False
        item["component_result"] = "clear_of_component"
    assert list(validator.iter_errors(degraded_without_intersection))

    ordinary_with_degradation = json.loads(json.dumps(degraded))
    ordinary_with_degradation["state"] = "planning"
    assert list(validator.iter_errors(ordinary_with_degradation))
