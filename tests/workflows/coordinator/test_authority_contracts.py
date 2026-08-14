from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parents[3]
SHA = "a" * 40


def _schema(name: str) -> dict[str, object]:
    path = ROOT / "contracts" / "coordinator" / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _errors(name: str, payload: dict[str, object]) -> list[object]:
    return list(Draft202012Validator(_schema(name)).iter_errors(payload))


def _reservation() -> dict[str, object]:
    return {
        "schema_version": 1,
        "contract": "coordinator-reservation-v1",
        "reservation_id": "reservation-150-1",
        "project_id": "kis-mcp",
        "change_id": "150-parallel-agent-coordinator",
        "change_sequence": 150,
        "base": {"commit_sha": SHA, "tree_sha": SHA},
        "owned_paths": ["contracts/coordinator/**"],
        "shared_paths": [],
        "dependencies": [],
        "integration_owner": "150-parallel-agent-coordinator",
        "authority_revision": 1,
        "lease_id": "lease-150-1",
        "fence_token": 1,
        "status": "reserved",
    }


def test_reservation_requires_exact_revision_and_fence_identity() -> None:
    payload = _reservation()
    assert _errors("reservation", payload) == []

    payload.pop("fence_token")
    assert _errors("reservation", payload)


def test_runtime_binding_is_structurally_non_authorizing() -> None:
    payload = {
        "schema_version": 1,
        "contract": "coordinator-runtime-binding-v1",
        "binding_id": "runtime-binding-1",
        "runtime_id": "kis-dev",
        "runtime_revision": SHA,
        "tool_id": "worker-agent",
        "tool_revision": "worker-agent-v1",
        "transport": "mcp",
        "capabilities": ["repository.read", "repository.change"],
        "observed_at": "2026-08-14T19:40:00Z",
        "grants_mutation_authority": False,
    }
    assert _errors("runtime-binding", payload) == []

    payload["grants_mutation_authority"] = True
    assert _errors("runtime-binding", payload)


def test_scope_revision_requires_compare_and_swap_evidence() -> None:
    payload = {
        "schema_version": 1,
        "contract": "coordinator-scope-revision-v1",
        "request_id": "scope-revision-1",
        "reservation_id": "reservation-150-1",
        "expected_authority_revision": 1,
        "proposed_authority_revision": 2,
        "expected_fence_token": 1,
        "changes": {
            "add_owned_paths": ["src/kis_mcp/workflows/coordinator/**"],
            "remove_owned_paths": [],
            "add_shared_paths": [],
            "remove_shared_paths": [],
            "add_dependencies": [],
            "remove_dependencies": [],
            "integration_owner": "150-parallel-agent-coordinator",
        },
        "status": "proposed",
    }
    assert _errors("scope-revision", payload) == []
    payload.pop("expected_authority_revision")
    assert _errors("scope-revision", payload)


def test_shared_dependency_node_requires_explicit_integration_owner() -> None:
    payload = {
        "schema_version": 1,
        "contract": "coordinator-dependency-dag-v1",
        "project_id": "kis-mcp",
        "change_id": "150-parallel-agent-coordinator",
        "revision": 1,
        "nodes": {
            "slice-247": {
                "kind": "slice",
                "outcome": "Define executable coordinator contracts",
                "owned_paths": [],
                "shared_paths": ["shared/hotspot.py"],
                "integration_owner": "150-parallel-agent-coordinator",
            }
        },
        "edges": [],
        "validation": {"status": "unverified", "evidence": []},
    }
    assert _errors("dependency-dag", payload) == []
    payload["nodes"]["slice-247"]["integration_owner"] = None
    assert _errors("dependency-dag", payload)
    payload["nodes"]["slice-247"]["integration_owner"] = "150-parallel-agent-coordinator"
    payload["validation"]["status"] = "verified"
    assert _errors("dependency-dag", payload)


def test_lease_requires_positive_fence_token() -> None:
    payload = {
        "schema_version": 1,
        "contract": "coordinator-lease-v1",
        "lease_id": "lease-150-1",
        "reservation_id": "reservation-150-1",
        "holder_id": "agent-4",
        "fence_token": 1,
        "issued_at": "2026-08-14T19:40:00Z",
        "expires_at": "2026-08-14T20:40:00Z",
        "status": "active",
    }
    assert _errors("lease", payload) == []
    payload["fence_token"] = 0
    assert _errors("lease", payload)
