import hashlib
import json
import os
import re
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from kis_mcp.paths import is_within_windows_boundary
from kis_mcp.state import (
    StateNamespaceRequest,
    StateNamespaceResolver,
    StateOwnershipClass,
    derive_change_source_id,
)
from kis_mcp.workflows.change_controls import select_change_controls

from .models import ReservationAdmissionError
from .service import _overlaps, _path_claim, _validate_candidate


ListClaims = Callable[[], list[dict[str, Any]]]
LoadExecution = Callable[[str], object | None]
AuthorityPreflight = Callable[[], None]
Clock = Callable[[], datetime]
_SHA = re.compile(r"^[0-9a-f]{40}$")


class AuthorityPort(Protocol):
    def current_reservation(self, reservation_id: str) -> dict[str, Any]: ...


class VerificationRequirementService:
    def derive(
        self,
        *,
        project_id: str,
        change_id: str,
        authority_revision: int,
        changed_paths: Sequence[str],
        complexity: str,
        risk_triggers: Sequence[str] = (),
        verification_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        paths = _exact_paths(changed_paths, "changed_paths")
        if not paths:
            raise ReservationAdmissionError(
                "VERIFICATION_SCOPE_EMPTY", "Verification requirements need changed paths."
            )
        controls = select_change_controls(
            complexity=complexity,
            risk_triggers=tuple(risk_triggers),
        )
        checks: dict[str, dict[str, str]] = {}
        for verification_id in sorted(set(verification_ids)):
            _required_text(verification_id, "verification_id")
            checks[verification_id] = {
                "check_id": verification_id,
                "category": "repository",
                "reason": "authoritative repository verification requirement",
            }
        checks["change-governance"] = {
            "check_id": "change-governance",
            "category": "governance",
            "reason": "governed scope must remain valid before review and landing",
        }
        checks["integration-preflight"] = {
            "check_id": "integration-preflight",
            "category": "integration",
            "reason": "accepted handoff must remain eligible for serialized integration",
        }
        if any(path.endswith(".py") for path in paths):
            checks["python-affected"] = {
                "check_id": "python-affected",
                "category": "tests",
                "reason": "Python implementation or tests changed",
            }
        if any(path.startswith("contracts/") or path.endswith(".schema.json") for path in paths):
            checks["contract-validation"] = {
                "check_id": "contract-validation",
                "category": "contract",
                "reason": "machine-readable contract changed",
            }
        if any(path.endswith(".md") for path in paths):
            checks["documentation-validation"] = {
                "check_id": "documentation-validation",
                "category": "documentation",
                "reason": "governed documentation changed",
            }
        scope_fingerprint = _digest({"changed_paths": paths})
        identity = {
            "project_id": _required_text(project_id, "project_id"),
            "change_id": _required_text(change_id, "change_id"),
            "authority_revision": _positive_int(authority_revision, "authority_revision"),
            "source_scope_fingerprint": scope_fingerprint,
            "risk_triggers": tuple(sorted(controls.risk_triggers)),
            "checks": tuple(checks[key] for key in sorted(checks)),
            "review_types": controls.review_types,
            "verification_authority": "github_actions_exact_head",
        }
        return {
            "schema_version": 3,
            "contract": "coordinator-verification-requirements-v3",
            "requirement_id": f"verification-{_digest(identity)[:24]}",
            "project_id": identity["project_id"],
            "change_id": identity["change_id"],
            "authority_revision": identity["authority_revision"],
            "source_scope_fingerprint": scope_fingerprint,
            "risk_triggers": list(identity["risk_triggers"]),
            "checks": [checks[key] for key in sorted(checks)],
            "review_types": list(controls.review_types),
            "exact_head_required": True,
            "verification_authority": "github_actions_exact_head",
        }


class ReconciliationService:
    def __init__(
        self,
        *,
        state_root: Path,
        project_boundary: Path,
        authority: AuthorityPort,
        list_claims: ListClaims,
        load_execution: LoadExecution,
        clock: Clock | None = None,
        namespace_resolver: StateNamespaceResolver | None = None,
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
        self._authority = authority
        self._list_claims = list_claims
        self._load_execution = load_execution
        self._clock = clock or (lambda: datetime.now(UTC))
        self._requirements = VerificationRequirementService()
        self._namespace_resolver = namespace_resolver or StateNamespaceResolver()

    def reconcile(
        self,
        *,
        packet: Mapping[str, Any],
        handoff: Mapping[str, Any],
        assignment_key: str,
        observed_change: Mapping[str, Any],
        completed_dependency_ids: Sequence[str] = (),
        complexity: str = "medium",
        risk_triggers: Sequence[str] = (),
        verification_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        packet_id = _required_text(packet.get("packet_id"), "packet.packet_id")
        project_id = _required_text(packet.get("project_id"), "packet.project_id")
        change_id = _required_text(packet.get("change_id"), "packet.change_id")
        handoff_id = _required_text(handoff.get("handoff_id"), "handoff.handoff_id")
        evidence_root = _evidence_root(
            self._namespace_resolver,
            project_id=project_id,
            change_id=change_id,
            state_key="coordinator-reconciliation",
        )
        integration = IntegrationQueueService(
            project_id=project_id,
            change_id=change_id,
            authority_preflight=lambda: self._assert_integration_authority(packet),
            namespace_resolver=self._namespace_resolver,
            clock=self._clock,
        )
        reconciliation_identity = {
            "packet_id": packet_id,
            "handoff": dict(handoff),
            "observed_change": dict(observed_change),
            "completed_dependencies": sorted(set(completed_dependency_ids)),
            "complexity": complexity,
            "risk_triggers": sorted(set(risk_triggers)),
            "verification_ids": sorted(set(verification_ids)),
            "assignment_key_sha256": hashlib.sha256(
                _required_text(assignment_key, "assignment_key").encode("utf-8")
            ).hexdigest(),
        }
        reconciliation_id = f"reconciliation-{_digest(reconciliation_identity)[:24]}"
        with _file_lock(evidence_root / "reconciliation.lock"):
            existing = self._read_reconciliation(reconciliation_id, evidence_root)
            if existing is not None:
                reconciliation = _mapping(
                    existing.get("reconciliation"), "existing.reconciliation"
                )
                if reconciliation.get("status") == "accepted":
                    self._assert_integration_authority(packet)
                return existing
            terminal = self._assignment_terminal(packet_id)
            if terminal is not None and terminal.get("state") == "revoked":
                raise ReservationAdmissionError(
                    "ASSIGNMENT_REVOKED",
                    "The work-packet assignment has been revoked.",
                )
            if terminal is not None and terminal.get("state") == "consumed":
                if terminal.get("handoff_id") != handoff_id:
                    raise ReservationAdmissionError(
                        "ASSIGNMENT_ALREADY_CONSUMED",
                        "The work-packet assignment was already consumed by another handoff.",
                    )
                prior_id = terminal.get("reconciliation_id")
                if isinstance(prior_id, str):
                    prior = self._read_reconciliation(prior_id, evidence_root)
                    if prior is not None:
                        return prior
            result = self._evaluate(
                reconciliation_id=reconciliation_id,
                packet=packet,
                handoff=handoff,
                assignment_key=assignment_key,
                observed_change=observed_change,
                completed_dependency_ids=completed_dependency_ids,
                complexity=complexity,
                risk_triggers=risk_triggers,
                verification_ids=verification_ids,
            )
            if result["reconciliation"]["status"] == "accepted":
                with _file_lock(self._state_root / "coordinator" / "assignment.lock"):
                    terminal = self._assignment_terminal(packet_id)
                    already_consumed = False
                    if terminal is not None:
                        if terminal.get("state") == "revoked":
                            raise ReservationAdmissionError(
                                "ASSIGNMENT_REVOKED",
                                "The assignment became revoked before reconciliation acceptance.",
                            )
                        if (
                            terminal.get("state") != "consumed"
                            or terminal.get("handoff_id") != handoff_id
                            or terminal.get("reconciliation_id") != reconciliation_id
                        ):
                            raise ReservationAdmissionError(
                                "ASSIGNMENT_ALREADY_CONSUMED",
                                "The assignment was consumed by different reconciliation evidence.",
                            )
                        already_consumed = True
                    queue_item = integration.enqueue(
                        reconciliation=result["reconciliation"],
                        candidate_head=str(handoff["exact_head"]["commit_sha"]),
                    )
                    if not already_consumed:
                        self._consume_assignment(
                            packet_id=packet_id,
                            handoff_id=handoff_id,
                            reconciliation_id=reconciliation_id,
                            assignment_key=assignment_key,
                            generation=_positive_int(
                                handoff.get("assignment_generation"),
                                "handoff.assignment_generation",
                            ),
                        )
                result["reconciliation"]["integration"]["queue_state"] = "queued"
                result["integration_queue_item"] = queue_item
            self._persist_reconciliation(reconciliation_id, result, evidence_root)
            return result

    def _evaluate(
        self,
        *,
        reconciliation_id: str,
        packet: Mapping[str, Any],
        handoff: Mapping[str, Any],
        assignment_key: str,
        observed_change: Mapping[str, Any],
        completed_dependency_ids: Sequence[str],
        complexity: str,
        risk_triggers: Sequence[str],
        verification_ids: Sequence[str],
    ) -> dict[str, Any]:
        violations: list[dict[str, str]] = []
        validations = {
            "reservation": "passed",
            "runtime_binding": "passed",
            "fence": "passed",
            "global_claims": "passed",
            "local_scope": "passed",
            "exact_head": "passed",
        }
        packet_id = _required_text(packet.get("packet_id"), "packet.packet_id")
        change_id = _required_text(packet.get("change_id"), "packet.change_id")
        authority = _mapping(packet.get("authority"), "packet.authority")
        packet_scope = _mapping(packet.get("scope"), "packet.scope")
        packet_runtime = _mapping(packet.get("runtime_binding"), "packet.runtime_binding")
        issued = self._issued_packet(packet_id)
        durable_packet = _mapping(issued.get("packet"), "issued.packet")
        supplied_packet = {key: value for key, value in packet.items() if key != "assignment"}
        if durable_packet != supplied_packet:
            violations.append(
                _violation(
                    "WORK_PACKET_EVIDENCE_MISMATCH",
                    "supplied work packet differs from durable issuance evidence",
                )
            )
            validations["reservation"] = "failed"
        expected_pairs = (
            ("packet_id", packet_id),
            ("task_id", _required_text(packet.get("task_id"), "packet.task_id")),
            ("reservation_id", _required_text(authority.get("reservation_id"), "authority.reservation_id")),
            ("authority_revision", _positive_int(authority.get("authority_revision"), "authority.authority_revision")),
            ("fence_token", _positive_int(authority.get("fence_token"), "authority.fence_token")),
        )
        for field, expected in expected_pairs:
            if handoff.get(field) != expected:
                code = "STALE_FENCE_TOKEN" if field == "fence_token" else "HANDOFF_IDENTITY_MISMATCH"
                violations.append(_violation(code, f"handoff {field} does not match the work packet"))
                if field in {"authority_revision", "reservation_id"}:
                    validations["reservation"] = "failed"
                if field == "fence_token":
                    validations["fence"] = "failed"
        generation = _positive_int(handoff.get("assignment_generation"), "handoff.assignment_generation")
        packet_assignment = _mapping(packet.get("assignment"), "packet.assignment")
        if generation != _positive_int(packet_assignment.get("generation"), "packet.assignment.generation"):
            violations.append(_violation("STALE_ASSIGNMENT_GENERATION", "assignment generation is stale"))
            validations["reservation"] = "failed"
        if _mapping(handoff.get("runtime_binding"), "handoff.runtime_binding") != packet_runtime:
            violations.append(_violation("RUNTIME_BINDING_MISMATCH", "runtime binding differs from the packet"))
            validations["runtime_binding"] = "failed"
        execution_id = _required_text(handoff.get("execution_id"), "handoff.execution_id")
        durable_execution = _execution_payload(self._load_execution(execution_id))
        if durable_execution is None:
            violations.append(
                _violation(
                    "WORKER_EXECUTION_NOT_OBSERVED",
                    "durable worker execution evidence is missing",
                )
            )
            validations["reservation"] = "failed"
        elif not _execution_matches_handoff(
            durable_execution,
            handoff=handoff,
            packet=packet,
        ):
            violations.append(
                _violation(
                    "WORKER_EXECUTION_MISMATCH",
                    "worker handoff differs from durable execution identity or terminal state",
                )
            )
            validations["reservation"] = "failed"
        current = self._authority.current_reservation(str(authority["reservation_id"]))
        for field in ("reservation_id", "authority_revision", "fence_token"):
            if current.get(field) != authority.get(field):
                code = "STALE_FENCE_TOKEN" if field == "fence_token" else "STALE_RESERVATION_AUTHORITY"
                violations.append(_violation(code, f"current reservation {field} no longer matches"))
                validations["reservation"] = "failed"
                if field == "fence_token":
                    validations["fence"] = "failed"
        if current.get("status") not in {"active", "reserved"}:
            violations.append(_violation("RESERVATION_NOT_ACTIVE", "current reservation is not active"))
            validations["reservation"] = "failed"

        packet_base = _git_identity(packet.get("exact_base"), "packet.exact_base")
        observed_base = _git_identity(observed_change.get("exact_base"), "observed_change.exact_base")
        observed_head = _git_identity(observed_change.get("exact_head"), "observed_change.exact_head")
        handoff_head = _git_identity(handoff.get("exact_head"), "handoff.exact_head")
        observed_paths = _exact_paths(
            observed_change.get("changed_paths"), "observed_change.changed_paths"
        )
        handoff_paths = _exact_paths(handoff.get("changed_paths"), "handoff.changed_paths")
        if packet_base != observed_base:
            violations.append(_violation("EXACT_BASE_MISMATCH", "observed base differs from packet base"))
            validations["exact_head"] = "failed"
        if observed_head != handoff_head or observed_paths != handoff_paths:
            violations.append(_violation("EXACT_HEAD_MISMATCH", "handoff does not match independently observed Git evidence"))
            validations["exact_head"] = "failed"
        allowed_claims = [
            _path_claim(path)
            for path in (
                *_paths(packet_scope.get("owned_paths", ()), "scope.owned_paths"),
                *_paths(packet_scope.get("shared_paths", ()), "scope.shared_paths"),
            )
        ]
        for changed_path in observed_paths:
            candidate = _path_claim(changed_path)
            if not any(_overlaps(candidate, allowed) for allowed in allowed_claims):
                violations.append(
                    _violation("HANDOFF_PATH_OUT_OF_SCOPE", f"changed path is outside packet scope: {changed_path}")
                )
                validations["local_scope"] = "failed"

        claims = [dict(item) for item in self._list_claims()]
        matches = [item for item in claims if item.get("change_id") == change_id]
        if len(matches) != 1:
            violations.append(_violation("GOVERNED_CHANGE_NOT_OBSERVED", "expected one current governed claim"))
            validations["global_claims"] = "failed"
        else:
            observed_claim = matches[0]
            if not _reservation_matches_claim(current, observed_claim):
                violations.append(
                    _violation(
                        "GOVERNED_SCOPE_DIVERGED",
                        "current reservation scope differs from the current governed claim",
                    )
                )
                validations["global_claims"] = "failed"
            candidate = _candidate_claim(observed_claim, current)
            others = [item for item in claims if item.get("change_id") != change_id]
            try:
                _validate_candidate(candidate, others)
            except ReservationAdmissionError as exc:
                violations.append(_violation(exc.code, exc.reason))
                validations["global_claims"] = "failed"
            if not _packet_scope_matches_claim(packet_scope, candidate):
                violations.append(_violation("GOVERNED_SCOPE_DIVERGED", "packet scope differs from current governed claim"))
                validations["global_claims"] = "failed"
        stored_assignment = _mapping(issued.get("assignment"), "issued.assignment")
        expected_digest = _required_text(stored_assignment.get("key_sha256"), "assignment.key_sha256")
        supplied_digest = hashlib.sha256(_required_text(assignment_key, "assignment_key").encode("utf-8")).hexdigest()
        if expected_digest != supplied_digest:
            violations.append(_violation("ASSIGNMENT_KEY_INVALID", "assignment key does not match durable issuance evidence"))
            validations["reservation"] = "failed"
        if stored_assignment.get("state") != "active":
            violations.append(_violation("ASSIGNMENT_NOT_ACTIVE", "durable assignment is not active"))
            validations["reservation"] = "failed"

        dependencies = set(_strings(packet.get("dependencies", ()), "packet.dependencies"))
        completed = set(_strings(completed_dependency_ids, "completed_dependency_ids"))
        missing_dependencies = sorted(dependencies - completed)
        residual_state = _strings(handoff.get("residual_state", ()), "handoff.residual_state")
        worker_done = handoff.get("status") == "worker_done"
        status = "accepted"
        if violations:
            status = "rejected"
        elif missing_dependencies or residual_state or not worker_done:
            status = "incomplete"
        requirement = None
        if status == "accepted":
            requirement = self._requirements.derive(
                project_id=str(packet["project_id"]),
                change_id=change_id,
                authority_revision=int(authority["authority_revision"]),
                changed_paths=observed_paths,
                complexity=complexity,
                risk_triggers=risk_triggers,
                verification_ids=verification_ids,
            )
        if missing_dependencies:
            violations.append(
                _violation(
                    "DEPENDENCIES_INCOMPLETE",
                    "required dependencies are not complete: " + ", ".join(missing_dependencies),
                )
            )
        if residual_state:
            violations.append(
                _violation(
                    "RESIDUAL_STATE_REQUIRES_RESOLUTION",
                    "worker residual state must be resolved before reviewability: "
                    + ", ".join(residual_state),
                )
            )
        if not worker_done and status == "incomplete":
            violations.append(
                _violation("WORKER_NOT_DONE", "worker handoff is not in worker_done state")
            )
        owner = packet_scope.get("integration_owner") or change_id
        reconciliation = {
            "schema_version": 1,
            "contract": "coordinator-reconciliation-result-v1",
            "reconciliation_id": reconciliation_id,
            "handoff_id": str(handoff["handoff_id"]),
            "reservation_id": str(authority["reservation_id"]),
            "authority_revision": int(authority["authority_revision"]),
            "fence_token": int(authority["fence_token"]),
            "runtime_binding": dict(packet_runtime),
            "validations": validations,
            "status": status,
            "violations": violations,
            "verification_requirement_ids": (
                [str(requirement["requirement_id"])] if requirement is not None else []
            ),
            "integration": {
                "owner_change_id": str(owner),
                "queue_state": "not_queued" if status != "rejected" else "blocked",
                "merge_authority_granted": False,
            },
        }
        return {
            "reconciliation": reconciliation,
            "verification_requirements": requirement,
        }

    def _assert_integration_authority(self, packet: Mapping[str, Any]) -> None:
        change_id = _required_text(packet.get("change_id"), "packet.change_id")
        authority = _mapping(packet.get("authority"), "packet.authority")
        packet_scope = _mapping(packet.get("scope"), "packet.scope")
        reservation_id = _required_text(
            authority.get("reservation_id"), "authority.reservation_id"
        )
        current = self._authority.current_reservation(reservation_id)
        for field in ("reservation_id", "authority_revision", "fence_token"):
            if current.get(field) != authority.get(field):
                raise ReservationAdmissionError(
                    "INTEGRATION_AUTHORITY_STALE",
                    f"current reservation {field} no longer matches the accepted handoff",
                )
        if current.get("status") not in {"active", "reserved"}:
            raise ReservationAdmissionError(
                "INTEGRATION_AUTHORITY_STALE",
                "current reservation is no longer active for integration",
            )
        claims = [dict(item) for item in self._list_claims()]
        matches = [item for item in claims if item.get("change_id") == change_id]
        if len(matches) != 1:
            raise ReservationAdmissionError(
                "INTEGRATION_CLAIM_GRAPH_INVALID",
                "integration preflight requires exactly one current governed claim",
            )
        observed_claim = matches[0]
        if not _reservation_matches_claim(current, observed_claim):
            raise ReservationAdmissionError(
                "INTEGRATION_CLAIM_GRAPH_INVALID",
                "current reservation scope differs from the current governed claim",
            )
        candidate = _candidate_claim(observed_claim, current)
        others = [item for item in claims if item.get("change_id") != change_id]
        try:
            _validate_candidate(candidate, others)
        except ReservationAdmissionError as exc:
            raise ReservationAdmissionError(
                "INTEGRATION_CLAIM_GRAPH_INVALID",
                f"current global claim graph is invalid: {exc.code}: {exc.reason}",
            ) from exc
        if not _packet_scope_matches_claim(packet_scope, candidate):
            raise ReservationAdmissionError(
                "INTEGRATION_CLAIM_GRAPH_INVALID",
                "accepted packet scope is no longer contained by current governance",
            )

    def _issued_packet(self, packet_id: str) -> dict[str, Any]:
        path = self._packet_root(packet_id) / "001-issued.json"
        if not path.is_file():
            raise ReservationAdmissionError(
                "WORK_PACKET_EVIDENCE_MISSING",
                f"Durable issuance evidence is missing for {packet_id}.",
            )
        return _read_json_object(path, "WORK_PACKET_EVIDENCE_INVALID")

    def _packet_root(self, packet_id: str) -> Path:
        _safe_id(packet_id, "packet_id")
        return self._state_root / "coordinator" / "packets" / packet_id

    def revoke_assignment(
        self,
        packet_id: str,
        *,
        generation: int,
        reason: str,
    ) -> dict[str, Any]:
        with _file_lock(self._state_root / "coordinator" / "assignment.lock"):
            terminal = self._assignment_terminal(packet_id)
            if terminal is not None:
                if terminal.get("state") == "revoked":
                    return terminal
                raise ReservationAdmissionError(
                    "ASSIGNMENT_ALREADY_CONSUMED",
                    "A consumed assignment cannot be revoked.",
                )
            issued = self._issued_packet(packet_id)
            assignment = _mapping(issued.get("assignment"), "issued.assignment")
            if generation != _positive_int(assignment.get("generation"), "assignment.generation"):
                raise ReservationAdmissionError(
                    "STALE_ASSIGNMENT_GENERATION", "Assignment generation is stale."
                )
            payload = {
                "schema_version": 1,
                "contract": "coordinator-assignment-revocation-v1",
                "packet_id": packet_id,
                "generation": generation,
                "key_sha256": assignment.get("key_sha256"),
                "state": "revoked",
                "reason": _required_text(reason, "reason"),
                "observed_at": _timestamp(self._clock()),
            }
            _write_json_once(
                self._packet_root(packet_id) / "002-assignment-revoked.json", payload
            )
            return payload

    def _assignment_terminal(self, packet_id: str) -> dict[str, Any] | None:
        root = self._packet_root(packet_id)
        paths = sorted(root.glob("002-assignment-*.json")) if root.is_dir() else []
        if not paths:
            return None
        if len(paths) != 1:
            raise ReservationAdmissionError(
                "ASSIGNMENT_EVIDENCE_CONFLICT",
                "Multiple terminal assignment records exist for one work packet.",
            )
        value = _read_json_object(paths[0], "ASSIGNMENT_EVIDENCE_INVALID")
        state = value.get("state")
        expected_contract = {
            "consumed": "coordinator-assignment-consumption-v1",
            "revoked": "coordinator-assignment-revocation-v1",
        }.get(state)
        if (
            value.get("schema_version") != 1
            or expected_contract is None
            or value.get("contract") != expected_contract
            or value.get("packet_id") != packet_id
            or not isinstance(value.get("generation"), int)
            or isinstance(value.get("generation"), bool)
            or int(value["generation"]) < 1
        ):
            raise ReservationAdmissionError(
                "ASSIGNMENT_EVIDENCE_INVALID",
                "Terminal assignment evidence does not match its versioned contract.",
            )
        return value

    def _consume_assignment(
        self,
        *,
        packet_id: str,
        handoff_id: str,
        reconciliation_id: str,
        assignment_key: str,
        generation: int,
    ) -> None:
        current = self._assignment_terminal(packet_id)
        if current is not None:
            if current.get("state") == "revoked":
                raise ReservationAdmissionError(
                    "ASSIGNMENT_REVOKED", "The assignment has been revoked."
                )
            if current.get("handoff_id") == handoff_id:
                return
            raise ReservationAdmissionError(
                "ASSIGNMENT_ALREADY_CONSUMED",
                "The assignment was already consumed by another handoff.",
            )
        issued = self._issued_packet(packet_id)
        assignment = _mapping(issued.get("assignment"), "issued.assignment")
        if generation != _positive_int(assignment.get("generation"), "assignment.generation"):
            raise ReservationAdmissionError(
                "STALE_ASSIGNMENT_GENERATION", "Assignment generation is stale."
            )
        digest = hashlib.sha256(assignment_key.encode("utf-8")).hexdigest()
        if digest != assignment.get("key_sha256"):
            raise ReservationAdmissionError(
                "ASSIGNMENT_KEY_INVALID", "Assignment key does not match issuance evidence."
            )
        _write_json_once(
            self._packet_root(packet_id) / "002-assignment-consumed.json",
            {
                "schema_version": 1,
                "contract": "coordinator-assignment-consumption-v1",
                "packet_id": packet_id,
                "generation": generation,
                "handoff_id": handoff_id,
                "reconciliation_id": reconciliation_id,
                "key_sha256": digest,
                "state": "consumed",
                "observed_at": _timestamp(self._clock()),
            },
        )

    def _reconciliation_path(
        self, reconciliation_id: str, evidence_root: Path
    ) -> Path:
        _safe_id(reconciliation_id, "reconciliation_id")
        return evidence_root / f"{reconciliation_id}.json"

    def _read_reconciliation(
        self, reconciliation_id: str, evidence_root: Path
    ) -> dict[str, Any] | None:
        path = self._reconciliation_path(reconciliation_id, evidence_root)
        if not path.is_file():
            return None
        return _read_json_object(path, "RECONCILIATION_EVIDENCE_INVALID")

    def _persist_reconciliation(
        self,
        reconciliation_id: str,
        result: Mapping[str, Any],
        evidence_root: Path,
    ) -> None:
        path = self._reconciliation_path(reconciliation_id, evidence_root)
        if path.is_file():
            existing = _read_json_object(path, "RECONCILIATION_EVIDENCE_INVALID")
            if existing != dict(result):
                raise ReservationAdmissionError(
                    "RECONCILIATION_EVIDENCE_CONFLICT",
                    "Existing reconciliation identity has different evidence.",
                )
            return
        _write_json_once(path, result)


class IntegrationQueueService:
    STATE_KEY = "coordinator-integration"

    def __init__(
        self,
        *,
        project_id: str,
        change_id: str,
        authority_preflight: AuthorityPreflight,
        namespace_resolver: StateNamespaceResolver | None = None,
        clock: Clock | None = None,
    ) -> None:
        resolver = namespace_resolver or StateNamespaceResolver()
        namespace = resolver.resolve(
            StateNamespaceRequest(
                ownership=StateOwnershipClass.DURABLE_EVIDENCE,
                state_key=self.STATE_KEY,
                identities={
                    "project_id": project_id,
                    "source_id": derive_change_source_id(change_id),
                },
            )
        )
        self.namespace = namespace
        self._state_root = Path(namespace.path)
        self._authority_preflight = authority_preflight
        self._clock = clock or (lambda: datetime.now(UTC))

    def enqueue(
        self,
        *,
        reconciliation: Mapping[str, Any],
        candidate_head: str,
    ) -> dict[str, Any]:
        if reconciliation.get("status") != "accepted":
            raise ReservationAdmissionError(
                "INTEGRATION_RECONCILIATION_NOT_ACCEPTED",
                "Only accepted reconciliation may enter the integration queue.",
            )
        candidate = _sha(candidate_head, "candidate_head")
        integration = _mapping(reconciliation.get("integration"), "reconciliation.integration")
        owner = _required_text(integration.get("owner_change_id"), "integration.owner_change_id")
        reconciliation_id = _required_text(
            reconciliation.get("reconciliation_id"), "reconciliation.reconciliation_id"
        )
        queue_item_id = f"integration-{_digest({'owner': owner, 'reconciliation_id': reconciliation_id, 'head': candidate})[:24]}"
        with _file_lock(self._state_root / "integration.lock"):
            existing = self._latest_queue_event(queue_item_id)
            if existing is not None:
                return existing
            self._authority_preflight()
            for item in self._active_queue_items():
                if item.get("owner_change_id") == owner:
                    raise ReservationAdmissionError(
                        "INTEGRATION_OWNER_BUSY",
                        f"Integration owner {owner} already has an active candidate.",
                    )
            payload = {
                "schema_version": 1,
                "contract": "coordinator-integration-queue-item-v1",
                "queue_item_id": queue_item_id,
                "reconciliation_id": reconciliation_id,
                "owner_change_id": owner,
                "candidate_head": candidate,
                "state": "queued",
                "verification": None,
                "merged_revision": None,
                "cleanup": None,
                "observed_at": _timestamp(self._clock()),
            }
            self._append_queue_event(queue_item_id, "queued", payload)
            return payload

    def authorize_delivery(
        self,
        queue_item_id: str,
        *,
        verification: Mapping[str, Any],
    ) -> dict[str, Any]:
        with _file_lock(self._state_root / "integration.lock"):
            current = self._require_queue_item(queue_item_id)
            if current.get("state") == "delivery_authorized":
                if dict(current.get("verification") or {}) == dict(verification):
                    return current
                raise ReservationAdmissionError(
                    "INTEGRATION_VERIFICATION_CONFLICT",
                    "Delivery was already authorized with different verification evidence.",
                )
            if current.get("state") != "queued":
                raise ReservationAdmissionError(
                    "INTEGRATION_ITEM_NOT_QUEUED",
                    "Delivery authorization requires a queued integration item.",
                )
            self._authority_preflight()
            if not _valid_github_actions_verification(
                verification, candidate_head=str(current["candidate_head"])
            ):
                raise ReservationAdmissionError(
                    "GITHUB_ACTIONS_EXACT_HEAD_VERIFICATION_REQUIRED",
                    "Referenced passing GitHub Actions verification must match the exact candidate head.",
                )
            payload = {
                **current,
                "state": "delivery_authorized",
                "verification": dict(verification),
                "observed_at": _timestamp(self._clock()),
            }
            self._append_queue_event(queue_item_id, "delivery-authorized", payload)
            return payload

    def mark_delivered(
        self,
        queue_item_id: str,
        *,
        merged_revision: str,
    ) -> dict[str, Any]:
        merged = _sha(merged_revision, "merged_revision")
        with _file_lock(self._state_root / "integration.lock"):
            current = self._require_queue_item(queue_item_id)
            if current.get("state") == "delivered":
                if current.get("merged_revision") == merged:
                    return current
                raise ReservationAdmissionError(
                    "INTEGRATION_DELIVERY_CONFLICT",
                    "Integration item was already delivered at another revision.",
                )
            if current.get("state") != "delivery_authorized":
                raise ReservationAdmissionError(
                    "INTEGRATION_DELIVERY_NOT_AUTHORIZED",
                    "Repository delivery requires exact-head GitHub Actions verification authorization.",
                )
            payload = {
                **current,
                "state": "delivered",
                "merged_revision": merged,
                "observed_at": _timestamp(self._clock()),
            }
            self._append_queue_event(queue_item_id, "delivered", payload)
            return payload

    def complete_cleanup(
        self,
        queue_item_id: str,
        *,
        cleanup: Mapping[str, Any],
    ) -> dict[str, Any]:
        with _file_lock(self._state_root / "integration.lock"):
            current = self._require_queue_item(queue_item_id)
            if current.get("state") == "cleanup_complete":
                if dict(current.get("cleanup") or {}) == dict(cleanup):
                    return current
                raise ReservationAdmissionError(
                    "INTEGRATION_CLEANUP_CONFLICT",
                    "Integration cleanup was already recorded with different evidence.",
                )
            if current.get("state") != "delivered":
                raise ReservationAdmissionError(
                    "INTEGRATION_CLEANUP_NOT_DELIVERED",
                    "Cleanup coordination begins only after repository delivery.",
                )
            if not _valid_cleanup_evidence(cleanup):
                raise ReservationAdmissionError(
                    "INTEGRATION_CLEANUP_NOT_READY",
                    "Cleanup requires referenced passing evidence that the worktree is clean, merged, and recoverable.",
                )
            payload = {
                **current,
                "state": "cleanup_complete",
                "cleanup": dict(cleanup),
                "observed_at": _timestamp(self._clock()),
            }
            self._append_queue_event(queue_item_id, "cleanup-complete", payload)
            return payload

    def _queue_root(self, queue_item_id: str) -> Path:
        _safe_id(queue_item_id, "queue_item_id")
        return self._state_root / queue_item_id

    def _require_queue_item(self, queue_item_id: str) -> dict[str, Any]:
        item = self._latest_queue_event(queue_item_id)
        if item is None:
            raise ReservationAdmissionError(
                "INTEGRATION_ITEM_NOT_FOUND", f"Unknown integration item {queue_item_id}."
            )
        return item

    def _active_queue_items(self) -> list[dict[str, Any]]:
        root = self._state_root
        if not root.is_dir():
            return []
        active: list[dict[str, Any]] = []
        for item_root in sorted(path for path in root.iterdir() if path.is_dir()):
            current = self._latest_queue_event(item_root.name)
            if current is not None and current.get("state") in {
                "queued",
                "delivery_authorized",
                "delivered",
            }:
                active.append(current)
        return active

    def _latest_queue_event(self, queue_item_id: str) -> dict[str, Any] | None:
        root = self._queue_root(queue_item_id)
        if not root.is_dir():
            return None
        paths = sorted(root.glob("*.json"), key=_journal_sort_key)
        if not paths:
            return None
        return _read_json_object(paths[-1], "INTEGRATION_EVIDENCE_INVALID")

    def _append_queue_event(
        self, queue_item_id: str, event_name: str, payload: Mapping[str, Any]
    ) -> None:
        root = self._queue_root(queue_item_id)
        root.mkdir(parents=True, exist_ok=True)
        paths = sorted(root.glob("*.json"), key=_journal_sort_key)
        ordinal = 1 if not paths else _journal_sort_key(paths[-1])[0] + 1
        path = root / f"{ordinal:03d}-{event_name}.json"
        _write_json_once(path, payload)


def _reservation_matches_claim(
    reservation: Mapping[str, Any], claim: Mapping[str, Any]
) -> bool:
    return (
        set(_paths(reservation.get("owned_paths", ()), "reservation.owned_paths"))
        == set(_paths(claim.get("owned_paths", ()), "claim.owned_paths"))
        and set(_paths(reservation.get("shared_paths", ()), "reservation.shared_paths"))
        == set(_paths(claim.get("shared_paths", ()), "claim.shared_paths"))
        and set(_strings(reservation.get("dependencies", ()), "reservation.dependencies"))
        == set(_strings(claim.get("dependencies", ()), "claim.dependencies"))
        and reservation.get("integration_owner") == claim.get("integration_owner")
    )


def _candidate_claim(
    observed: Mapping[str, Any], reservation: Mapping[str, Any]
) -> dict[str, Any]:
    change_id = _required_text(observed.get("change_id"), "claim.change_id")
    return {
        "change_id": change_id,
        "branch": observed.get("branch") or f"change/{change_id}",
        "worktree": observed.get("worktree") or f".work/worktrees/{change_id}",
        "outcome": observed.get("outcome") or change_id,
        "owned_paths": list(reservation.get("owned_paths", observed.get("owned_paths", ()))),
        "shared_paths": list(reservation.get("shared_paths", observed.get("shared_paths", ()))),
        "dependencies": list(reservation.get("dependencies", observed.get("dependencies", ()))),
        "integration_owner": reservation.get("integration_owner", observed.get("integration_owner")),
    }


def _packet_scope_matches_claim(
    packet_scope: Mapping[str, Any], claim: Mapping[str, Any]
) -> bool:
    governed = [
        _path_claim(path)
        for path in (
            *_paths(claim.get("owned_paths", ()), "claim.owned_paths"),
            *_paths(claim.get("shared_paths", ()), "claim.shared_paths"),
        )
    ]
    packet_paths = (
        *_paths(packet_scope.get("owned_paths", ()), "scope.owned_paths"),
        *_paths(packet_scope.get("shared_paths", ()), "scope.shared_paths"),
    )
    return all(
        any(_claim_within(_path_claim(path), allowed) for allowed in governed)
        for path in packet_paths
    )


def _evidence_root(
    resolver: StateNamespaceResolver,
    *,
    project_id: str,
    change_id: str,
    state_key: str,
) -> Path:
    namespace = resolver.resolve(
        StateNamespaceRequest(
            ownership=StateOwnershipClass.DURABLE_EVIDENCE,
            state_key=state_key,
            identities={
                "project_id": project_id,
                "source_id": derive_change_source_id(change_id),
            },
        )
    )
    return Path(namespace.path)


def _execution_payload(value: object | None) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        payload = dict(value)
    else:
        serializer = getattr(value, "to_json_dict", None)
        if not callable(serializer):
            raise ReservationAdmissionError(
                "WORKER_EXECUTION_EVIDENCE_INVALID",
                "worker execution evidence is not serializable",
            )
        payload = serializer()
        if not isinstance(payload, Mapping):
            raise ReservationAdmissionError(
                "WORKER_EXECUTION_EVIDENCE_INVALID",
                "worker execution serializer returned a non-object",
            )
        payload = dict(payload)
    if (
        payload.get("schema_version") != 2
        or payload.get("contract") != "coordinator-worker-execution-v2"
        or not isinstance(payload.get("identity"), Mapping)
    ):
        raise ReservationAdmissionError(
            "WORKER_EXECUTION_EVIDENCE_INVALID",
            "durable worker execution evidence has an invalid contract identity",
        )
    return payload


def _execution_matches_handoff(
    execution: Mapping[str, Any],
    *,
    handoff: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> bool:
    identity = _mapping(execution.get("identity"), "execution.identity")
    authority = _mapping(packet.get("authority"), "packet.authority")
    exact_identity = {
        "execution_id": handoff.get("execution_id"),
        "packet_id": handoff.get("packet_id"),
        "task_id": handoff.get("task_id"),
        "assignment_generation": handoff.get("assignment_generation"),
        "reservation_id": handoff.get("reservation_id"),
        "authority_revision": handoff.get("authority_revision"),
        "fence_token": handoff.get("fence_token"),
        "worker_id": handoff.get("worker_id"),
        "runtime_binding": handoff.get("runtime_binding"),
        "attempt_id": handoff.get("attempt_id"),
        "lease_id": authority.get("lease_id"),
    }
    if any(identity.get(field) != expected for field, expected in exact_identity.items()):
        return False
    expected_states = {
        "worker_done": {"completed"},
        "worker_failed": {"failed", "cancelled"},
        "worker_incomplete": {"pending", "running", "waiting_input", "recoverable"},
    }
    handoff_status = handoff.get("status")
    allowed_states = expected_states.get(handoff_status)
    if allowed_states is None or execution.get("state") not in allowed_states:
        return False
    if execution.get("result_id") != handoff.get("result_id"):
        return False
    return _strings(execution.get("residual_state", ()), "execution.residual_state") == _strings(
        handoff.get("residual_state", ()), "handoff.residual_state"
    )


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReservationAdmissionError("RECONCILIATION_INPUT_INVALID", f"{label} must be an object.")
    return dict(value)


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReservationAdmissionError("RECONCILIATION_INPUT_INVALID", f"{label} must be non-empty.")
    return value.strip()


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ReservationAdmissionError("RECONCILIATION_INPUT_INVALID", f"{label} must be positive.")
    return value


def _repo_path(value: object) -> str:
    text = _required_text(value, "repository path").replace("\\", "/")
    if text.startswith("/") or ":" in text or any(part == ".." for part in text.split("/")):
        raise ReservationAdmissionError("RECONCILIATION_PATH_INVALID", f"Unsafe repository path: {text}")
    return text.strip("/")


def _paths(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ReservationAdmissionError("RECONCILIATION_INPUT_INVALID", f"{label} must be an array.")
    result = tuple(sorted({_repo_path(item) for item in value}))
    return result


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ReservationAdmissionError("RECONCILIATION_INPUT_INVALID", f"{label} must be an array.")
    return tuple(sorted({_required_text(item, label) for item in value}))


def _exact_paths(value: object, label: str) -> tuple[str, ...]:
    paths = _paths(value, label)
    if any("*" in path for path in paths):
        raise ReservationAdmissionError(
            "RECONCILIATION_PATH_INVALID",
            f"{label} must contain exact changed paths, not patterns.",
        )
    return paths


def _claim_within(
    candidate: tuple[str, str, bool], allowed: tuple[str, str, bool]
) -> bool:
    _candidate_text, candidate_prefix, candidate_recursive = candidate
    _allowed_text, allowed_prefix, allowed_recursive = allowed
    if candidate_recursive:
        return allowed_recursive and (
            candidate_prefix == allowed_prefix
            or candidate_prefix.startswith(f"{allowed_prefix}/")
        )
    if allowed_recursive:
        return candidate_prefix == allowed_prefix or candidate_prefix.startswith(
            f"{allowed_prefix}/"
        )
    return candidate_prefix == allowed_prefix


def _git_identity(value: object, label: str) -> dict[str, str]:
    mapping = _mapping(value, label)
    return {
        "commit_sha": _sha(mapping.get("commit_sha"), f"{label}.commit_sha"),
        "tree_sha": _sha(mapping.get("tree_sha"), f"{label}.tree_sha"),
    }


def _sha(value: object, label: str) -> str:
    text = _required_text(value, label).lower()
    if _SHA.fullmatch(text) is None:
        raise ReservationAdmissionError("RECONCILIATION_INPUT_INVALID", f"{label} must be a 40-character Git SHA.")
    return text


def _safe_id(value: object, label: str) -> str:
    text = _required_text(value, label)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", text) is None:
        raise ReservationAdmissionError("RECONCILIATION_INPUT_INVALID", f"{label} is unsafe for durable storage.")
    return text


def _violation(code: str, reason: str) -> dict[str, str]:
    return {"code": code, "reason": reason[:1000]}


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_cleanup_evidence(cleanup: Mapping[str, Any]) -> bool:
    reference = cleanup.get("reference")
    return (
        cleanup.get("status") == "passed"
        and cleanup.get("worktree_clean") is True
        and cleanup.get("merged") is True
        and cleanup.get("recoverable") is True
        and isinstance(reference, str)
        and bool(reference.strip())
    )


def _valid_github_actions_verification(
    verification: Mapping[str, Any], *, candidate_head: str
) -> bool:
    revision = verification.get("revision")
    status = verification.get("status")
    source = verification.get("source")
    reference = verification.get("reference")
    return (
        isinstance(revision, str)
        and revision.lower() == candidate_head.lower()
        and status == "passed"
        and source == "github_actions"
        and isinstance(reference, str)
        and bool(reference.strip())
    )


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _journal_sort_key(path: Path) -> tuple[int, str]:
    prefix, separator, _rest = path.name.partition("-")
    if not separator:
        raise ReservationAdmissionError("INTEGRATION_EVIDENCE_INVALID", f"Invalid journal filename: {path.name}")
    try:
        ordinal = int(prefix)
    except ValueError as exc:
        raise ReservationAdmissionError("INTEGRATION_EVIDENCE_INVALID", f"Invalid journal ordinal: {path.name}") from exc
    return ordinal, path.name


@contextmanager
def _file_lock(path: Path) -> Iterable[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
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


def _read_json_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReservationAdmissionError(code, f"Cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReservationAdmissionError(code, f"Evidence at {path} is not an object.")
    return value


def _write_json_once(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(dict(payload), stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise ReservationAdmissionError("DURABLE_EVIDENCE_COLLISION", f"Evidence already exists: {path}") from exc


__all__ = [
    "IntegrationQueueService",
    "ReconciliationService",
    "VerificationRequirementService",
]
