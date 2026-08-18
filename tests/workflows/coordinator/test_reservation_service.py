from __future__ import annotations

import json
import multiprocessing
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.workflows.coordinator import (
    ReservationAdmissionError,
    ReservationRequest,
    ReservationService,
)


SHA_A = "a" * 40
SHA_B = "b" * 40


class FakeGovernance:
    def __init__(self) -> None:
        self.claims: list[dict[str, Any]] = []
        self.created: list[str] = []
        self._lock = threading.Lock()

    def list_claims(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self.claims]

    def create_change(self, request: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.created.append(request["change_id"])
            self.claims.append(
                {
                    "change_id": request["change_id"],
                    "branch": f"change/{request['change_id']}",
                    "worktree": f".work/worktrees/{request['change_id']}",
                    "outcome": request["outcome"],
                    "owned_paths": list(request["owned_paths"]),
                    "shared_paths": list(request["shared_paths"]),
                    "dependencies": list(request["dependencies"]),
                    "integration_owner": request["integration_owner"],
                    "base_evidence": {
                        "local_sha": SHA_A,
                        "local_tree": SHA_B,
                    },
                }
            )
        return {"worktree": f"C:/repo/.work/worktrees/{request['change_id']}"}


class FakeWorkClaims:
    def __init__(self) -> None:
        self.claimed: list[str] = []
        self.claim_payloads: list[dict[str, Any]] = []
        self.released: list[str] = []

    def claim(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.claimed.append(payload["change_id"])
        self.claim_payloads.append(dict(payload))
        return {
            "mode": "apply",
            "phase": "active",
            "outcomes": [{"success": True}],
        }

    def release(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.released.append(payload["change_id"])
        return {"mode": "apply", "outcomes": [{"success": True}]}


def request(
    slug: str,
    path: str,
    *,
    outcome: str | None = None,
    shared: bool = False,
    dependencies: tuple[str, ...] = (),
    integration_owner: str | None = None,
    work_management: dict[str, Any] | None = None,
) -> ReservationRequest:
    return ReservationRequest(
        project_id="kis-mcp",
        slug=slug,
        outcome=outcome or f"Implement {slug}",
        owned_paths=() if shared else (path,),
        shared_paths=(path,) if shared else (),
        dependencies=dependencies,
        integration_owner=integration_owner,
        work_management=work_management,
    )


def service(tmp_path: Path, governance: FakeGovernance, work: FakeWorkClaims | None = None) -> ReservationService:
    return ReservationService(
        repository=tmp_path,
        state_root=tmp_path / "state",
        project_boundary=tmp_path,
        list_claims=governance.list_claims,
        create_change=governance.create_change,
        resolve_base=lambda _base: {"commit_sha": SHA_A, "tree_sha": SHA_B},
        claim_work=None if work is None else work.claim,
        release_work=None if work is None else work.release,
    )


def test_conflicting_concurrent_reservations_admit_exactly_one(tmp_path: Path) -> None:
    governance = FakeGovernance()
    reservation_service = service(tmp_path, governance)

    def reserve(index: int) -> str:
        try:
            return reservation_service.reserve(request(f"race-{index}", "src/shared.py")).status
        except ReservationAdmissionError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))

    assert results.count("reserved") == 1
    assert results.count("EXCLUSIVE_PATH_OVERLAP") == 1
    assert len(governance.created) == 1


def test_disjoint_concurrent_reservations_all_succeed_with_unique_sequences(tmp_path: Path) -> None:
    governance = FakeGovernance()
    reservation_service = service(tmp_path, governance)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(
                lambda index: reservation_service.reserve(
                    request(f"disjoint-{index}", f"src/{index}.py")
                ),
                range(4),
            )
        )

    assert all(result.status == "reserved" for result in results)
    assert len({result.reservation["change_sequence"] for result in results}) == 4
    assert len({result.reservation["change_id"] for result in results}) == 4


def test_sequence_advances_past_existing_governed_changes(tmp_path: Path) -> None:
    governance = FakeGovernance()
    governance.claims.append(
        {
            "change_id": "219-existing",
            "branch": "change/219-existing",
            "worktree": ".work/worktrees/219-existing",
            "outcome": "Existing",
            "owned_paths": ["src/existing.py"],
            "shared_paths": [],
            "dependencies": [],
            "integration_owner": None,
        }
    )
    result = service(tmp_path, governance).reserve(request("next", "src/next.py"))

    assert result.reservation["change_sequence"] == 220
    assert result.reservation["change_id"] == "220-next"


def test_shared_claim_requires_explicit_coordination(tmp_path: Path) -> None:
    governance = FakeGovernance()
    reservation_service = service(tmp_path, governance)

    with pytest.raises(ReservationAdmissionError) as captured:
        reservation_service.reserve(request("shared", "docs/shared.md", shared=True))

    assert captured.value.code == "SHARED_PATH_COORDINATION_REQUIRED"
    assert governance.created == []


def test_coordinated_shared_claims_can_overlap(tmp_path: Path) -> None:
    governance = FakeGovernance()
    reservation_service = service(tmp_path, governance)
    first = reservation_service.reserve(
        request(
            "owner",
            "docs/shared.md",
            shared=True,
            integration_owner="220-owner",
        )
    )
    second = reservation_service.reserve(
        request(
            "follower",
            "docs/shared.md",
            shared=True,
            dependencies=(first.reservation["change_id"],),
            integration_owner=first.reservation["change_id"],
        )
    )

    assert first.status == second.status == "reserved"


def test_work_management_claim_is_required_and_coupled_when_configured(tmp_path: Path) -> None:
    governance = FakeGovernance()
    metadata = {
        "project_id": "kis-mcp",
        "record_id": "SPEC-999",
        "source_repository": "NielPieterse0/kis-mcp",
        "source_number": 999,
        "source_kind": "issue",
        "documentation_impact": "planned",
    }

    with pytest.raises(ReservationAdmissionError) as captured:
        service(tmp_path, governance).reserve(
            request("claimed", "src/claimed.py", work_management=metadata)
        )
    assert captured.value.code == "WORK_CLAIM_ADAPTER_REQUIRED"

    work = FakeWorkClaims()
    result = service(tmp_path, governance, work).reserve(
        request("claimed", "src/claimed.py", work_management=metadata)
    )
    assert work.claimed == [result.reservation["change_id"]]
    assert work.claim_payloads[0]["work_management"] == metadata
    assert work.claim_payloads[0]["exact_base"] == {
        "commit_sha": SHA_A,
        "tree_sha": SHA_B,
    }
    assert result.work_management_claim == {
        "mode": "apply",
        "phase": "active",
        "outcomes": [{"success": True}],
    }


def test_success_returns_complete_bounded_authority_identity(tmp_path: Path) -> None:
    governance = FakeGovernance()
    result = service(tmp_path, governance).reserve(request("identity", "src/id.py"))

    reservation = result.reservation
    assert reservation["contract"] == "coordinator-reservation-v1"
    assert reservation["authority_revision"] == 1
    assert reservation["fence_token"] == 1
    assert reservation["base"] == {"commit_sha": SHA_A, "tree_sha": SHA_B}
    assert result.work_packet_identity == {
        "project_id": "kis-mcp",
        "change_id": reservation["change_id"],
        "exact_base": reservation["base"],
        "authority": {
            "reservation_id": reservation["reservation_id"],
            "authority_revision": 1,
            "lease_id": reservation["lease_id"],
            "fence_token": 1,
        },
    }


def test_sequence_never_reuses_closed_historical_change_identity(tmp_path: Path) -> None:
    governance = FakeGovernance()
    scope_root = tmp_path / ".work" / "changes" / "275-closed"
    scope_root.mkdir(parents=True)
    (scope_root / "scope.json").write_text(
        '{"change_id":"275-closed","status":"closed"}\n',
        encoding="utf-8",
    )

    result = service(tmp_path, governance).reserve(request("after-history", "src/new.py"))

    assert result.reservation["change_sequence"] == 276
    assert result.reservation["change_id"] == "276-after-history"


def test_duplicate_active_outcome_is_rejected_before_creation(tmp_path: Path) -> None:
    governance = FakeGovernance()
    governance.claims.append(
        {
            "change_id": "219-existing",
            "branch": "change/219-existing",
            "worktree": ".work/worktrees/219-existing",
            "outcome": "Same outcome",
            "owned_paths": ["src/existing.py"],
            "shared_paths": [],
            "dependencies": [],
            "integration_owner": "219-existing",
        }
    )

    with pytest.raises(ReservationAdmissionError) as captured:
        service(tmp_path, governance).reserve(
            request("duplicate", "src/new.py", outcome="  same   OUTCOME ")
        )

    assert captured.value.code == "DUPLICATE_ACTIVE_OUTCOME"
    assert governance.created == []


def test_successful_reservation_conforms_to_slice_one_contract(tmp_path: Path) -> None:
    governance = FakeGovernance()
    result = service(tmp_path, governance).reserve(request("schema", "src/schema.py"))
    root = Path(__file__).parents[3]
    schema = json.loads(
        (root / "contracts" / "coordinator" / "reservation.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(dict(result.reservation))


def test_coordinator_state_cannot_escape_declared_project_boundary(tmp_path: Path) -> None:
    governance = FakeGovernance()
    outside = tmp_path.parent / "outside-coordinator-state"

    with pytest.raises(ReservationAdmissionError) as captured:
        ReservationService(
            repository=tmp_path,
            state_root=outside,
            project_boundary=tmp_path,
            list_claims=governance.list_claims,
            create_change=governance.create_change,
            resolve_base=lambda _base: {"commit_sha": SHA_A, "tree_sha": SHA_B},
        )

    assert captured.value.code == "COORDINATOR_WRITE_BOUNDARY_VIOLATION"


def test_governed_base_mismatch_fails_closed_as_degraded(tmp_path: Path) -> None:
    class WrongBaseGovernance(FakeGovernance):
        def create_change(self, request: dict[str, Any]) -> dict[str, Any]:
            result = super().create_change(request)
            self.claims[-1]["base_evidence"] = {
                "local_sha": "c" * 40,
                "local_tree": SHA_B,
            }
            return result

    governance = WrongBaseGovernance()
    reservation_service = service(tmp_path, governance)

    with pytest.raises(ReservationAdmissionError) as captured:
        reservation_service.reserve(request("moved-base", "src/base.py"))

    assert captured.value.code == "GOVERNED_CHANGE_BASE_MISMATCH"
    events = list((tmp_path / "state" / "coordinator" / "reservations").glob("*/002-degraded.json"))
    assert len(events) == 1
    payload = json.loads(events[0].read_text(encoding="utf-8"))
    assert payload["state"] == "degraded"
    assert payload["created"] is not None


def _process_reservation_worker(root_text: str, slug: str, result_queue: Any) -> None:
    root = Path(root_text)
    claims_path = root / "claims.json"

    def list_claims() -> list[dict[str, Any]]:
        if not claims_path.is_file():
            return []
        return json.loads(claims_path.read_text(encoding="utf-8"))

    def create_change(payload: dict[str, Any]) -> dict[str, Any]:
        claims = list_claims()
        claims.append(
            {
                "change_id": payload["change_id"],
                "branch": f"change/{payload['change_id']}",
                "worktree": f".work/worktrees/{payload['change_id']}",
                "outcome": payload["outcome"],
                "owned_paths": list(payload["owned_paths"]),
                "shared_paths": list(payload["shared_paths"]),
                "dependencies": list(payload["dependencies"]),
                "integration_owner": payload["integration_owner"],
                "base_evidence": {"local_sha": SHA_A, "local_tree": SHA_B},
            }
        )
        claims_path.write_text(json.dumps(claims), encoding="utf-8")
        return {"worktree": f"C:/repo/.work/worktrees/{payload['change_id']}"}

    reservation_service = ReservationService(
        repository=root,
        state_root=root / "state",
        project_boundary=root,
        list_claims=list_claims,
        create_change=create_change,
        resolve_base=lambda _base: {"commit_sha": SHA_A, "tree_sha": SHA_B},
    )
    try:
        result = reservation_service.reserve(
            request(slug, "src/cross-process-shared.py")
        )
        result_queue.put(result.status)
    except ReservationAdmissionError as exc:
        result_queue.put(exc.code)


def test_cross_process_exclusive_race_has_exactly_one_winner(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_process_reservation_worker,
            args=(str(tmp_path), f"process-{index}", result_queue),
        )
        for index in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0

    results = [result_queue.get(timeout=5) for _ in processes]
    assert results.count("reserved") == 1
    assert results.count("EXCLUSIVE_PATH_OVERLAP") == 1


def test_malformed_journal_sequence_fails_closed(tmp_path: Path) -> None:
    governance = FakeGovernance()
    event_root = tmp_path / "state" / "coordinator" / "reservations" / "res-malformed"
    event_root.mkdir(parents=True)
    (event_root / "001-pending.json").write_text(
        json.dumps(
            {
                "state": "pending",
                "change_id": "300-malformed",
                "change_sequence": "300",
                "outcome": "Malformed evidence",
                "owned_paths": ["src/malformed.py"],
                "shared_paths": [],
                "dependencies": [],
                "integration_owner": "300-malformed",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReservationAdmissionError) as captured:
        service(tmp_path, governance).reserve(request("next", "src/next.py"))

    assert captured.value.code == "RESERVATION_JOURNAL_INVALID"


def test_work_claim_must_be_applied_and_active(tmp_path: Path) -> None:
    class PreviewWork(FakeWorkClaims):
        def claim(self, payload: dict[str, Any]) -> dict[str, Any]:
            self.claimed.append(payload["change_id"])
            return {"mode": "preview", "outcomes": [{"success": True}]}

    metadata = {
        "project_id": "kis-mcp",
        "record_id": "SPEC-999",
        "source_repository": "NielPieterse0/kis-mcp",
        "source_number": 999,
        "source_kind": "issue",
        "documentation_impact": "planned",
    }
    governance = FakeGovernance()

    with pytest.raises(ReservationAdmissionError) as captured:
        service(tmp_path, governance, PreviewWork()).reserve(
            request("preview-claim", "src/claim.py", work_management=metadata)
        )

    assert captured.value.code == "WORK_CLAIM_FAILED"
    assert governance.created == []


def test_failed_work_release_marks_failed_creation_degraded(tmp_path: Path) -> None:
    class FailingGovernance(FakeGovernance):
        def create_change(self, request: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("governed creation failed")

    class FailedRelease(FakeWorkClaims):
        def release(self, payload: dict[str, Any]) -> dict[str, Any]:
            self.released.append(payload["change_id"])
            return {"mode": "apply", "outcomes": [{"success": False}]}

    metadata = {
        "project_id": "kis-mcp",
        "record_id": "SPEC-999",
        "source_repository": "NielPieterse0/kis-mcp",
        "source_number": 999,
        "source_kind": "issue",
        "documentation_impact": "planned",
    }
    work = FailedRelease()
    with pytest.raises(ReservationAdmissionError):
        service(tmp_path, FailingGovernance(), work).reserve(
            request("failed-release", "src/release.py", work_management=metadata)
        )
    events = list((tmp_path / "state" / "coordinator" / "reservations").glob("*/002-degraded.json"))
    assert len(events) == 1
    assert work.released
