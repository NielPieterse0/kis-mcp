from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.workflows.coordinator import (
    PlannerRequest,
    PlannerService,
    PlannerTask,
    ReservationAdmissionError,
    WorkPacketService,
)


ROOT = Path(__file__).parents[3]
SHA = "a" * 40
TREE = "b" * 40


def _schema(name: str) -> dict[str, object]:
    path = ROOT / "contracts" / "coordinator" / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _request(*tasks: PlannerTask) -> PlannerRequest:
    return PlannerRequest(
        project_id="kis-mcp",
        change_id="150-parallel-agent-coordinator",
        work_id="issue-250",
        slice_id="250",
        revision=1,
        exact_base={"commit_sha": SHA, "tree_sha": TREE},
        tasks=tasks,
        governed_root="C:/Projects/kis-mcp",
        governed_worktree="C:/Projects/kis-mcp/.work/worktrees/150-parallel-agent-coordinator",
        lifecycle_phase="implementation",
        authority_references=("AGENTS.md", "issue:#250"),
        work_management={"record_id": "TASK-250", "source_number": 250},
        external_provenance={"session_id": "chat-123", "source": "operator"},
        verification_requirement_ids=("coordinator-planner-tests",),
    )


def _authority(**overrides: object) -> dict[str, object]:
    authority: dict[str, object] = {
        "reservation_id": "res-150",
        "authority_revision": 4,
        "lease_id": "lease-150",
        "fence_token": 4,
    }
    authority.update(overrides)
    return authority


def _candidate(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "binding_id": "kis-dev-codex",
        "worker_id": "implementer",
        "worker_revision": "develop-code@10ab0e84",
        "runtime_id": "kis-dev",
        "runtime_revision": SHA,
        "tool_id": "codex-cli",
        "tool_revision": "0.147.0",
        "protocol": "mcp",
        "interface": "reviewable-worker-v1",
        "endpoint": "127.0.0.1:8011/mcp",
        "binding": "development",
        "transport": "mcp",
        "capabilities": ["code.change.implement", "verification.execute"],
        "observed_at": "2026-08-15T20:00:00Z",
        "grants_mutation_authority": False,
    }
    candidate.update(overrides)
    return candidate


def test_planner_is_deterministic_and_hotspots_constrain_concurrency() -> None:
    tasks = (
        PlannerTask(
            task_id="alpha",
            outcome="Implement alpha",
            owned_paths=("src/alpha/**",),
            shared_paths=("docs/OPERATIONS.md",),
            acceptance_checks=("alpha tests pass",),
            required_capabilities=("code.change.implement",),
            integration_owner="integrate",
        ),
        PlannerTask(
            task_id="beta",
            outcome="Implement beta",
            owned_paths=("src/beta/**",),
            shared_paths=("docs/OPERATIONS.md",),
            acceptance_checks=("beta tests pass",),
            required_capabilities=("code.change.implement",),
            integration_owner="integrate",
        ),
        PlannerTask(
            task_id="gamma",
            outcome="Implement gamma",
            owned_paths=("src/gamma/**",),
            acceptance_checks=("gamma tests pass",),
            required_capabilities=("code.change.implement",),
        ),
        PlannerTask(
            task_id="integrate",
            outcome="Integrate shared documentation",
            owned_paths=("docs/integration-note.md",),
            dependencies=("alpha", "beta"),
            acceptance_checks=("integration review passes",),
            required_capabilities=("documentation.change.implement",),
        ),
    )
    request = _request(*tasks)
    first = PlannerService().plan(request)
    second = PlannerService().plan(request)

    assert first == second
    assert first["ready_frontier"] == ["alpha", "beta", "gamma"]
    assert first["recommended_concurrency"] == 2
    assert first["integration_hotspots"] == [
        {
            "paths": ["docs/OPERATIONS.md"],
            "integration_owner": "integrate",
            "task_ids": ["alpha", "beta"],
        }
    ]
    assert list(Draft202012Validator(_schema("dependency-dag")).iter_errors(first)) == []


def test_planner_rejects_missing_dependency_and_cycles() -> None:
    missing = _request(
        PlannerTask(
            task_id="alpha",
            outcome="Alpha",
            owned_paths=("src/alpha/**",),
            dependencies=("missing",),
            acceptance_checks=("done",),
        )
    )
    with pytest.raises(ReservationAdmissionError, match="PLANNER_DEPENDENCY_NOT_FOUND"):
        PlannerService().plan(missing)

    cyclic = _request(
        PlannerTask(
            task_id="alpha",
            outcome="Alpha",
            owned_paths=("src/alpha/**",),
            dependencies=("beta",),
            acceptance_checks=("done",),
        ),
        PlannerTask(
            task_id="beta",
            outcome="Beta",
            owned_paths=("src/beta/**",),
            dependencies=("alpha",),
            acceptance_checks=("done",),
        ),
    )
    with pytest.raises(ReservationAdmissionError, match="PLANNER_DEPENDENCY_CYCLE"):
        PlannerService().plan(cyclic)


def test_planner_rejects_ambiguous_shared_hotspot() -> None:
    request = _request(
        PlannerTask(
            task_id="alpha",
            outcome="Alpha",
            owned_paths=("src/alpha/**",),
            shared_paths=("SPEC.md",),
            acceptance_checks=("done",),
            integration_owner="alpha",
        ),
        PlannerTask(
            task_id="beta",
            outcome="Beta",
            owned_paths=("src/beta/**",),
            shared_paths=("SPEC.md",),
            acceptance_checks=("done",),
            integration_owner="beta",
        ),
    )
    with pytest.raises(ReservationAdmissionError, match="PLANNER_INTEGRATION_OWNER_AMBIGUOUS"):
        PlannerService().plan(request)


def test_packet_issuance_freezes_runtime_authority_and_hashes_assignment_key(tmp_path: Path) -> None:
    task = PlannerTask(
        task_id="alpha",
        outcome="Implement alpha",
        owned_paths=("src/alpha/**",),
        acceptance_checks=("alpha tests pass",),
        required_capabilities=("code.change.implement",),
    )
    request = _request(task)
    plan = PlannerService().plan(request)
    service = WorkPacketService(
        state_root=tmp_path,
        project_boundary=tmp_path,
        resolve_runtime=lambda _capabilities: [_candidate()],
        token_factory=lambda: "opaque-assignment-key",
        clock=lambda: datetime(2026, 8, 15, 20, 5, tzinfo=UTC),
    )
    result = service.issue(
        request=request, plan=plan, task_id="alpha", authority=_authority()
    )
    packet = result["packet"]
    binding = result["runtime_binding"]

    assert packet["assignment"] == {"generation": 1, "key": "opaque-assignment-key"}
    assert packet["run_id"].startswith("run-")
    assert packet["predecessor_run_id"] is None
    assert packet["governed"] == {
        "root": "C:/Projects/kis-mcp",
        "worktree": "C:/Projects/kis-mcp/.work/worktrees/150-parallel-agent-coordinator",
        "base_revision": {"commit_sha": SHA, "tree_sha": TREE},
    }
    assert packet["lifecycle_phase"] == "implementation"
    assert packet["authority_references"] == ["AGENTS.md", "issue:#250"]
    assert packet["work_management"] == {"record_id": "TASK-250", "source_number": 250}
    assert packet["external_provenance"] == {"session_id": "chat-123", "source": "operator"}
    assert packet["executor"] == {
        "worker_id": "implementer",
        "profile": "development",
        "runtime_id": "kis-dev",
    }
    handoff_required = sorted(
        set(_schema("worker-handoff")["required"]) - {"schema_version", "contract"}
    )
    assert packet["required_handoff_fields"] == handoff_required
    assert binding["grants_mutation_authority"] is False
    assert binding["worker_id"] == "implementer"
    assert binding["endpoint"] == "127.0.0.1:8011/mcp"
    assert list(Draft202012Validator(_schema("runtime-binding")).iter_errors(binding)) == []
    assert list(Draft202012Validator(_schema("work-packet")).iter_errors(packet)) == []

    packet_root = tmp_path / "coordinator" / "packets" / packet["packet_id"]
    stored = json.loads(next(packet_root.glob("*.json")).read_text(encoding="utf-8"))
    assert stored["assignment"]["key_sha256"]
    assert "opaque-assignment-key" not in json.dumps(stored)

    binding_path = (
        tmp_path
        / "coordinator"
        / "runtime-bindings"
        / binding["binding_id"]
        / f"{binding['binding_fingerprint']}.json"
    )
    assert json.loads(binding_path.read_text(encoding="utf-8")) == binding


def test_packet_id_is_stable_and_duplicate_issue_is_rejected(tmp_path: Path) -> None:
    task = PlannerTask(
        task_id="alpha",
        outcome="Implement alpha",
        owned_paths=("src/alpha/**",),
        acceptance_checks=("done",),
        required_capabilities=("code.change.implement",),
    )
    request = _request(task)
    plan = PlannerService().plan(request)

    service = WorkPacketService(
        state_root=tmp_path,
        project_boundary=tmp_path,
        resolve_runtime=lambda _capabilities: [_candidate()],
        token_factory=lambda: "first-key",
        clock=lambda: datetime(2026, 8, 15, 20, 5, tzinfo=UTC),
    )
    first = service.issue(
        request=request, plan=plan, task_id="alpha", authority=_authority()
    )
    with pytest.raises(ReservationAdmissionError, match="WORK_PACKET_ALREADY_ISSUED"):
        service.issue(
            request=request, plan=plan, task_id="alpha", authority=_authority()
        )

    second_root = tmp_path / "second"
    second_root.mkdir()
    second = WorkPacketService(
        state_root=second_root,
        project_boundary=tmp_path,
        resolve_runtime=lambda _capabilities: [
            _candidate(
                binding_id="kis-op-codex",
                runtime_id="kis-op",
                endpoint="127.0.0.1:8010/mcp",
                binding="operations",
                observed_at="2026-08-15T21:00:00Z",
            )
        ],
        token_factory=lambda: "different-key",
        clock=lambda: datetime(2026, 8, 15, 21, 5, tzinfo=UTC),
    ).issue(
        request=request,
        plan=plan,
        task_id="alpha",
        authority=_authority(
            authority_revision=9, lease_id="lease-reassigned", fence_token=9
        ),
    )
    assert first["packet"]["packet_id"] == second["packet"]["packet_id"]


def test_reassignment_preserves_packet_task_lineage_and_fences_prior_run(tmp_path: Path) -> None:
    task = PlannerTask(
        task_id="alpha",
        outcome="Implement alpha",
        owned_paths=("src/alpha/**",),
        acceptance_checks=("done",),
        required_capabilities=("code.change.implement",),
    )
    request = _request(task)
    plan = PlannerService().plan(request)
    keys = iter(("first-key", "second-key"))
    candidates = iter(
        (
            [_candidate()],
            [
                _candidate(
                    binding_id="kis-op-codex",
                    runtime_id="kis-op",
                    endpoint="127.0.0.1:8010/mcp",
                    binding="operations",
                    observed_at="2026-08-15T21:00:00Z",
                )
            ],
        )
    )
    service = WorkPacketService(
        state_root=tmp_path,
        project_boundary=tmp_path,
        resolve_runtime=lambda _capabilities: next(candidates),
        token_factory=lambda: next(keys),
        clock=lambda: datetime(2026, 8, 15, 21, 5, tzinfo=UTC),
    )
    first = service.issue(
        request=request, plan=plan, task_id="alpha", authority=_authority()
    )["packet"]
    with pytest.raises(
        ReservationAdmissionError, match="REASSIGNMENT_AUTHORITY_NOT_ADVANCED"
    ):
        service.reassign(
            packet_id=first["packet_id"],
            authority=_authority(),
            expected_generation=1,
            predecessor_run_id=first["run_id"],
        )
    second = service.reassign(
        packet_id=first["packet_id"],
        authority=_authority(authority_revision=5, lease_id="lease-151", fence_token=5),
        expected_generation=1,
        predecessor_run_id=first["run_id"],
    )["packet"]

    assert second["packet_id"] == first["packet_id"]
    assert second["task_id"] == first["task_id"]
    assert second["assignment"]["generation"] == 2
    assert second["run_id"] != first["run_id"]
    assert second["predecessor_run_id"] == first["run_id"]
    assert second["executor"]["runtime_id"] == "kis-op"
    events = sorted((tmp_path / "coordinator" / "packets" / first["packet_id"]).glob("*.json"))
    reassigned = json.loads(events[-1].read_text(encoding="utf-8"))
    assert reassigned["previous_assignment"]["run_id"] == first["run_id"]
    assert reassigned["previous_assignment"]["state"] == "revoked"
    assert reassigned["assignment"]["run_id"] == second["run_id"]
    assert reassigned["assignment"]["state"] == "active"
    assert "first-key" not in json.dumps(reassigned)
    assert "second-key" not in json.dumps(reassigned)

    with pytest.raises(ReservationAdmissionError, match="STALE_ASSIGNMENT_GENERATION"):
        service.reassign(
            packet_id=first["packet_id"],
            authority=_authority(authority_revision=6, lease_id="lease-152", fence_token=6),
            expected_generation=1,
            predecessor_run_id=first["run_id"],
        )


def test_runtime_discovery_cannot_grant_mutation_authority(tmp_path: Path) -> None:
    task = PlannerTask(
        task_id="alpha",
        outcome="Implement alpha",
        owned_paths=("src/alpha/**",),
        acceptance_checks=("done",),
        required_capabilities=("code.change.implement",),
    )
    request = _request(task)
    plan = PlannerService().plan(request)
    service = WorkPacketService(
        state_root=tmp_path,
        project_boundary=tmp_path,
        resolve_runtime=lambda _capabilities: [
            _candidate(grants_mutation_authority=True)
        ],
        token_factory=lambda: "key",
    )
    with pytest.raises(ReservationAdmissionError, match="RUNTIME_DISCOVERY_AUTHORITY_CONFLICT"):
        service.issue(
            request=request, plan=plan, task_id="alpha", authority=_authority()
        )


def test_planner_request_snapshots_mutable_base_input() -> None:
    exact_base = {"commit_sha": SHA, "tree_sha": TREE}
    task = PlannerTask(
        task_id="alpha",
        outcome="Alpha",
        owned_paths=("src/alpha/**",),
        acceptance_checks=("done",),
    )
    request = PlannerRequest(
        project_id="kis-mcp",
        change_id="150-parallel-agent-coordinator",
        work_id="issue-250",
        slice_id="250",
        revision=1,
        exact_base=exact_base,
        tasks=(task,),
    )
    first = PlannerService().plan(request)
    exact_base["commit_sha"] = "c" * 40
    assert PlannerService().plan(request) == first


def test_hotspot_edges_block_integration_owner_without_explicit_dependency() -> None:
    request = _request(
        PlannerTask(
            task_id="alpha",
            outcome="Alpha",
            owned_paths=("src/alpha/**",),
            shared_paths=("SPEC.md",),
            integration_owner="integrate",
            acceptance_checks=("done",),
        ),
        PlannerTask(
            task_id="beta",
            outcome="Beta",
            owned_paths=("src/beta/**",),
            shared_paths=("SPEC.md",),
            integration_owner="integrate",
            acceptance_checks=("done",),
        ),
        PlannerTask(
            task_id="integrate",
            outcome="Integrate canonical file",
            owned_paths=("docs/integration-note.md",),
            acceptance_checks=("integrated",),
        ),
    )
    plan = PlannerService().plan(request)
    assert plan["ready_frontier"] == ["alpha", "beta"]
    assert {tuple(sorted(edge.items())) for edge in plan["edges"]} >= {
        tuple(sorted({"from": "alpha", "to": "integrate", "kind": "integrates_with"}.items())),
        tuple(sorted({"from": "beta", "to": "integrate", "kind": "integrates_with"}.items())),
    }


def test_combined_dependency_and_hotspot_cycle_is_rejected() -> None:
    request = _request(
        PlannerTask(
            task_id="alpha",
            outcome="Alpha",
            owned_paths=("src/alpha/**",),
            shared_paths=("SPEC.md",),
            dependencies=("integrate",),
            integration_owner="integrate",
            acceptance_checks=("done",),
        ),
        PlannerTask(
            task_id="beta",
            outcome="Beta",
            owned_paths=("src/beta/**",),
            shared_paths=("SPEC.md",),
            integration_owner="integrate",
            acceptance_checks=("done",),
        ),
        PlannerTask(
            task_id="integrate",
            outcome="Integrate canonical file",
            owned_paths=("docs/integration-note.md",),
            acceptance_checks=("integrated",),
        ),
    )
    with pytest.raises(ReservationAdmissionError, match="PLANNER_EXECUTION_CYCLE"):
        PlannerService().plan(request)
