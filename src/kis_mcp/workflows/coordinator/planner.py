from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from kis_mcp.paths import is_within_windows_boundary

from .models import (
    PlannerRequest,
    PlannerTask,
    ReservationAdmissionError,
)
from .service import _overlaps, _path_claim


ResolveRuntime = Callable[[tuple[str, ...]], Sequence[Mapping[str, Any]]]
TokenFactory = Callable[[], str]
Clock = Callable[[], datetime]

_REQUIRED_HANDOFF_FIELDS = tuple(
    sorted(
        (
            "authority_revision",
            "changed_paths",
            "evidence",
            "exact_head",
            "fence_token",
            "handoff_id",
            "observed_at",
            "packet_id",
            "reservation_id",
            "residual_state",
            "runtime_binding",
            "status",
            "worker_id",
        )
    )
)


class PlannerService:
    def plan(self, request: PlannerRequest) -> dict[str, Any]:
        tasks = {task.task_id: task for task in request.tasks}
        exact_base = _git_identity(request.exact_base)
        _validate_dependencies(tasks)
        hotspots = _validate_scope_topology(tasks)

        nodes = {
            task_id: _node(tasks[task_id])
            for task_id in sorted(tasks)
        }
        edges = _edges(tasks, hotspots)
        _validate_execution_edges(tasks, edges)
        blocked = {edge["to"] for edge in edges}
        ready_frontier = sorted(task_id for task_id in tasks if task_id not in blocked)
        recommended_concurrency = _recommended_concurrency(
            ready_frontier, tasks
        )
        return {
            "schema_version": 1,
            "contract": "coordinator-dependency-dag-v1",
            "project_id": request.project_id,
            "change_id": request.change_id,
            "revision": request.revision,
            "nodes": nodes,
            "edges": edges,
            "ready_frontier": ready_frontier,
            "integration_hotspots": hotspots,
            "recommended_concurrency": recommended_concurrency,
            "validation": {
                "status": "validated",
                "evidence": [
                    "dependency endpoints resolved",
                    "dependency graph acyclic",
                    "exclusive ownership unambiguous",
                    "shared hotspots have one integration owner",
                    f"exact base {exact_base['commit_sha']}",
                ],
            },
        }


class WorkPacketService:
    def __init__(
        self,
        *,
        state_root: Path,
        project_boundary: Path,
        resolve_runtime: ResolveRuntime,
        token_factory: TokenFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._state_root = Path(state_root).resolve(strict=False)
        self._project_boundary = Path(project_boundary).resolve(strict=False)
        if not is_within_windows_boundary(
            str(self._state_root), boundary=str(self._project_boundary)
        ):
            raise ReservationAdmissionError(
                "COORDINATOR_WRITE_BOUNDARY_VIOLATION",
                f"state_root must remain inside {self._project_boundary}.",
            )
        self._resolve_runtime = resolve_runtime
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._clock = clock or (lambda: datetime.now(UTC))

    def issue(
        self,
        *,
        request: PlannerRequest,
        plan: Mapping[str, Any],
        task_id: str,
        authority: Mapping[str, Any],
    ) -> dict[str, Any]:
        _validate_plan_identity(request, plan)
        tasks = {task.task_id: task for task in request.tasks}
        task = tasks.get(task_id)
        if task is None:
            raise ReservationAdmissionError(
                "WORK_PACKET_TASK_NOT_FOUND", f"Unknown planner task {task_id}."
            )
        nodes = plan.get("nodes")
        if not isinstance(nodes, Mapping) or task_id not in nodes:
            raise ReservationAdmissionError(
                "WORK_PACKET_PLAN_MISMATCH",
                f"Planner output does not contain task {task_id}.",
            )

        exact_base = _git_identity(request.exact_base)
        normalized_authority = _authority_identity(authority)
        binding = self._runtime_binding(task.required_capabilities)
        binding_ref = {
            "binding_id": binding["binding_id"],
            "binding_fingerprint": binding["binding_fingerprint"],
        }
        stable_identity = {
            "project_id": request.project_id,
            "change_id": request.change_id,
            "work_id": request.work_id,
            "slice_id": request.slice_id,
            "task_id": task.task_id,
            "outcome": task.outcome,
            "scope": {
                "owned_paths": sorted(task.owned_paths),
                "shared_paths": sorted(task.shared_paths),
                "integration_owner": task.integration_owner,
            },
            "dependencies": sorted(task.dependencies),
            "acceptance_checks": sorted(task.acceptance_checks),
            "exact_base": exact_base,
            "verification_requirement_ids": sorted(
                request.verification_requirement_ids
            ),
            "required_handoff_fields": list(_REQUIRED_HANDOFF_FIELDS),
        }
        packet_id = _stable_id("packet", stable_identity)
        packet_root = self._state_root / "coordinator" / "packets" / packet_id
        issued_path = packet_root / "001-issued.json"
        if issued_path.is_file():
            raise ReservationAdmissionError(
                "WORK_PACKET_ALREADY_ISSUED",
                f"Work packet {packet_id} already has durable issuance evidence.",
            )

        assignment_key = self._token_factory()
        if not isinstance(assignment_key, str) or not assignment_key.strip():
            raise ReservationAdmissionError(
                "ASSIGNMENT_KEY_INVALID", "Assignment key factory returned an invalid key."
            )
        issued_at = _timestamp(self._clock())
        packet = {
            "schema_version": 1,
            "contract": "coordinator-work-packet-v1",
            "packet_id": packet_id,
            "work_id": request.work_id,
            "project_id": request.project_id,
            "change_id": request.change_id,
            "slice_id": request.slice_id,
            "outcome": task.outcome,
            "scope": stable_identity["scope"],
            "dependencies": stable_identity["dependencies"],
            "acceptance_checks": stable_identity["acceptance_checks"],
            "exact_base": exact_base,
            "authority": normalized_authority,
            "runtime_binding": binding_ref,
            "verification_requirement_ids": stable_identity[
                "verification_requirement_ids"
            ],
            "required_handoff_fields": list(_REQUIRED_HANDOFF_FIELDS),
            "assignment": {"generation": 1, "key": assignment_key},
            "issued_at": issued_at,
        }
        self._persist_runtime_binding(binding)
        stored = {
            "schema_version": 1,
            "contract": "coordinator-work-packet-issued-v1",
            "packet_id": packet_id,
            "packet": {
                key: value
                for key, value in packet.items()
                if key != "assignment"
            },
            "assignment": {
                "generation": 1,
                "key_sha256": hashlib.sha256(
                    assignment_key.encode("utf-8")
                ).hexdigest(),
                "state": "active",
            },
            "issued_at": issued_at,
        }
        _write_json_once(issued_path, stored)
        return {"packet": packet, "runtime_binding": binding}

    def _runtime_binding(
        self, required_capabilities: tuple[str, ...]
    ) -> dict[str, Any]:
        required = tuple(sorted(required_capabilities))
        candidates = list(self._resolve_runtime(required))
        valid: list[dict[str, Any]] = []
        authority_conflict = False
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise ReservationAdmissionError(
                    "RUNTIME_BINDING_INVALID", "Runtime discovery returned a non-object candidate."
                )
            raw_capabilities = candidate.get("capabilities", ())
            if not isinstance(raw_capabilities, Sequence) or isinstance(
                raw_capabilities, (str, bytes, bytearray)
            ):
                raise ReservationAdmissionError(
                    "RUNTIME_BINDING_INVALID", "Runtime candidate capabilities must be an array."
                )
            if any(not isinstance(item, str) or not item.strip() for item in raw_capabilities):
                raise ReservationAdmissionError(
                    "RUNTIME_BINDING_INVALID", "Runtime capabilities must be non-empty strings."
                )
            capabilities = tuple(sorted(set(raw_capabilities)))
            if not set(required).issubset(capabilities):
                continue
            if candidate.get("grants_mutation_authority") is not False:
                authority_conflict = True
                continue
            valid.append(_normalize_runtime_candidate(candidate, capabilities))
        if not valid:
            code = (
                "RUNTIME_DISCOVERY_AUTHORITY_CONFLICT"
                if authority_conflict
                else "RUNTIME_BINDING_NOT_FOUND"
            )
            raise ReservationAdmissionError(
                code, "No safe exact runtime binding satisfies the required capabilities."
            )
        valid.sort(key=_canonical)
        chosen = valid[0]
        fingerprint = hashlib.sha256(_canonical(chosen).encode("utf-8")).hexdigest()
        return {**chosen, "binding_fingerprint": fingerprint}

    def _persist_runtime_binding(self, binding: Mapping[str, Any]) -> None:
        binding_id = str(binding["binding_id"])
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", binding_id) is None:
            raise ReservationAdmissionError(
                "RUNTIME_BINDING_INVALID", "binding_id is not safe for durable storage."
            )
        path = (
            self._state_root
            / "coordinator"
            / "runtime-bindings"
            / binding_id
            / f"{binding['binding_fingerprint']}.json"
        )
        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ReservationAdmissionError(
                    "RUNTIME_BINDING_EVIDENCE_INVALID", str(exc)[:1000]
                ) from exc
            if existing != dict(binding):
                raise ReservationAdmissionError(
                    "RUNTIME_BINDING_EVIDENCE_CONFLICT",
                    "Existing runtime binding fingerprint has different evidence.",
                )
            return
        _write_json_once(path, binding)


def _validate_dependencies(tasks: Mapping[str, PlannerTask]) -> None:
    for task in tasks.values():
        for dependency in task.dependencies:
            if dependency == task.task_id:
                raise ReservationAdmissionError(
                    "PLANNER_DEPENDENCY_SELF", f"Task {task.task_id} depends on itself."
                )
            if dependency not in tasks:
                raise ReservationAdmissionError(
                    "PLANNER_DEPENDENCY_NOT_FOUND",
                    f"Task {task.task_id} depends on unknown task {dependency}.",
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ReservationAdmissionError(
                "PLANNER_DEPENDENCY_CYCLE", "Dependency graph contains a cycle."
            )
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in tasks[task_id].dependencies:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(tasks):
        visit(task_id)


def _validate_scope_topology(
    tasks: Mapping[str, PlannerTask],
) -> list[dict[str, Any]]:
    for task in tasks.values():
        owned = [_path_claim(path) for path in task.owned_paths]
        shared = [_path_claim(path) for path in task.shared_paths]
        if shared and task.integration_owner is None:
            raise ReservationAdmissionError(
                "PLANNER_INTEGRATION_OWNER_REQUIRED",
                f"Task {task.task_id} has shared paths without an integration owner.",
            )
        if task.integration_owner is not None and task.integration_owner not in tasks:
            raise ReservationAdmissionError(
                "PLANNER_INTEGRATION_OWNER_NOT_FOUND",
                f"Task {task.task_id} names unknown integration owner {task.integration_owner}.",
            )
        if any(_overlaps(left, right) for left in owned for right in shared):
            raise ReservationAdmissionError(
                "PLANNER_TASK_SCOPE_CONTRADICTION",
                f"Task {task.task_id} has overlapping owned/shared scope.",
            )

    shared_edges: list[tuple[str, str, str, str, str]] = []
    ordered = sorted(tasks)
    for index, left_id in enumerate(ordered):
        for right_id in ordered[index + 1 :]:
            left = tasks[left_id]
            right = tasks[right_id]
            _validate_exclusive_pair(left, right)
            for left_path in left.shared_paths:
                for right_path in right.shared_paths:
                    if not _overlaps(_path_claim(left_path), _path_claim(right_path)):
                        continue
                    if left.integration_owner != right.integration_owner:
                        raise ReservationAdmissionError(
                            "PLANNER_INTEGRATION_OWNER_AMBIGUOUS",
                            f"Shared hotspot between {left_id} and {right_id} has multiple owners.",
                        )
                    shared_edges.append(
                        (left_id, right_id, left_path, right_path, str(left.integration_owner))
                    )
    return _hotspot_components(shared_edges)


def _validate_exclusive_pair(left: PlannerTask, right: PlannerTask) -> None:
    left_owned = [_path_claim(path) for path in left.owned_paths]
    left_shared = [_path_claim(path) for path in left.shared_paths]
    right_owned = [_path_claim(path) for path in right.owned_paths]
    right_shared = [_path_claim(path) for path in right.shared_paths]
    for owned in left_owned:
        if any(_overlaps(owned, other) for other in (*right_owned, *right_shared)):
            raise ReservationAdmissionError(
                "PLANNER_OWNERSHIP_UNRESOLVED",
                f"Exclusive scope for {left.task_id} overlaps {right.task_id}.",
            )
    for owned in right_owned:
        if any(_overlaps(owned, other) for other in left_shared):
            raise ReservationAdmissionError(
                "PLANNER_OWNERSHIP_UNRESOLVED",
                f"Exclusive scope for {right.task_id} overlaps {left.task_id}.",
            )


def _hotspot_components(
    edges: Sequence[tuple[str, str, str, str, str]],
) -> list[dict[str, Any]]:
    adjacency: dict[str, set[str]] = {}
    evidence: list[tuple[str, str, str, str, str]] = []
    for edge in edges:
        left, right, *_rest = edge
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)
        evidence.append(edge)
    hotspots: list[dict[str, Any]] = []
    visited: set[str] = set()
    for start in sorted(adjacency):
        if start in visited:
            continue
        pending = [start]
        members: set[str] = set()
        while pending:
            current = pending.pop()
            if current in members:
                continue
            members.add(current)
            pending.extend(sorted(adjacency.get(current, ()), reverse=True))
        visited.update(members)
        component_edges = [
            edge for edge in evidence if edge[0] in members and edge[1] in members
        ]
        owners = {edge[4] for edge in component_edges}
        if len(owners) != 1:
            raise ReservationAdmissionError(
                "PLANNER_INTEGRATION_OWNER_AMBIGUOUS",
                "Shared hotspot component has multiple integration owners.",
            )
        paths = sorted({path for edge in component_edges for path in edge[2:4]})
        hotspots.append(
            {
                "paths": paths,
                "integration_owner": next(iter(owners)),
                "task_ids": sorted(members),
            }
        )
    return sorted(hotspots, key=_canonical)


def _node(task: PlannerTask) -> dict[str, Any]:
    return {
        "kind": task.kind,
        "outcome": task.outcome,
        "owned_paths": sorted(task.owned_paths),
        "shared_paths": sorted(task.shared_paths),
        "integration_owner": task.integration_owner,
        "acceptance_checks": sorted(task.acceptance_checks),
        "required_capabilities": sorted(task.required_capabilities),
    }


def _edges(
    tasks: Mapping[str, PlannerTask], hotspots: Sequence[Mapping[str, Any]]
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for task_id in sorted(tasks):
        for dependency in sorted(tasks[task_id].dependencies):
            edges.append({"from": dependency, "to": task_id, "kind": "depends_on"})
    for hotspot in hotspots:
        owner = str(hotspot["integration_owner"])
        for task_id in hotspot["task_ids"]:
            if task_id == owner:
                continue
            edges.append(
                {"from": str(task_id), "to": owner, "kind": "integrates_with"}
            )
    unique = {_canonical(edge): edge for edge in edges}
    return [unique[key] for key in sorted(unique)]


def _validate_execution_edges(
    tasks: Mapping[str, PlannerTask], edges: Sequence[Mapping[str, str]]
) -> None:
    adjacency: dict[str, set[str]] = {task_id: set() for task_id in tasks}
    indegree = {task_id: 0 for task_id in tasks}
    for edge in edges:
        source = str(edge["from"])
        target = str(edge["to"])
        if target not in adjacency[source]:
            adjacency[source].add(target)
            indegree[target] += 1
    ready = sorted(task_id for task_id, count in indegree.items() if count == 0)
    visited = 0
    while ready:
        current = ready.pop(0)
        visited += 1
        for target in sorted(adjacency[current]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    if visited != len(tasks):
        raise ReservationAdmissionError(
            "PLANNER_EXECUTION_CYCLE",
            "Combined dependency and integration edges contain a cycle.",
        )


def _recommended_concurrency(
    ready_frontier: Sequence[str], tasks: Mapping[str, PlannerTask]
) -> int:
    selected: list[PlannerTask] = []
    for task_id in sorted(ready_frontier):
        candidate = tasks[task_id]
        if any(_shared_overlap(candidate, current) for current in selected):
            continue
        selected.append(candidate)
    return max(1, len(selected))


def _shared_overlap(left: PlannerTask, right: PlannerTask) -> bool:
    return any(
        _overlaps(_path_claim(left_path), _path_claim(right_path))
        for left_path in left.shared_paths
        for right_path in right.shared_paths
    )


def _git_identity(value: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in ("commit_sha", "tree_sha"):
        item = value.get(field)
        if not isinstance(item, str) or re.fullmatch(r"[0-9a-f]{40}", item) is None:
            raise ReservationAdmissionError(
                "PLANNER_BASE_INVALID", f"{field} must be an exact lowercase Git SHA."
            )
        result[field] = item
    return result


def _authority_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    reservation_id = value.get("reservation_id")
    lease_id = value.get("lease_id")
    if not isinstance(reservation_id, str) or not reservation_id.strip():
        raise ReservationAdmissionError(
            "PLANNER_AUTHORITY_INVALID", "reservation_id is required."
        )
    if not isinstance(lease_id, str) or not lease_id.strip():
        raise ReservationAdmissionError(
            "PLANNER_AUTHORITY_INVALID", "lease_id is required."
        )
    revision = _positive_int(value.get("authority_revision"), "authority_revision")
    fence = _positive_int(value.get("fence_token"), "fence_token")
    return {
        "reservation_id": reservation_id,
        "authority_revision": revision,
        "lease_id": lease_id,
        "fence_token": fence,
    }


def _normalize_runtime_candidate(
    candidate: Mapping[str, Any], capabilities: tuple[str, ...]
) -> dict[str, Any]:
    required_strings = (
        "binding_id",
        "worker_id",
        "worker_revision",
        "runtime_id",
        "tool_id",
        "tool_revision",
        "protocol",
        "interface",
        "endpoint",
        "binding",
        "transport",
        "observed_at",
    )
    normalized: dict[str, Any] = {
        "schema_version": 1,
        "contract": "coordinator-runtime-binding-v1",
    }
    for field in required_strings:
        value = candidate.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ReservationAdmissionError(
                "RUNTIME_BINDING_INVALID", f"Runtime candidate is missing {field}."
            )
        normalized[field] = value
    runtime_revision = candidate.get("runtime_revision")
    if not isinstance(runtime_revision, str) or re.fullmatch(
        r"[0-9a-f]{40}", runtime_revision
    ) is None:
        raise ReservationAdmissionError(
            "RUNTIME_BINDING_INVALID", "runtime_revision must be an exact Git SHA."
        )
    if normalized["transport"] not in {"mcp", "a2a", "local-process", "other"}:
        raise ReservationAdmissionError(
            "RUNTIME_BINDING_INVALID", "transport is not supported."
        )
    _parse_timestamp(normalized["observed_at"])
    normalized["runtime_revision"] = runtime_revision
    normalized["capabilities"] = list(capabilities)
    normalized["grants_mutation_authority"] = False
    return normalized


def _validate_plan_identity(
    request: PlannerRequest, plan: Mapping[str, Any]
) -> None:
    expected = {
        "contract": "coordinator-dependency-dag-v1",
        "project_id": request.project_id,
        "change_id": request.change_id,
        "revision": request.revision,
    }
    if any(plan.get(key) != value for key, value in expected.items()):
        raise ReservationAdmissionError(
            "WORK_PACKET_PLAN_MISMATCH",
            "Planner output does not match the requested work identity.",
        )
    validation = plan.get("validation")
    if not isinstance(validation, Mapping) or validation.get("status") != "validated":
        raise ReservationAdmissionError(
            "WORK_PACKET_PLAN_UNVALIDATED", "Work packet requires a validated plan."
        )


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ReservationAdmissionError(
            "PLANNER_AUTHORITY_INVALID", f"{label} must be a positive integer."
        )
    return value


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("coordinator clock must return an aware datetime")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReservationAdmissionError(
            "RUNTIME_BINDING_INVALID", "observed_at must be a valid date-time."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReservationAdmissionError(
            "RUNTIME_BINDING_INVALID", "observed_at must include a timezone."
        )
    return parsed.astimezone(UTC)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_id(prefix: str, value: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:24]}"


def _write_json_once(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(dict(payload), stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError as exc:
        raise ReservationAdmissionError(
            "COORDINATOR_EVIDENCE_COLLISION", f"Evidence already exists: {path}"
        ) from exc


__all__ = [
    "Clock",
    "PlannerService",
    "ResolveRuntime",
    "TokenFactory",
    "WorkPacketService",
]
