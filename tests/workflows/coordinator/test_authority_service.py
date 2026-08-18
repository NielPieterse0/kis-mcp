from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.workflows.coordinator import (
    AuthorityService,
    ReservationAdmissionError,
    ReservationRequest,
    ReservationService,
    ScopeRevisionRequest,
)


SHA_A = "a" * 40
SHA_B = "b" * 40


class FakeGovernance:
    def __init__(self) -> None:
        self.claims: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def list_claims(self) -> list[dict[str, Any]]:
        with self._lock:
            return [json.loads(json.dumps(item)) for item in self.claims]
    def create_change(self, request: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.claims.append(
                {
                    "change_id": request["change_id"],
                    "branch": f"change/{request['change_id']}",
                    "worktree": f".work/worktrees/{request['change_id']}",
                    "outcome": request["outcome"],
                    "owned_paths": list(request["owned_paths"]),
                    "shared_paths": list(request["shared_paths"]),
                    "excluded_paths": list(request["excluded_paths"]),
                    "dependencies": list(request["dependencies"]),
                    "integration_owner": request["integration_owner"],
                    "base_evidence": {"local_sha": SHA_A, "local_tree": SHA_B},
                }
            )
        return {"worktree": f"C:/repo/.work/worktrees/{request['change_id']}"}

    def amend_change(self, request: dict[str, Any]) -> dict[str, Any]:
        expected = request["expected_claim"]
        proposed = request["proposed_claim"]
        with self._lock:
            matches = [item for item in self.claims if item["change_id"] == request["change_id"]]
            if len(matches) != 1:
                raise RuntimeError("governed claim not found")
            claim = matches[0]
            for field in (
                "outcome",
                "owned_paths",
                "shared_paths",
                "excluded_paths",
                "dependencies",
                "integration_owner",
            ):
                if claim.get(field) != expected.get(field):
                    raise RuntimeError("governed claim changed before amendment")
            for field in ("owned_paths", "shared_paths", "dependencies", "integration_owner"):
                claim[field] = json.loads(json.dumps(proposed[field]))
        return {"mode": "apply", "success": True}


class Clock:
    def __init__(self) -> None:
        self.current = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> None:
        self.current += timedelta(seconds=seconds)


def reservation_service(root: Path, governance: FakeGovernance) -> ReservationService:
    return ReservationService(
        repository=root,
        state_root=root / "state",
        project_boundary=root,
        list_claims=governance.list_claims,
        create_change=governance.create_change,
        resolve_base=lambda _base: {"commit_sha": SHA_A, "tree_sha": SHA_B},
    )


def authority_service(
    root: Path, governance: FakeGovernance, clock: Clock
) -> AuthorityService:
    return AuthorityService(
        repository=root,
        state_root=root / "state",
        project_boundary=root,
        list_claims=governance.list_claims,
        amend_change=governance.amend_change,
        clock=clock,
    )


def reserve(root: Path, governance: FakeGovernance, slug: str, path: str) -> dict[str, Any]:
    result = reservation_service(root, governance).reserve(
        ReservationRequest(
            project_id="kis-mcp",
            slug=slug,
            outcome=f"Implement {slug}",
            owned_paths=(path,),
        )
    )
    return dict(result.reservation)


def revision_request(
    reservation: dict[str, Any], *, request_id: str, old_path: str, new_path: str
) -> ScopeRevisionRequest:
    return ScopeRevisionRequest(
        request_id=request_id,
        reservation_id=reservation["reservation_id"],
        expected_authority_revision=reservation["authority_revision"],
        expected_fence_token=reservation["fence_token"],
        add_owned_paths=(new_path,),
        remove_owned_paths=(old_path,),
    )


def schema(root: Path, name: str) -> dict[str, Any]:
    return json.loads(
        (root / "contracts" / "coordinator" / f"{name}.schema.json").read_text(
            encoding="utf-8"
        )
    )


def test_concurrent_scope_amendment_accepts_one_revision_and_rejects_stale_writer(
    tmp_path: Path,
) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "cas", "src/old.py")
    authority = authority_service(tmp_path, governance, Clock())

    requests = [
        revision_request(
            current,
            request_id=f"scope-{index}",
            old_path="src/old.py",
            new_path=f"src/new-{index}.py",
        )
        for index in range(2)
    ]

    def amend(item: ScopeRevisionRequest) -> str:
        try:
            return str(authority.amend_scope(item)["status"])
        except ReservationAdmissionError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(amend, requests))

    assert outcomes.count("accepted") == 1
    assert outcomes.count("STALE_AUTHORITY_REVISION") == 1
    claim = governance.list_claims()[0]
    assert claim["owned_paths"] in (["src/new-0.py"], ["src/new-1.py"])


def test_scope_revision_re_reads_governed_claim_and_matches_contract(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "contract", "src/old.py")
    authority = authority_service(tmp_path, governance, Clock())

    result = authority.amend_scope(
        revision_request(
            current,
            request_id="scope-contract",
            old_path="src/old.py",
            new_path="src/new.py",
        )
    )

    assert result["status"] == "accepted"
    assert result["proposed_authority_revision"] == 2
    assert authority.current_reservation(current["reservation_id"])["owned_paths"] == [
        "src/new.py"
    ]
    root = Path(__file__).parents[3]
    Draft202012Validator(schema(root, "scope-revision")).validate(result)


def test_lease_activation_and_heartbeat_require_exact_current_authority(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "lease", "src/lease.py")
    clock = Clock()
    authority = authority_service(tmp_path, governance, clock)

    lease = authority.activate_lease(current["reservation_id"], "worker-a", ttl_seconds=30)
    clock.advance(10)
    heartbeat = authority.heartbeat_lease(
        current["reservation_id"],
        holder_id="worker-a",
        lease_id=lease["lease_id"],
        authority_revision=1,
        fence_token=1,
        ttl_seconds=30,
    )

    assert heartbeat["status"] == "active"
    assert heartbeat["expires_at"] > lease["expires_at"]
    root = Path(__file__).parents[3]
    Draft202012Validator(schema(root, "lease")).validate(heartbeat)


def test_restart_recovery_expires_then_reassigns_with_higher_fence(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "recovery", "src/recovery.py")
    clock = Clock()
    first = authority_service(tmp_path, governance, clock)
    old_lease = first.activate_lease(current["reservation_id"], "worker-a", ttl_seconds=10)
    clock.advance(11)

    restarted = authority_service(tmp_path, governance, clock)
    recovered = restarted.recover()
    assert [item["status"] for item in recovered] == ["expired"]

    new_lease = restarted.reassign_lease(
        current["reservation_id"],
        holder_id="worker-b",
        expected_authority_revision=1,
        expected_fence_token=1,
        ttl_seconds=30,
    )
    reservation = restarted.current_reservation(current["reservation_id"])
    assert reservation["authority_revision"] == 2
    assert reservation["fence_token"] == 2
    assert new_lease["lease_id"] != old_lease["lease_id"]
    assert new_lease["fence_token"] == 2

    with pytest.raises(ReservationAdmissionError):
        restarted.assert_mutation_authority(
            current["reservation_id"],
            holder_id="worker-a",
            lease_id=old_lease["lease_id"],
            authority_revision=1,
            fence_token=1,
        )
    restarted.assert_mutation_authority(
        current["reservation_id"],
        holder_id="worker-b",
        lease_id=new_lease["lease_id"],
        authority_revision=2,
        fence_token=2,
    )


def test_degraded_component_blocks_intersection_but_not_disjoint_reservation(
    tmp_path: Path,
) -> None:
    governance = FakeGovernance()
    first = reserve(tmp_path, governance, "first", "src/shared.py")
    governance.claims.append(
        {
            "change_id": "900-invalid",
            "branch": "change/900-invalid",
            "worktree": ".work/worktrees/900-invalid",
            "outcome": "Invalid overlapping claim",
            "owned_paths": ["src/shared.py"],
            "shared_paths": [],
            "excluded_paths": [],
            "dependencies": [],
            "integration_owner": "900-invalid",
            "base_evidence": {"local_sha": SHA_A, "local_tree": SHA_B},
        }
    )
    authority = authority_service(tmp_path, governance, Clock())
    components = authority.degraded_components()
    assert len(components) == 1
    assert components[0]["affected_paths"] == ["src/shared.py"]

    with pytest.raises(ReservationAdmissionError) as captured:
        reservation_service(tmp_path, governance).reserve(
            ReservationRequest(
                project_id="kis-mcp",
                slug="intersecting",
                outcome="Intersect degraded component",
                owned_paths=("src/shared.py",),
            )
        )
    assert captured.value.code == "DEGRADED_COMPONENT_INTERSECTION"

    disjoint = reservation_service(tmp_path, governance).reserve(
        ReservationRequest(
            project_id="kis-mcp",
            slug="disjoint",
            outcome="Disjoint work",
            owned_paths=("docs/disjoint.md",),
        )
    )
    assert disjoint.status == "reserved"
    assert first["reservation_id"]


def test_scope_repair_removes_degraded_component(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "repair", "src/shared.py")
    governance.claims.append(
        {
            "change_id": "901-invalid",
            "branch": "change/901-invalid",
            "worktree": ".work/worktrees/901-invalid",
            "outcome": "Invalid overlap",
            "owned_paths": ["src/shared.py"],
            "shared_paths": [],
            "excluded_paths": [],
            "dependencies": [],
            "integration_owner": "901-invalid",
            "base_evidence": {"local_sha": SHA_A, "local_tree": SHA_B},
        }
    )
    authority = authority_service(tmp_path, governance, Clock())
    assert authority.degraded_components()

    result = authority.amend_scope(
        revision_request(
            current,
            request_id="repair-conflict",
            old_path="src/shared.py",
            new_path="src/repaired.py",
        )
    )

    assert result["status"] == "accepted"
    assert authority.degraded_components() == []


def test_scope_amendment_requires_governed_re_read_match(tmp_path: Path) -> None:
    class NonApplyingGovernance(FakeGovernance):
        def amend_change(self, request: dict[str, Any]) -> dict[str, Any]:
            return {"mode": "apply", "success": True}

    governance = NonApplyingGovernance()
    current = reserve(tmp_path, governance, "reread", "src/old.py")
    authority = authority_service(tmp_path, governance, Clock())

    with pytest.raises(ReservationAdmissionError) as captured:
        authority.amend_scope(
            revision_request(
                current,
                request_id="missing-reread",
                old_path="src/old.py",
                new_path="src/new.py",
            )
        )
    assert captured.value.code == "GOVERNED_SCOPE_AMEND_NOT_OBSERVED"


def test_expired_lease_cannot_be_reactivated_with_old_identity(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "expired", "src/expired.py")
    clock = Clock()
    authority = authority_service(tmp_path, governance, clock)
    authority.activate_lease(current["reservation_id"], "worker-a", ttl_seconds=5)
    clock.advance(6)
    authority.recover()

    with pytest.raises(ReservationAdmissionError) as captured:
        authority.activate_lease(current["reservation_id"], "worker-a", ttl_seconds=5)
    assert captured.value.code == "LEASE_REASSIGNMENT_REQUIRED"


def test_scope_revision_rejects_add_remove_overlap_before_authority_change(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "overlap", "src/current.py")
    authority = authority_service(tmp_path, governance, Clock())

    with pytest.raises(ValueError, match="owned_paths cannot add and remove"):
        ScopeRevisionRequest(
            request_id="scope-overlap",
            reservation_id=current["reservation_id"],
            expected_authority_revision=1,
            expected_fence_token=1,
            add_owned_paths=("src/same.py",),
            remove_owned_paths=("src/same.py",),
        )

    assert authority.current_reservation(current["reservation_id"])["authority_revision"] == 1


def test_scope_revision_rejects_effective_noop_without_fence_bump(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "noop", "src/current.py")
    authority = authority_service(tmp_path, governance, Clock())

    with pytest.raises(ReservationAdmissionError) as captured:
        authority.amend_scope(
            ScopeRevisionRequest(
                request_id="scope-noop",
                reservation_id=current["reservation_id"],
                expected_authority_revision=1,
                expected_fence_token=1,
                add_owned_paths=("src/current.py",),
            )
        )

    assert captured.value.code == "SCOPE_REVISION_NO_CHANGE"
    reservation = authority.current_reservation(current["reservation_id"])
    assert reservation["authority_revision"] == 1
    assert reservation["fence_token"] == 1


def test_scope_amendment_rejects_owned_path_that_overlaps_excluded_scope(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "excluded", "src/allowed.py")
    governance.claims[0]["excluded_paths"] = ["src/forbidden/**"]
    authority = authority_service(tmp_path, governance, Clock())

    with pytest.raises(ReservationAdmissionError) as captured:
        authority.amend_scope(
            revision_request(
                current,
                request_id="excluded-overlap",
                old_path="src/allowed.py",
                new_path="src/forbidden/new.py",
            )
        )
    assert captured.value.code == "CHANGE_PATH_CLAIM_CONTRADICTION"
    assert governance.list_claims()[0]["owned_paths"] == ["src/allowed.py"]


def test_journal_ordering_remains_numeric_after_three_digit_ordinals(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "journal-order", "src/journal.py")
    clock = Clock()
    authority = authority_service(tmp_path, governance, clock)
    event_root = tmp_path / "state" / "coordinator" / "reservations" / current["reservation_id"]
    baseline = json.loads((event_root / "002-reserved.json").read_text(encoding="utf-8"))

    older = json.loads(json.dumps(baseline))
    older["reservation"]["authority_revision"] = 9
    older["reservation"]["fence_token"] = 9
    newer = json.loads(json.dumps(baseline))
    newer["reservation"]["authority_revision"] = 10
    newer["reservation"]["fence_token"] = 10
    (event_root / "999-authority.json").write_text(json.dumps(older), encoding="utf-8")
    (event_root / "1000-authority.json").write_text(json.dumps(newer), encoding="utf-8")

    observed = authority.current_reservation(current["reservation_id"])
    assert observed["authority_revision"] == 10
    assert observed["fence_token"] == 10
    lease = authority.activate_lease(current["reservation_id"], "worker-a", ttl_seconds=30)
    assert lease["fence_token"] == 10
    assert (event_root / "1001-lease-activated.json").is_file()


@pytest.mark.parametrize(
    "overrides",
    [
        {"add_dependencies": ("not-a-governed-id",)},
        {"integration_owner": "not-a-governed-id"},
    ],
)
def test_scope_amendment_rejects_invalid_governed_change_ids(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "ids", "src/ids.py")
    authority = authority_service(tmp_path, governance, Clock())
    revision = ScopeRevisionRequest(
        request_id="invalid-id",
        reservation_id=current["reservation_id"],
        expected_authority_revision=1,
        expected_fence_token=1,
        add_owned_paths=("src/extra.py",),
        **overrides,
    )

    with pytest.raises(ReservationAdmissionError) as captured:
        authority.amend_scope(revision)
    assert captured.value.code == "CHANGE_ID_INVALID"
    assert governance.list_claims()[0]["owned_paths"] == ["src/ids.py"]


def test_scope_revision_requires_explicit_coordination_for_first_shared_path(tmp_path: Path) -> None:
    governance = FakeGovernance()
    current = reserve(tmp_path, governance, "shared-revision", "src/current.py")
    authority = authority_service(tmp_path, governance, Clock())

    with pytest.raises(ReservationAdmissionError) as captured:
        authority.amend_scope(
            ScopeRevisionRequest(
                request_id="shared-without-coordination",
                reservation_id=current["reservation_id"],
                expected_authority_revision=1,
                expected_fence_token=1,
                add_shared_paths=("src/shared.py",),
            )
        )
    assert captured.value.code == "SHARED_PATH_COORDINATION_REQUIRED"
    assert governance.list_claims()[0]["shared_paths"] == []

    accepted = authority.amend_scope(
        ScopeRevisionRequest(
            request_id="shared-with-owner",
            reservation_id=current["reservation_id"],
            expected_authority_revision=1,
            expected_fence_token=1,
            add_shared_paths=("src/shared.py",),
            integration_owner="777-integration",
        )
    )
    assert accepted["status"] == "accepted"
    claim = governance.list_claims()[0]
    assert claim["shared_paths"] == ["src/shared.py"]
    assert claim["integration_owner"] == "777-integration"


def test_scope_cas_rejects_concurrent_excluded_path_change(tmp_path: Path) -> None:
    class ExcludedRaceGovernance(FakeGovernance):
        def amend_change(self, request: dict[str, Any]) -> dict[str, Any]:
            with self._lock:
                claim = next(item for item in self.claims if item["change_id"] == request["change_id"])
                claim["excluded_paths"] = ["src/raced/**"]
            return super().amend_change(request)

    governance = ExcludedRaceGovernance()
    current = reserve(tmp_path, governance, "cas-excluded", "src/current.py")
    authority = authority_service(tmp_path, governance, Clock())

    with pytest.raises(ReservationAdmissionError) as captured:
        authority.amend_scope(
            revision_request(
                current,
                request_id="cas-excluded",
                old_path="src/current.py",
                new_path="src/new.py",
            )
        )
    assert captured.value.code == "GOVERNED_SCOPE_AMEND_FAILED"
    claim = governance.list_claims()[0]
    assert claim["owned_paths"] == ["src/current.py"]
    assert claim["excluded_paths"] == ["src/raced/**"]
    event_root = tmp_path / "state" / "coordinator" / "reservations" / current["reservation_id"]
    latest = json.loads(sorted(event_root.glob("*.json"))[-1].read_text(encoding="utf-8"))
    assert latest["state"] == "degraded"


def test_restart_recovery_uses_persisted_full_cas_claim_evidence(tmp_path: Path) -> None:
    class CrashAfterApplyGovernance(FakeGovernance):
        def amend_change(self, request: dict[str, Any]) -> dict[str, Any]:
            super().amend_change(request)
            with self._lock:
                claim = next(item for item in self.claims if item["change_id"] == request["change_id"])
                claim["excluded_paths"] = ["src/raced/**"]
            raise SystemExit("simulated crash after governed mutation")

    governance = CrashAfterApplyGovernance()
    current = reserve(tmp_path, governance, "recover-cas", "src/current.py")
    clock = Clock()
    authority = authority_service(tmp_path, governance, clock)

    with pytest.raises(SystemExit):
        authority.amend_scope(
            revision_request(
                current,
                request_id="recover-cas",
                old_path="src/current.py",
                new_path="src/new.py",
            )
        )

    restarted = authority_service(tmp_path, governance, clock)
    reservation = restarted.current_reservation(current["reservation_id"])
    assert reservation["authority_revision"] == 1
    assert reservation["owned_paths"] == ["src/current.py"]
    event_root = tmp_path / "state" / "coordinator" / "reservations" / current["reservation_id"]
    latest = json.loads(sorted(event_root.glob("*.json"))[-1].read_text(encoding="utf-8"))
    assert latest["event_type"] == "scope_revision_recovery_degraded"
    assert latest["state"] == "degraded"
