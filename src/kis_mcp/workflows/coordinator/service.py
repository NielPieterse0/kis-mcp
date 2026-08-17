from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from kis_mcp.paths import is_within_windows_boundary

from .models import ReservationAdmissionError, ReservationRequest, ReservationResult


ListClaims = Callable[[], list[dict[str, Any]]]
CreateChange = Callable[[dict[str, Any]], Mapping[str, Any]]
ResolveBase = Callable[[str], Mapping[str, str]]
WorkClaim = Callable[[dict[str, Any]], Mapping[str, Any]]
WorkRelease = Callable[[dict[str, Any]], Mapping[str, Any]]

_ACTIVE_JOURNAL_STATES = frozenset({"pending", "reserved", "degraded"})
_CHANGE_ID = re.compile(r"^(?P<sequence>[0-9]+)-[a-z0-9]+(?:-[a-z0-9]+)*$")


class ReservationService:
    def __init__(
        self,
        *,
        repository: Path,
        state_root: Path,
        project_boundary: Path,
        list_claims: ListClaims,
        create_change: CreateChange,
        resolve_base: ResolveBase,
        claim_work: WorkClaim | None = None,
        release_work: WorkRelease | None = None,
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
        self._create_change = create_change
        self._resolve_base = resolve_base
        self._claim_work = claim_work
        self._release_work = release_work

    def reserve(self, request: ReservationRequest) -> ReservationResult:
        if request.work_management is not None and self._claim_work is None:
            raise ReservationAdmissionError(
                "WORK_CLAIM_ADAPTER_REQUIRED",
                "Work Management metadata requires an execution-claim adapter.",
            )
        if request.work_management is not None and self._release_work is None:
            raise ReservationAdmissionError(
                "WORK_RELEASE_ADAPTER_REQUIRED",
                "Work Management admission requires a compensation adapter.",
            )
        if request.shared_paths and not (request.dependencies or request.integration_owner):
            raise ReservationAdmissionError(
                "SHARED_PATH_COORDINATION_REQUIRED",
                "Shared paths require an explicit dependency or integration owner.",
            )

        with self._admission_lock():
            claims = self._combined_active_claims()
            sequence = self._next_sequence(claims)
            if sequence > 999:
                raise ReservationAdmissionError(
                    "CHANGE_SEQUENCE_EXHAUSTED",
                    "The governed three-digit change sequence has reached its maximum value.",
                )
            change_id = f"{sequence:03d}-{request.slug}"
            base = _base_identity(self._resolve_base(request.base))
            reservation_id = f"res-{uuid.uuid4().hex}"
            lease_id = f"lease-{uuid.uuid4().hex}"
            candidate = self._candidate_claim(request, change_id)
            component = _candidate_degraded_component(
                candidate, _find_degraded_components(claims)
            )
            if component is not None:
                raise ReservationAdmissionError(
                    "DEGRADED_COMPONENT_INTERSECTION",
                    f"Reservation intersects degraded component {component['component_id']}.",
                )
            _validate_candidate(candidate, claims)

            event_root = self._event_root(reservation_id)
            pending = self._journal_event(
                event_root,
                1,
                "pending",
                request,
                change_id,
                sequence,
                reservation_id,
                lease_id,
                base,
            )
            self._write_event(event_root, 1, "pending", pending)

            work_claim: Mapping[str, Any] | None = None
            created: Mapping[str, Any] | None = None
            try:
                if request.work_management is not None:
                    work_claim = _validated_work_claim(
                        self._claim_work(  # type: ignore[misc]
                            self._work_claim_payload(pending)
                        )
                    )
                create_payload = self._create_payload(request, change_id, base)
                created = self._create_change(create_payload)
                self._verify_created_claim(change_id, create_payload)
            except Exception as exc:
                state = (
                    "degraded"
                    if created is not None
                    else self._compensate_work_claim(pending, work_claim)
                )
                self._write_event(
                    event_root,
                    2,
                    state,
                    {
                        **pending,
                        "state": state,
                        "error": _bounded_error(exc),
                        "work_management_claim": (
                            dict(work_claim) if work_claim is not None else None
                        ),
                        "created": dict(created) if created is not None else None,
                    },
                )
                if isinstance(exc, ReservationAdmissionError):
                    raise
                raise ReservationAdmissionError(
                    "RESERVATION_TRANSACTION_FAILED",
                    _bounded_error(exc),
                ) from exc

            reservation = {
                "schema_version": 1,
                "contract": "coordinator-reservation-v1",
                "reservation_id": reservation_id,
                "project_id": request.project_id,
                "change_id": change_id,
                "change_sequence": sequence,
                "base": base,
                "owned_paths": list(request.owned_paths),
                "shared_paths": list(request.shared_paths),
                "dependencies": list(request.dependencies),
                "integration_owner": request.integration_owner or change_id,
                "authority_revision": 1,
                "lease_id": lease_id,
                "fence_token": 1,
                "status": "reserved",
            }
            final_event = {
                **pending,
                "state": "reserved",
                "reservation": reservation,
                "work_management_claim": dict(work_claim) if work_claim else None,
                "created": dict(created),
            }
            self._write_event(event_root, 2, "reserved", final_event)
            work_packet_identity = {
                "project_id": request.project_id,
                "change_id": change_id,
                "exact_base": base,
                "authority": {
                    "reservation_id": reservation_id,
                    "authority_revision": 1,
                    "lease_id": lease_id,
                    "fence_token": 1,
                },
            }
            return ReservationResult(
                reservation=reservation,
                work_packet_identity=work_packet_identity,
                branch=f"change/{change_id}",
                worktree=f".work/worktrees/{change_id}",
                work_management_claim=work_claim,
            )

    def _combined_active_claims(self) -> list[dict[str, Any]]:
        claims = [dict(item) for item in self._list_claims()]
        known = {str(item.get("change_id")) for item in claims}
        for event in self._latest_journal_events():
            if event.get("state") not in _ACTIVE_JOURNAL_STATES:
                continue
            journal_claim = _claim_from_event(event)
            change_id = str(journal_claim.get("change_id", ""))
            if not change_id or change_id in known:
                continue
            claims.append(journal_claim)
            known.add(change_id)
        return claims

    def _next_sequence(self, claims: Sequence[Mapping[str, Any]]) -> int:
        maximum = 0
        for claim in claims:
            match = _CHANGE_ID.fullmatch(str(claim.get("change_id", "")))
            if match:
                maximum = max(maximum, int(match.group("sequence")))
        maximum = max(maximum, self._historical_sequence_floor())
        for event in self._latest_journal_events():
            value = event.get("change_sequence")
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ReservationAdmissionError(
                    "RESERVATION_JOURNAL_INVALID",
                    "Reservation journal change_sequence must be a positive integer.",
                )
            maximum = max(maximum, value)
        return maximum + 1

    def _historical_sequence_floor(self) -> int:
        changes_root = self._repository / ".work" / "changes"
        if not changes_root.is_dir():
            return 0
        maximum = 0
        for scope_path in sorted(changes_root.glob("*/scope.json")):
            if scope_path.parent.name.startswith("_"):
                continue
            try:
                payload = json.loads(scope_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ReservationAdmissionError(
                    "RESERVATION_SEQUENCE_EVIDENCE_INVALID",
                    f"Cannot read historical change identity from {scope_path}: {exc}",
                ) from exc
            if not isinstance(payload, dict):
                raise ReservationAdmissionError(
                    "RESERVATION_SEQUENCE_EVIDENCE_INVALID",
                    f"Historical change scope {scope_path} is not an object.",
                )
            match = _CHANGE_ID.fullmatch(str(payload.get("change_id", "")))
            if match:
                maximum = max(maximum, int(match.group("sequence")))
        return maximum

    def _event_root(self, reservation_id: str) -> Path:
        return self._state_root / "coordinator" / "reservations" / reservation_id

    def _latest_journal_events(self) -> list[dict[str, Any]]:
        root = self._state_root / "coordinator" / "reservations"
        if not root.is_dir():
            return []
        events: list[dict[str, Any]] = []
        for reservation_root in sorted(path for path in root.iterdir() if path.is_dir()):
            candidates = _sorted_journal_paths(reservation_root)
            if not candidates:
                continue
            try:
                loaded = json.loads(candidates[-1].read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ReservationAdmissionError(
                    "RESERVATION_JOURNAL_INVALID",
                    f"Cannot read {candidates[-1]}: {exc}",
                ) from exc
            if not isinstance(loaded, dict):
                raise ReservationAdmissionError(
                    "RESERVATION_JOURNAL_INVALID",
                    f"Journal event {candidates[-1]} is not an object.",
                )
            events.append(loaded)
        return events

    def _write_event(
        self,
        event_root: Path,
        ordinal: int,
        state: str,
        payload: Mapping[str, Any],
    ) -> None:
        event_root.mkdir(parents=True, exist_ok=True)
        path = event_root / f"{ordinal:03d}-{state}.json"
        try:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(dict(payload), stream, indent=2, sort_keys=True)
                stream.write("\n")
        except FileExistsError as exc:
            raise ReservationAdmissionError(
                "RESERVATION_JOURNAL_COLLISION",
                f"Journal event already exists: {path}",
            ) from exc

    def _journal_event(
        self,
        _event_root: Path,
        _ordinal: int,
        state: str,
        request: ReservationRequest,
        change_id: str,
        sequence: int,
        reservation_id: str,
        lease_id: str,
        base: Mapping[str, str],
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "contract": "coordinator-reservation-journal-event-v1",
            "state": state,
            "reservation_id": reservation_id,
            "project_id": request.project_id,
            "change_id": change_id,
            "change_sequence": sequence,
            "outcome": request.outcome,
            "base": dict(base),
            "owned_paths": list(request.owned_paths),
            "shared_paths": list(request.shared_paths),
            "dependencies": list(request.dependencies),
            "integration_owner": request.integration_owner or change_id,
            "work_management": (
                dict(request.work_management)
                if request.work_management is not None
                else None
            ),
            "lease_id": lease_id,
            "authority_revision": 1,
            "fence_token": 1,
        }

    def _candidate_claim(
        self,
        request: ReservationRequest,
        change_id: str,
    ) -> dict[str, Any]:
        return {
            "change_id": change_id,
            "branch": f"change/{change_id}",
            "worktree": f".work/worktrees/{change_id}",
            "outcome": request.outcome,
            "owned_paths": list(request.owned_paths),
            "shared_paths": list(request.shared_paths),
            "dependencies": list(request.dependencies),
            "integration_owner": request.integration_owner or change_id,
        }

    def _create_payload(
        self,
        request: ReservationRequest,
        change_id: str,
        base: Mapping[str, str],
    ) -> dict[str, Any]:
        return {
            "change_id": change_id,
            "outcome": request.outcome,
            "owned_paths": list(request.owned_paths),
            "shared_paths": list(request.shared_paths),
            "excluded_paths": list(request.excluded_paths),
            "dependencies": list(request.dependencies),
            "integration_owner": request.integration_owner or change_id,
            "complexity": request.complexity,
            "risk_triggers": list(request.risk_triggers),
            "base": request.base,
            "exact_base": dict(base),
            "work_management": (
                dict(request.work_management)
                if request.work_management is not None
                else None
            ),
        }

    def _work_claim_payload(self, pending: Mapping[str, Any]) -> dict[str, Any]:
        work_management = pending.get("work_management")
        if not isinstance(work_management, Mapping):
            raise ReservationAdmissionError(
                "WORK_MANAGEMENT_METADATA_INCOMPLETE",
                "Configured Work Management admission is missing record metadata.",
            )
        return {
            "project_id": pending["project_id"],
            "change_id": pending["change_id"],
            "change_sequence": pending["change_sequence"],
            "reservation_id": pending["reservation_id"],
            "exact_base": dict(pending["base"]),
            "work_management": dict(work_management),
        }

    def _verify_created_claim(
        self,
        change_id: str,
        expected: Mapping[str, Any],
    ) -> None:
        matches = [
            claim
            for claim in self._list_claims()
            if claim.get("change_id") == change_id
        ]
        if len(matches) != 1:
            raise ReservationAdmissionError(
                "GOVERNED_CHANGE_NOT_OBSERVED",
                f"Expected one active governed claim for {change_id}; found {len(matches)}.",
            )
        observed = matches[0]
        for field in ("outcome", "owned_paths", "shared_paths", "dependencies", "integration_owner"):
            if observed.get(field) != expected.get(field):
                raise ReservationAdmissionError(
                    "GOVERNED_CHANGE_IDENTITY_MISMATCH",
                    f"Observed {field} differs for {change_id}.",
                )
        observed_base = observed.get("base_evidence")
        expected_base = expected.get("exact_base")
        if not isinstance(observed_base, Mapping) or not isinstance(expected_base, Mapping):
            raise ReservationAdmissionError(
                "GOVERNED_CHANGE_BASE_EVIDENCE_MISSING",
                f"Exact governed base evidence is missing for {change_id}.",
            )
        if {
            "commit_sha": observed_base.get("local_sha"),
            "tree_sha": observed_base.get("local_tree"),
        } != dict(expected_base):
            raise ReservationAdmissionError(
                "GOVERNED_CHANGE_BASE_MISMATCH",
                f"Governed change {change_id} was created from a different exact base.",
            )

    def _compensate_work_claim(
        self,
        pending: Mapping[str, Any],
        work_claim: Mapping[str, Any] | None,
    ) -> str:
        if work_claim is None:
            return "aborted"
        try:
            released = self._release_work(  # type: ignore[misc]
                {
                    "change_id": pending["change_id"],
                    "claim": dict(work_claim),
                    "work_management": pending.get("work_management"),
                }
            )
            _require_successful_work_mutation(released, code="WORK_RELEASE_FAILED")
        except Exception:
            return "degraded"
        return "aborted"

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


def _base_identity(value: Mapping[str, str]) -> dict[str, str]:
    commit = str(value.get("commit_sha", "")).lower()
    tree = str(value.get("tree_sha", "")).lower()
    for label, sha in (("commit_sha", commit), ("tree_sha", tree)):
        if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
            raise ReservationAdmissionError(
                "BASE_IDENTITY_INVALID",
                f"{label} must be an exact 40-character lowercase Git SHA.",
            )
    return {"commit_sha": commit, "tree_sha": tree}


def _bounded_error(exc: Exception) -> str:
    detail = str(exc).strip() or exc.__class__.__name__
    return detail[:1000]


def _journal_ordinal(path: Path) -> int:
    prefix, separator, _rest = path.name.partition("-")
    if not separator:
        raise ReservationAdmissionError(
            "RESERVATION_JOURNAL_INVALID",
            f"Journal event name has no ordinal separator: {path.name}",
        )
    try:
        ordinal = int(prefix)
    except ValueError as exc:
        raise ReservationAdmissionError(
            "RESERVATION_JOURNAL_INVALID",
            f"Journal event name has an invalid ordinal: {path.name}",
        ) from exc
    if ordinal < 1:
        raise ReservationAdmissionError(
            "RESERVATION_JOURNAL_INVALID",
            f"Journal event ordinal must be positive: {path.name}",
        )
    return ordinal


def _sorted_journal_paths(root: Path) -> list[Path]:
    return sorted(root.glob("*.json"), key=lambda path: (_journal_ordinal(path), path.name))


def _claim_from_event(event: Mapping[str, Any]) -> dict[str, Any]:
    reservation = event.get("reservation")
    source = reservation if isinstance(reservation, Mapping) else event
    change_id = str(source["change_id"])
    return {
        "change_id": change_id,
        "branch": f"change/{change_id}",
        "worktree": f".work/worktrees/{change_id}",
        "outcome": event.get("outcome", ""),
        "owned_paths": list(source.get("owned_paths", ())),
        "shared_paths": list(source.get("shared_paths", ())),
        "dependencies": list(source.get("dependencies", ())),
        "integration_owner": source.get("integration_owner"),
    }


def _validate_candidate(
    candidate: Mapping[str, Any],
    existing: Sequence[Mapping[str, Any]],
) -> None:
    candidate_outcome = _normalize_outcome(str(candidate["outcome"]))
    for current in existing:
        if candidate["change_id"] == current.get("change_id"):
            _raise("DUPLICATE_CHANGE_ID", str(candidate["change_id"]))
        if candidate["branch"] == current.get("branch"):
            _raise("DUPLICATE_ACTIVE_BRANCH", str(candidate["branch"]))
        if candidate["worktree"] == current.get("worktree"):
            _raise("DUPLICATE_ACTIVE_WORKTREE", str(candidate["worktree"]))
        if candidate_outcome == _normalize_outcome(str(current.get("outcome", ""))):
            _raise("DUPLICATE_ACTIVE_OUTCOME", str(candidate["outcome"]))
        _validate_path_conflicts(candidate, current)


def _validate_path_conflicts(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> None:
    left_owned = [_path_claim(item) for item in left.get("owned_paths", ())]
    left_shared = [_path_claim(item) for item in left.get("shared_paths", ())]
    right_owned = [_path_claim(item) for item in right.get("owned_paths", ())]
    right_shared = [_path_claim(item) for item in right.get("shared_paths", ())]

    for owned in left_owned:
        if any(_overlaps(owned, item) for item in (*right_owned, *right_shared)):
            _raise("EXCLUSIVE_PATH_OVERLAP", owned[0])
    for owned in right_owned:
        if any(_overlaps(owned, item) for item in left_shared):
            _raise("EXCLUSIVE_PATH_OVERLAP", owned[0])
    for shared in left_shared:
        for other in right_shared:
            if _overlaps(shared, other) and not _coordinated(left, right):
                _raise("UNCOORDINATED_SHARED_PATH", shared[0])

def _claim_conflict_paths(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> set[str]:
    left_owned = [_path_claim(item) for item in left.get("owned_paths", ())]
    left_shared = [_path_claim(item) for item in left.get("shared_paths", ())]
    right_owned = [_path_claim(item) for item in right.get("owned_paths", ())]
    right_shared = [_path_claim(item) for item in right.get("shared_paths", ())]
    conflicts: set[str] = set()

    for owned in left_owned:
        for other in (*right_owned, *right_shared):
            if _overlaps(owned, other):
                conflicts.update((owned[0], other[0]))
    for owned in right_owned:
        for other in left_shared:
            if _overlaps(owned, other):
                conflicts.update((owned[0], other[0]))
    if not _coordinated(left, right):
        for shared in left_shared:
            for other in right_shared:
                if _overlaps(shared, other):
                    conflicts.update((shared[0], other[0]))
    return conflicts


def _find_degraded_components(
    claims: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    adjacency: dict[int, set[int]] = {}
    edge_paths: dict[tuple[int, int], set[str]] = {}
    for left_index in range(len(claims)):
        for right_index in range(left_index + 1, len(claims)):
            conflicts = _claim_conflict_paths(
                claims[left_index], claims[right_index]
            )
            if not conflicts:
                continue
            adjacency.setdefault(left_index, set()).add(right_index)
            adjacency.setdefault(right_index, set()).add(left_index)
            edge_paths[(left_index, right_index)] = conflicts

    components: list[dict[str, Any]] = []
    visited: set[int] = set()
    for start in sorted(adjacency):
        if start in visited:
            continue
        pending = [start]
        members: set[int] = set()
        while pending:
            current = pending.pop()
            if current in members:
                continue
            members.add(current)
            pending.extend(adjacency.get(current, ()))
        visited.update(members)
        affected: set[str] = set()
        for (left_index, right_index), paths in edge_paths.items():
            if left_index in members and right_index in members:
                affected.update(paths)
        change_ids = sorted(str(claims[index].get("change_id", "")) for index in members)
        affected_paths = sorted(affected)
        stable = json.dumps(
            {"change_ids": change_ids, "affected_paths": affected_paths},
            sort_keys=True,
            separators=(",", ":"),
        )
        components.append(
            {
                "component_id": f"cmp-{hashlib.sha256(stable.encode('utf-8')).hexdigest()[:16]}",
                "change_ids": change_ids,
                "affected_paths": affected_paths,
                "reason": "conflicting active path claims",
                "disjoint_admission": "allowed",
            }
        )
    return sorted(components, key=lambda item: item["component_id"])


def _candidate_degraded_component(
    candidate: Mapping[str, Any], components: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    candidate_paths = [
        _path_claim(item)
        for item in (*candidate.get("owned_paths", ()), *candidate.get("shared_paths", ()))
    ]
    for component in components:
        affected = [_path_claim(item) for item in component.get("affected_paths", ())]
        if any(_overlaps(candidate_path, path) for candidate_path in candidate_paths for path in affected):
            return component
    return None


def _coordinated(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_id = str(left.get("change_id", ""))
    right_id = str(right.get("change_id", ""))
    left_dependencies = set(str(item) for item in left.get("dependencies", ()))
    right_dependencies = set(str(item) for item in right.get("dependencies", ()))
    if left_id in right_dependencies or right_id in left_dependencies:
        return True
    left_owner = left.get("integration_owner")
    right_owner = right.get("integration_owner")
    if left_owner and left_owner == right_owner:
        return True
    if left_owner == right_id or right_owner == left_id:
        return True
    return False


def _path_claim(value: Any) -> tuple[str, str, bool]:
    if not isinstance(value, str) or not value.strip():
        _raise("CHANGE_PATH_PATTERN_INVALID", str(value))
    normalized = value.strip().replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        _raise("CHANGE_PATH_PATTERN_INVALID", normalized)
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _raise("CHANGE_PATH_PATTERN_INVALID", normalized)
    recursive = normalized.endswith("/**")
    if "*" in normalized and not recursive:
        _raise("CHANGE_PATH_PATTERN_INVALID", normalized)
    prefix = normalized[:-3] if recursive else normalized
    if not prefix or "*" in prefix:
        _raise("CHANGE_PATH_PATTERN_INVALID", normalized)
    return normalized, prefix, recursive


def _overlaps(left: tuple[str, str, bool], right: tuple[str, str, bool]) -> bool:
    _, left_prefix, left_recursive = left
    _, right_prefix, right_recursive = right
    if not left_recursive and not right_recursive:
        return left_prefix == right_prefix
    if left_recursive and right_recursive:
        return _descendant(left_prefix, right_prefix) or _descendant(right_prefix, left_prefix)
    recursive = left if left_recursive else right
    exact = right if left_recursive else left
    return _descendant(exact[1], recursive[1])


def _descendant(path: str, parent: str) -> bool:
    return path == parent or path.startswith(f"{parent}/")


def _normalize_outcome(value: str) -> str:
    return " ".join(value.casefold().split())


def _validated_work_claim(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    _require_successful_work_mutation(payload, code="WORK_CLAIM_FAILED")
    if payload.get("phase") != "active":
        raise ReservationAdmissionError(
            "WORK_CLAIM_NOT_ACTIVE",
            "Work Management claim did not reach the Active phase.",
        )
    return dict(payload)


def _require_successful_work_mutation(
    payload: Mapping[str, Any],
    *,
    code: str,
) -> None:
    if not isinstance(payload, Mapping) or payload.get("mode") != "apply":
        raise ReservationAdmissionError(code, "Work Management mutation was not applied.")
    outcomes = payload.get("outcomes")
    if not isinstance(outcomes, Sequence) or isinstance(
        outcomes, (str, bytes, bytearray)
    ) or not outcomes:
        raise ReservationAdmissionError(code, "Work Management mutation returned no outcomes.")
    for outcome in outcomes:
        if not isinstance(outcome, Mapping) or outcome.get("success") is not True:
            raise ReservationAdmissionError(code, "Work Management mutation was not successful.")


def _raise(code: str, detail: str) -> None:
    raise ReservationAdmissionError(code, detail)


__all__ = [
    "CreateChange",
    "ListClaims",
    "ReservationService",
    "ResolveBase",
    "WorkClaim",
    "WorkRelease",
]
