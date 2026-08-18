from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from kis_mcp.paths import is_within_windows_boundary

from .models import ReservationAdmissionError, ScopeRevisionRequest
from .service import (
    _claim_from_event,
    _find_degraded_components,
    _overlaps,
    _path_claim,
    _sorted_journal_paths,
    _validate_candidate,
)


ListClaims = Callable[[], list[dict[str, Any]]]
AmendChange = Callable[[dict[str, Any]], Mapping[str, Any]]
Clock = Callable[[], datetime]

_ACTIVE_EVENT_STATES = frozenset({"pending", "reserved", "degraded"})
_SCOPE_FIELDS = ("owned_paths", "shared_paths", "dependencies", "integration_owner")
_CAS_FIELDS = (
    "outcome",
    "owned_paths",
    "shared_paths",
    "excluded_paths",
    "dependencies",
    "integration_owner",
)
_CHANGE_ID = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")


class AuthorityService:
    def __init__(
        self,
        *,
        repository: Path,
        state_root: Path,
        project_boundary: Path,
        list_claims: ListClaims,
        amend_change: AmendChange | None,
        clock: Clock | None = None,
    ) -> None:
        self._repository = Path(repository).resolve(strict=False)
        self._state_root = Path(state_root).resolve(strict=False)
        self._project_boundary = Path(project_boundary).resolve(strict=False)
        for label, candidate in (
            ("repository", self._repository),
            ("state_root", self._state_root),
        ):
            if not is_within_windows_boundary(
                str(candidate), boundary=str(self._project_boundary)
            ):
                raise ReservationAdmissionError(
                    "COORDINATOR_WRITE_BOUNDARY_VIOLATION",
                    f"{label} must remain inside {self._project_boundary}.",
                )
        self._list_claims = list_claims
        self._amend_change = amend_change
        self._clock = clock or (lambda: datetime.now(UTC))

    def current_reservation(self, reservation_id: str) -> dict[str, Any]:
        with self._admission_lock():
            self._recover_scope_transition_locked(reservation_id)
            event = self._latest_event(reservation_id)
            return _event_reservation(event)

    def degraded_components(self) -> list[dict[str, Any]]:
        with self._admission_lock():
            self._recover_all_pending_locked()
            return _find_degraded_components(self._combined_claims())

    def activate_lease(
        self,
        reservation_id: str,
        holder_id: str,
        *,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        _require_non_empty(holder_id, "holder_id")
        ttl = _ttl(ttl_seconds)
        with self._admission_lock():
            self._recover_scope_transition_locked(reservation_id)
            event = self._latest_event(reservation_id)
            reservation = _event_reservation(event)
            current_lease = _event_lease(event)
            if current_lease is not None:
                code = (
                    "LEASE_ALREADY_ACTIVE"
                    if current_lease.get("status") == "active"
                    else "LEASE_REASSIGNMENT_REQUIRED"
                )
                raise ReservationAdmissionError(
                    code,
                    "An existing lease must be replaced through explicit reassignment.",
                )
            now = _utc(self._clock())
            lease = _lease_payload(
                reservation,
                holder_id=holder_id,
                lease_id=str(reservation["lease_id"]),
                issued_at=now,
                expires_at=now + ttl,
                status="active",
            )
            reservation["status"] = "active"
            self._append_event(
                reservation_id,
                _authority_event(
                    event,
                    reservation=reservation,
                    lease=lease,
                    event_type="lease_activated",
                ),
            )
            return lease

    def heartbeat_lease(
        self,
        reservation_id: str,
        *,
        holder_id: str,
        lease_id: str,
        authority_revision: int,
        fence_token: int,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        ttl = _ttl(ttl_seconds)
        with self._admission_lock():
            event = self._current_authority_event_locked(reservation_id)
            reservation, lease = self._require_authority_locked(
                event,
                holder_id=holder_id,
                lease_id=lease_id,
                authority_revision=authority_revision,
                fence_token=fence_token,
            )
            now = _utc(self._clock())
            heartbeat = {
                **lease,
                "expires_at": _timestamp(now + ttl),
                "status": "active",
            }
            self._append_event(
                reservation_id,
                _authority_event(
                    event,
                    reservation=reservation,
                    lease=heartbeat,
                    event_type="lease_heartbeat",
                ),
            )
            return heartbeat

    def assert_mutation_authority(
        self,
        reservation_id: str,
        *,
        holder_id: str,
        lease_id: str,
        authority_revision: int,
        fence_token: int,
    ) -> dict[str, Any]:
        with self._admission_lock():
            event = self._current_authority_event_locked(reservation_id)
            reservation, _lease = self._require_authority_locked(
                event,
                holder_id=holder_id,
                lease_id=lease_id,
                authority_revision=authority_revision,
                fence_token=fence_token,
            )
            return reservation

    def recover(self) -> list[dict[str, Any]]:
        recovered: list[dict[str, Any]] = []
        with self._admission_lock():
            self._recover_all_pending_locked()
            root = self._state_root / "coordinator" / "reservations"
            if not root.is_dir():
                return recovered
            for reservation_root in sorted(path for path in root.iterdir() if path.is_dir()):
                event = self._latest_event(reservation_root.name)
                lease = _event_lease(event)
                if lease is None or lease.get("status") != "active":
                    continue
                if _parse_timestamp(str(lease["expires_at"])) > _utc(self._clock()):
                    continue
                expired = {**lease, "status": "expired"}
                reservation = _event_reservation(event)
                reservation["status"] = "expired"
                self._append_event(
                    reservation_root.name,
                    _authority_event(
                        event,
                        reservation=reservation,
                        lease=expired,
                        event_type="lease_expired",
                    ),
                )
                recovered.append(expired)
        return recovered

    def reassign_lease(
        self,
        reservation_id: str,
        *,
        holder_id: str,
        expected_authority_revision: int,
        expected_fence_token: int,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        _require_non_empty(holder_id, "holder_id")
        ttl = _ttl(ttl_seconds)
        with self._admission_lock():
            event = self._current_authority_event_locked(reservation_id)
            reservation = _event_reservation(event)
            _require_expected_authority(
                reservation,
                expected_authority_revision,
                expected_fence_token,
            )
            previous_lease = _event_lease(event)
            now = _utc(self._clock())
            reservation["authority_revision"] += 1
            reservation["fence_token"] += 1
            reservation["lease_id"] = f"lease-{uuid.uuid4().hex}"
            reservation["status"] = "active"
            lease = _lease_payload(
                reservation,
                holder_id=holder_id,
                lease_id=str(reservation["lease_id"]),
                issued_at=now,
                expires_at=now + ttl,
                status="active",
            )
            payload = _authority_event(
                event,
                reservation=reservation,
                lease=lease,
                event_type="lease_reassigned",
            )
            if previous_lease is not None:
                payload["previous_lease"] = {**previous_lease, "status": "reassigned"}
            self._append_event(reservation_id, payload)
            return lease

    def amend_scope(self, request: ScopeRevisionRequest) -> dict[str, Any]:
        with self._admission_lock():
            self._recover_scope_transition_locked(request.reservation_id)
            event = self._latest_event(request.reservation_id)
            reservation = _event_reservation(event)
            _require_expected_authority(
                reservation,
                request.expected_authority_revision,
                request.expected_fence_token,
            )
            observed = self._governed_claim(str(reservation["change_id"]))
            current_claim = _claim_with_reservation(observed, reservation)
            if not _scope_matches(observed, current_claim):
                raise ReservationAdmissionError(
                    "GOVERNED_SCOPE_DIVERGED",
                    "Governed scope no longer matches the current coordinator authority.",
                )
            proposed_claim = _apply_scope_revision(current_claim, request)
            _validate_claim_shape(proposed_claim)
            _validate_scope_coordination(current_claim, proposed_claim, request)
            if _scope_matches(proposed_claim, current_claim):
                raise ReservationAdmissionError(
                    "SCOPE_REVISION_NO_CHANGE",
                    "Scope revision must change the effective governed scope.",
                )
            others = [
                claim
                for claim in self._combined_claims()
                if claim.get("change_id") != reservation["change_id"]
            ]
            _validate_candidate(proposed_claim, others)
            revision = _scope_revision_payload(request, status="proposed")
            proposed_reservation = {
                **reservation,
                "owned_paths": list(proposed_claim["owned_paths"]),
                "shared_paths": list(proposed_claim["shared_paths"]),
                "dependencies": list(proposed_claim["dependencies"]),
                "integration_owner": proposed_claim["integration_owner"],
                "authority_revision": request.expected_authority_revision + 1,
                "fence_token": request.expected_fence_token + 1,
            }
            current_lease = _event_lease(event)
            proposed_lease = (
                None
                if current_lease is None
                else {**current_lease, "fence_token": proposed_reservation["fence_token"]}
            )
            pending = _authority_event(
                event,
                reservation=reservation,
                lease=current_lease,
                event_type="scope_revision_proposed",
            )
            pending["scope_revision"] = revision
            pending["expected_claim"] = _cas_projection(current_claim)
            pending["proposed_claim"] = _cas_projection(proposed_claim)
            pending["proposed_reservation"] = proposed_reservation
            pending["proposed_lease"] = proposed_lease
            self._append_event(request.reservation_id, pending)
            adapter_error: Exception | None = None
            if self._amend_change is None:
                adapter_error = ReservationAdmissionError(
                    "GOVERNED_SCOPE_AMEND_ADAPTER_REQUIRED",
                    "Scope amendment requires a governed-scope CAS adapter.",
                )
            else:
                try:
                    self._amend_change(
                        {
                            "change_id": reservation["change_id"],
                            "expected_claim": _cas_projection(current_claim),
                            "proposed_claim": _cas_projection(proposed_claim),
                        }
                    )
                except Exception as exc:  # recovered from observed governance below
                    adapter_error = exc

            observed_after = self._governed_claim(str(reservation["change_id"]))
            if _cas_matches(observed_after, proposed_claim):
                accepted = {**revision, "status": "accepted"}
                final = _authority_event(
                    event,
                    reservation=proposed_reservation,
                    lease=proposed_lease,
                    event_type="scope_revision_accepted",
                )
                final["scope_revision"] = accepted
                self._append_event(request.reservation_id, final)
                return accepted
            rejected = {**revision, "status": "rejected"}
            final = _authority_event(
                event,
                reservation=reservation,
                lease=current_lease,
                event_type="scope_revision_rejected",
            )
            final["scope_revision"] = rejected
            if not _cas_matches(observed_after, current_claim):
                final["state"] = "degraded"
                final["recovery_error"] = "governed claim matches neither current nor proposed authority"
            self._append_event(request.reservation_id, final)
            if adapter_error is not None:
                if isinstance(adapter_error, ReservationAdmissionError):
                    raise adapter_error
                raise ReservationAdmissionError(
                    "GOVERNED_SCOPE_AMEND_FAILED", str(adapter_error)[:1000]
                ) from adapter_error
            raise ReservationAdmissionError(
                "GOVERNED_SCOPE_AMEND_NOT_OBSERVED",
                "Governed scope re-read did not match the proposed amendment.",
            )

    def _current_authority_event_locked(self, reservation_id: str) -> dict[str, Any]:
        self._recover_scope_transition_locked(reservation_id)
        self._expire_lease_locked(reservation_id)
        return self._latest_event(reservation_id)

    def _require_authority_locked(
        self,
        event: Mapping[str, Any],
        *,
        holder_id: str,
        lease_id: str,
        authority_revision: int,
        fence_token: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        reservation = _event_reservation(event)
        _require_expected_authority(reservation, authority_revision, fence_token)
        lease = _event_lease(event)
        if lease is None or lease.get("status") != "active":
            raise ReservationAdmissionError("LEASE_NOT_ACTIVE", "No active lease exists.")
        if lease.get("lease_id") != lease_id:
            raise ReservationAdmissionError("STALE_LEASE", "Lease ID is no longer current.")
        if lease.get("holder_id") != holder_id:
            raise ReservationAdmissionError("STALE_LEASE_HOLDER", "Lease holder is no longer current.")
        if lease.get("fence_token") != fence_token:
            raise ReservationAdmissionError("STALE_FENCE_TOKEN", "Lease fence token is stale.")
        if _parse_timestamp(str(lease["expires_at"])) <= _utc(self._clock()):
            raise ReservationAdmissionError("LEASE_EXPIRED", "Lease has expired.")
        return reservation, lease

    def _expire_lease_locked(self, reservation_id: str) -> dict[str, Any] | None:
        event = self._latest_event(reservation_id)
        lease = _event_lease(event)
        if lease is None or lease.get("status") != "active":
            return None
        if _parse_timestamp(str(lease["expires_at"])) > _utc(self._clock()):
            return None
        expired = {**lease, "status": "expired"}
        reservation = _event_reservation(event)
        reservation["status"] = "expired"
        self._append_event(
            reservation_id,
            _authority_event(
                event,
                reservation=reservation,
                lease=expired,
                event_type="lease_expired",
            ),
        )
        return expired

    def _recover_all_pending_locked(self) -> None:
        root = self._state_root / "coordinator" / "reservations"
        if not root.is_dir():
            return
        for reservation_root in sorted(path for path in root.iterdir() if path.is_dir()):
            self._recover_scope_transition_locked(reservation_root.name)

    def _recover_scope_transition_locked(self, reservation_id: str) -> None:
        event = self._latest_event(reservation_id)
        revision = event.get("scope_revision")
        proposed_reservation = event.get("proposed_reservation")
        if not isinstance(revision, Mapping) or revision.get("status") != "proposed":
            return
        if not isinstance(proposed_reservation, Mapping):
            raise ReservationAdmissionError(
                "SCOPE_TRANSITION_EVIDENCE_INVALID",
                "Proposed scope transition is missing proposed reservation evidence.",
            )
        current_reservation = _event_reservation(event)
        change_id = str(current_reservation["change_id"])
        observed = self._governed_claim(change_id)
        current_claim = _claim_with_reservation(observed, current_reservation)
        proposed_claim = _claim_with_reservation(observed, proposed_reservation)
        expected_evidence = event.get("expected_claim")
        proposed_evidence = event.get("proposed_claim")
        if isinstance(expected_evidence, Mapping) != isinstance(proposed_evidence, Mapping):
            raise ReservationAdmissionError(
                "SCOPE_TRANSITION_EVIDENCE_INVALID",
                "Scope transition must contain both expected and proposed CAS claim evidence.",
            )
        if isinstance(expected_evidence, Mapping) and isinstance(proposed_evidence, Mapping):
            proposed_matches = _cas_matches(observed, proposed_evidence)
            current_matches = _cas_matches(observed, expected_evidence)
        else:
            proposed_matches = _scope_matches(observed, proposed_claim)
            current_matches = _scope_matches(observed, current_claim)
        proposed_lease = event.get("proposed_lease")

        if proposed_matches:
            status = "accepted"
            reservation = dict(proposed_reservation)
            lease = dict(proposed_lease) if isinstance(proposed_lease, Mapping) else None
            event_type = "scope_revision_recovered_accepted"
        elif current_matches:
            status = "rejected"
            reservation = current_reservation
            lease = _event_lease(event)
            event_type = "scope_revision_recovered_rejected"
        else:
            status = "rejected"
            reservation = current_reservation
            lease = _event_lease(event)
            event_type = "scope_revision_recovery_degraded"
        final = _authority_event(
            event,
            reservation=reservation,
            lease=lease,
            event_type=event_type,
        )
        final["scope_revision"] = {**dict(revision), "status": status}
        if event_type.endswith("degraded"):
            final["state"] = "degraded"
            final["recovery_error"] = "governed scope matches neither transition endpoint"
        self._append_event(reservation_id, final)

    def _combined_claims(self) -> list[dict[str, Any]]:
        claims = [dict(item) for item in self._list_claims()]
        known = {str(item.get("change_id")) for item in claims}
        for event in self._latest_events():
            if event.get("state") not in _ACTIVE_EVENT_STATES:
                continue
            journal_claim = _claim_from_event(event)
            change_id = str(journal_claim.get("change_id", ""))
            if not change_id or change_id in known:
                continue
            claims.append(journal_claim)
            known.add(change_id)
        return claims

    def _governed_claim(self, change_id: str) -> dict[str, Any]:
        matches = [
            dict(claim)
            for claim in self._list_claims()
            if claim.get("change_id") == change_id
        ]
        if len(matches) != 1:
            raise ReservationAdmissionError(
                "GOVERNED_CHANGE_NOT_OBSERVED",
                f"Expected one governed claim for {change_id}; found {len(matches)}.",
            )
        return matches[0]

    def _latest_events(self) -> list[dict[str, Any]]:
        root = self._state_root / "coordinator" / "reservations"
        if not root.is_dir():
            return []
        return [
            self._latest_event(path.name)
            for path in sorted(candidate for candidate in root.iterdir() if candidate.is_dir())
        ]

    def _latest_event(self, reservation_id: str) -> dict[str, Any]:
        root = self._reservation_root(reservation_id)
        if not root.is_dir():
            raise ReservationAdmissionError(
                "RESERVATION_NOT_FOUND", f"Unknown reservation {reservation_id}."
            )
        candidates = _sorted_journal_paths(root)
        if not candidates:
            raise ReservationAdmissionError(
                "RESERVATION_JOURNAL_INVALID", f"Reservation {reservation_id} has no events."
            )
        try:
            payload = json.loads(candidates[-1].read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ReservationAdmissionError(
                "RESERVATION_JOURNAL_INVALID",
                f"Cannot read {candidates[-1]}: {exc}",
            ) from exc
        if not isinstance(payload, dict):
            raise ReservationAdmissionError(
                "RESERVATION_JOURNAL_INVALID",
                f"Journal event {candidates[-1]} is not an object.",
            )
        return payload

    def _append_event(self, reservation_id: str, payload: Mapping[str, Any]) -> None:
        root = self._reservation_root(reservation_id)
        root.mkdir(parents=True, exist_ok=True)
        candidates = _sorted_journal_paths(root)
        ordinal = 1
        if candidates:
            try:
                ordinal = int(candidates[-1].name.split("-", 1)[0]) + 1
            except ValueError as exc:
                raise ReservationAdmissionError(
                    "RESERVATION_JOURNAL_INVALID",
                    f"Invalid journal ordinal in {candidates[-1].name}.",
                ) from exc
        event_type = str(payload.get("event_type", "authority")).replace("_", "-")
        path = root / f"{ordinal:03d}-{event_type}.json"
        try:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(dict(payload), stream, indent=2, sort_keys=True)
                stream.write("\n")
        except FileExistsError as exc:
            raise ReservationAdmissionError(
                "RESERVATION_JOURNAL_COLLISION",
                f"Journal event already exists: {path}",
            ) from exc

    def _reservation_root(self, reservation_id: str) -> Path:
        _require_non_empty(reservation_id, "reservation_id")
        if any(character in reservation_id for character in ("/", "\\")):
            raise ReservationAdmissionError(
                "RESERVATION_ID_INVALID", "Reservation ID cannot contain path separators."
            )
        return self._state_root / "coordinator" / "reservations" / reservation_id

    @contextmanager
    def _admission_lock(self) -> Iterable[None]:
        lock_path = self._state_root / "coordinator" / "admission.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as stream:
            stream.seek(0)
            _lock_file(stream)
            try:
                stream.seek(0, os.SEEK_END)
                if stream.tell() == 0:
                    stream.write(b"0")
                    stream.flush()
                    os.fsync(stream.fileno())
                stream.seek(0)
                yield
            finally:
                _unlock_file(stream)


def _lock_file(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)


def _unlock_file(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _authority_event(
    source: Mapping[str, Any],
    *,
    reservation: Mapping[str, Any],
    lease: Mapping[str, Any] | None,
    event_type: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "contract": "coordinator-authority-journal-event-v1",
        "state": "reserved",
        "event_type": event_type,
        "reservation_id": reservation["reservation_id"],
        "project_id": reservation["project_id"],
        "change_id": reservation["change_id"],
        "change_sequence": reservation["change_sequence"],
        "outcome": source.get("outcome", ""),
        "owned_paths": list(reservation["owned_paths"]),
        "shared_paths": list(reservation["shared_paths"]),
        "dependencies": list(reservation["dependencies"]),
        "integration_owner": reservation["integration_owner"],
        "reservation": dict(reservation),
        "lease": None if lease is None else dict(lease),
    }


def _event_reservation(event: Mapping[str, Any]) -> dict[str, Any]:
    reservation = event.get("reservation")
    if not isinstance(reservation, Mapping):
        raise ReservationAdmissionError(
            "RESERVATION_NOT_FINALIZED",
            "Mutation authority requires a finalized reservation event.",
        )
    return dict(reservation)


def _event_lease(event: Mapping[str, Any]) -> dict[str, Any] | None:
    lease = event.get("lease")
    if lease is None:
        return None
    if not isinstance(lease, Mapping):
        raise ReservationAdmissionError(
            "LEASE_EVIDENCE_INVALID", "Lease evidence must be an object or null."
        )
    return dict(lease)


def _scope_revision_payload(
    request: ScopeRevisionRequest, *, status: str
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "contract": "coordinator-scope-revision-v1",
        "request_id": request.request_id,
        "reservation_id": request.reservation_id,
        "expected_authority_revision": request.expected_authority_revision,
        "proposed_authority_revision": request.expected_authority_revision + 1,
        "expected_fence_token": request.expected_fence_token,
        "changes": {
            "add_owned_paths": list(request.add_owned_paths),
            "remove_owned_paths": list(request.remove_owned_paths),
            "add_shared_paths": list(request.add_shared_paths),
            "remove_shared_paths": list(request.remove_shared_paths),
            "add_dependencies": list(request.add_dependencies),
            "remove_dependencies": list(request.remove_dependencies),
            "integration_owner": request.integration_owner,
        },
        "status": status,
    }


def _claim_with_reservation(
    observed: Mapping[str, Any], reservation: Mapping[str, Any]
) -> dict[str, Any]:
    claim = dict(observed)
    claim.update(
        {
            "owned_paths": list(reservation["owned_paths"]),
            "shared_paths": list(reservation["shared_paths"]),
            "dependencies": list(reservation["dependencies"]),
            "integration_owner": reservation["integration_owner"],
        }
    )
    return claim


def _scope_projection(claim: Mapping[str, Any]) -> dict[str, Any]:
    return {field: claim.get(field) for field in _SCOPE_FIELDS}


def _cas_projection(claim: Mapping[str, Any]) -> dict[str, Any]:
    return {field: claim.get(field) for field in _CAS_FIELDS}


def _scope_matches(observed: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(observed.get(field) == expected.get(field) for field in _SCOPE_FIELDS)


def _cas_matches(observed: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(observed.get(field) == expected.get(field) for field in _CAS_FIELDS)


def _apply_scope_revision(
    current: Mapping[str, Any], request: ScopeRevisionRequest
) -> dict[str, Any]:
    proposed = dict(current)
    proposed["owned_paths"] = _revise_values(
        current.get("owned_paths", ()),
        remove=request.remove_owned_paths,
        add=request.add_owned_paths,
    )
    proposed["shared_paths"] = _revise_values(
        current.get("shared_paths", ()),
        remove=request.remove_shared_paths,
        add=request.add_shared_paths,
    )
    proposed["dependencies"] = _revise_values(
        current.get("dependencies", ()),
        remove=request.remove_dependencies,
        add=request.add_dependencies,
    )
    if request.integration_owner is not None:
        proposed["integration_owner"] = request.integration_owner
    return proposed


def _revise_values(
    current: Sequence[Any], *, remove: Sequence[str], add: Sequence[str]
) -> list[str]:
    values = [str(item) for item in current if str(item) not in set(remove)]
    for item in add:
        if item not in values:
            values.append(item)
    return values


def _validate_claim_shape(claim: Mapping[str, Any]) -> None:
    owned = [_path_claim(item) for item in claim.get("owned_paths", ())]
    shared = [_path_claim(item) for item in claim.get("shared_paths", ())]
    excluded = [_path_claim(item) for item in claim.get("excluded_paths", ())]
    if not owned:
        raise ReservationAdmissionError(
            "GOVERNED_OWNED_PATHS_EMPTY",
            "Governed scope must retain at least one exclusive owned path.",
        )
    for owned_path in owned:
        if any(_overlaps(owned_path, shared_path) for shared_path in shared):
            raise ReservationAdmissionError(
                "CHANGE_PATH_CLAIM_CONTRADICTION",
                f"{owned_path[0]} cannot be both owned and shared.",
            )
        if any(_overlaps(owned_path, excluded_path) for excluded_path in excluded):
            raise ReservationAdmissionError(
                "CHANGE_PATH_CLAIM_CONTRADICTION",
                f"{owned_path[0]} cannot be both owned and excluded.",
            )
    for shared_path in shared:
        if any(_overlaps(shared_path, excluded_path) for excluded_path in excluded):
            raise ReservationAdmissionError(
                "CHANGE_PATH_CLAIM_CONTRADICTION",
                f"{shared_path[0]} cannot be both shared and excluded.",
            )
    dependencies = [str(item) for item in claim.get("dependencies", ())]
    if len(dependencies) != len(set(dependencies)):
        raise ReservationAdmissionError(
            "CHANGE_DEPENDENCIES_DUPLICATE", "Dependencies must be unique."
        )
    if any(_CHANGE_ID.fullmatch(item) is None for item in dependencies):
        raise ReservationAdmissionError(
            "CHANGE_ID_INVALID", "Dependencies must contain governed change IDs."
        )
    if str(claim.get("change_id", "")) in dependencies:
        raise ReservationAdmissionError(
            "CHANGE_DEPENDENCY_SELF", "A change cannot depend on itself."
        )
    integration_owner = claim.get("integration_owner")
    if integration_owner is not None and _CHANGE_ID.fullmatch(str(integration_owner)) is None:
        raise ReservationAdmissionError(
            "CHANGE_ID_INVALID", "integration_owner must be a governed change ID."
        )


def _validate_scope_coordination(
    current: Mapping[str, Any],
    proposed: Mapping[str, Any],
    request: ScopeRevisionRequest,
) -> None:
    if not request.add_shared_paths or current.get("shared_paths"):
        return
    dependencies = tuple(str(item) for item in proposed.get("dependencies", ()))
    change_id = str(proposed.get("change_id", ""))
    integration_owner = str(proposed.get("integration_owner", ""))
    if dependencies or (integration_owner and integration_owner != change_id):
        return
    raise ReservationAdmissionError(
        "SHARED_PATH_COORDINATION_REQUIRED",
        "Adding the first shared path requires an explicit dependency or external integration owner.",
    )


def _require_expected_authority(
    reservation: Mapping[str, Any], expected_revision: int, expected_fence: int
) -> None:
    if reservation.get("authority_revision") != expected_revision:
        raise ReservationAdmissionError(
            "STALE_AUTHORITY_REVISION", "Authority revision is no longer current."
        )
    if reservation.get("fence_token") != expected_fence:
        raise ReservationAdmissionError(
            "STALE_FENCE_TOKEN", "Fence token is no longer current."
        )


def _lease_payload(
    reservation: Mapping[str, Any],
    *,
    holder_id: str,
    lease_id: str,
    issued_at: datetime,
    expires_at: datetime,
    status: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "contract": "coordinator-lease-v1",
        "lease_id": lease_id,
        "reservation_id": reservation["reservation_id"],
        "holder_id": holder_id,
        "fence_token": reservation["fence_token"],
        "issued_at": _timestamp(issued_at),
        "expires_at": _timestamp(expires_at),
        "status": status,
    }


def _ttl(seconds: int) -> timedelta:
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= 86400:
        raise ValueError("ttl_seconds must be an integer from 1 to 86400")
    return timedelta(seconds=seconds)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("coordinator clock must return an aware datetime")
    return value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReservationAdmissionError(
            "LEASE_EVIDENCE_INVALID", f"Invalid lease timestamp {value}."
        ) from exc
    return _utc(parsed)


def _require_non_empty(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


__all__ = ["AmendChange", "AuthorityService", "Clock", "ListClaims"]
