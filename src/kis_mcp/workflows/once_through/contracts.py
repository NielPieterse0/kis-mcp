from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = frozenset({LEGACY_SCHEMA_VERSION, SCHEMA_VERSION})


class ObligationPhase(StrEnum):
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    CANDIDATE = "candidate"
    PULL_REQUEST = "pull_request"
    DOCUMENTATION = "documentation"
    COMMISSIONING = "commissioning"
    COMPLETION = "completion"


class TaskObligation(StrEnum):
    VERIFICATION = "verification"
    REVIEW_CLOSED = "review_closed"
    LIVE_CANDIDATE_VERIFICATION = "live_candidate_verification"
    PROVIDER_PROOF = "provider_proof"
    DOCUMENTATION = "documentation"
    COMMISSIONING = "commissioning"
    COMPLETION = "completion"

    @property
    def phase(self) -> ObligationPhase:
        return {
            TaskObligation.VERIFICATION: ObligationPhase.IMPLEMENTATION,
            TaskObligation.REVIEW_CLOSED: ObligationPhase.REVIEW,
            TaskObligation.LIVE_CANDIDATE_VERIFICATION: ObligationPhase.CANDIDATE,
            TaskObligation.PROVIDER_PROOF: ObligationPhase.PULL_REQUEST,
            TaskObligation.DOCUMENTATION: ObligationPhase.DOCUMENTATION,
            TaskObligation.COMMISSIONING: ObligationPhase.COMMISSIONING,
            TaskObligation.COMPLETION: ObligationPhase.COMPLETION,
        }[self]


class EvidenceValidityClass(StrEnum):
    CONTENT_STABLE = "content_tree_stable"
    BASE_SENSITIVE = "base_sensitive"
    RUNTIME_SENSITIVE = "dependency_config_runtime_sensitive"
    PROVIDER_EXACT_HEAD = "provider_exact_head_specific"
    POST_MERGE = "post_merge"


class EvidenceState(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"
    NOT_YET_APPLICABLE = "not_yet_applicable"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    evidence_id: str
    kind: str
    subject: str
    validity_class: EvidenceValidityClass
    validity_inputs: Mapping[str, str]
    receipt_ref: str
    applicable_phase: str = "implementation"

    def __post_init__(self) -> None:
        for label, value in (
            ("evidence_id", self.evidence_id), ("kind", self.kind),
            ("subject", self.subject), ("receipt_ref", self.receipt_ref),
            ("applicable_phase", self.applicable_phase),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be non-empty")
        if not isinstance(self.validity_class, EvidenceValidityClass):
            raise ValueError("validity_class is unsupported")
        for key, value in self.validity_inputs.items():
            if not isinstance(key, str) or not key or not isinstance(value, str) or not value:
                raise ValueError("validity_inputs require non-empty string keys and values")
        required_inputs = {
            EvidenceValidityClass.CONTENT_STABLE: {"tree"},
            EvidenceValidityClass.BASE_SENSITIVE: {"tree", "base"},
            EvidenceValidityClass.RUNTIME_SENSITIVE: {"tree", "runtime"},
            EvidenceValidityClass.PROVIDER_EXACT_HEAD: {"head", "provider"},
            EvidenceValidityClass.POST_MERGE: {"landed"},
        }[self.validity_class]
        missing = required_inputs - set(self.validity_inputs)
        if missing:
            raise ValueError(
                "validity_inputs missing required class inputs: " + ", ".join(sorted(missing))
            )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id, "kind": self.kind,
            "subject": self.subject, "validity_class": self.validity_class.value,
            "validity_inputs": dict(self.validity_inputs), "receipt_ref": self.receipt_ref,
            "applicable_phase": self.applicable_phase,
        }


@dataclass(frozen=True, slots=True)
class EvidenceResolution:
    evidence_id: str
    kind: str
    state: EvidenceState
    reason: str
    receipt_ref: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id, "kind": self.kind,
            "state": self.state.value, "reason": self.reason,
            "receipt_ref": self.receipt_ref,
        }


@dataclass(frozen=True, slots=True)
class TaskHandoffContract:
    project_id: str
    work_id: str
    repository: str
    requirements: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    affected_surfaces: tuple[str, ...]
    obligations: tuple[TaskObligation | str, ...]
    candidate_port: int
    source_identity: str
    change_id: str | None = None
    schema_version: int = SCHEMA_VERSION
    contract_fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError("handoff schema version is unsupported")
        try:
            normalized_obligations = tuple(TaskObligation(item) for item in self.obligations)
        except (TypeError, ValueError) as exc:
            raise ValueError("obligations contain an unsupported obligation") from exc
        if len(set(normalized_obligations)) != len(normalized_obligations):
            raise ValueError("obligations must be unique")
        object.__setattr__(self, "obligations", normalized_obligations)
        for label, value in (
            ("project_id", self.project_id), ("work_id", self.work_id),
            ("repository", self.repository), ("source_identity", self.source_identity),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be non-empty")
        for label, values in (
            ("requirements", self.requirements),
            ("acceptance_criteria", self.acceptance_criteria),
            ("affected_surfaces", self.affected_surfaces),
            ("obligations", self.obligations),
        ):
            if not values or any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{label} must contain resolved values")
        if type(self.candidate_port) is not int or not 1024 <= self.candidate_port <= 65535:
            raise ValueError("candidate_port is invalid")
        if self.change_id is not None and not self.change_id.strip():
            raise ValueError("change_id must be non-empty when provided")
        object.__setattr__(self, "contract_fingerprint", fingerprint(self._identity_payload()))

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "project_id": self.project_id,
            "work_id": self.work_id, "repository": self.repository,
            "requirements": list(self.requirements),
            "acceptance_criteria": list(self.acceptance_criteria),
            "affected_surfaces": list(self.affected_surfaces),
            "obligations": [item.value for item in self.obligations],
            "candidate_port": self.candidate_port,
            "source_identity": self.source_identity, "change_id": self.change_id,
        }

    def to_json_dict(self) -> dict[str, Any]:
        payload = {**self._identity_payload(), "contract_fingerprint": self.contract_fingerprint}
        if self.schema_version >= 2:
            active = set(self.obligations)
            payload["typed_obligations"] = [
                {
                    "kind": item.value,
                    "phase": item.phase.value,
                    "declared": item in active,
                }
                for item in TaskObligation
            ]
        return payload

    def obligations_through(self, phase: ObligationPhase | str) -> tuple[TaskObligation, ...]:
        resolved = ObligationPhase(phase)
        order = tuple(ObligationPhase)
        limit = order.index(resolved)
        return tuple(item for item in self.obligations if order.index(item.phase) <= limit)


@dataclass(frozen=True, slots=True)
class PromotionReadyHandoff:
    work_id: str
    change_id: str
    contract_fingerprint: str
    source_commit_sha: str
    candidate_identity: Mapping[str, Any]
    execution: Mapping[str, Any]
    evidence: tuple[EvidenceReference, ...]
    satisfied_obligations: tuple[str, ...]
    pending_obligations: tuple[str, ...] = ()
    status: str = "promotion_ready"
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError("promotion schema version is unsupported")
        if self.status != "promotion_ready":
            raise ValueError("promotion handoff status is fixed")
        if len(self.source_commit_sha) != 40 or any(c not in "0123456789abcdef" for c in self.source_commit_sha):
            raise ValueError("source_commit_sha must be full lowercase SHA")
        if len(self.contract_fingerprint) != 64:
            raise ValueError("contract_fingerprint must be SHA-256")
        if self.pending_obligations:
            raise ValueError("promotion_ready cannot contain pending obligations")
        if self.candidate_identity.get("work_id") != self.work_id:
            raise ValueError("candidate identity work_id mismatch")
        if self.candidate_identity.get("contract_fingerprint") != self.contract_fingerprint:
            raise ValueError("candidate identity contract fingerprint mismatch")
        server_instance = self.candidate_identity.get("server_instance_id")
        if not isinstance(server_instance, str) or not server_instance:
            raise ValueError("candidate identity server_instance_id is required")
        if self.execution.get("contract") != "change-execution-result-v2" or self.execution.get("status") != "passed":
            raise ValueError("promotion_ready requires passed implementation execution")
        if not self.satisfied_obligations or len(set(self.satisfied_obligations)) != len(self.satisfied_obligations):
            raise ValueError("satisfied_obligations must be non-empty and unique")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "status": self.status,
            "work_id": self.work_id, "change_id": self.change_id,
            "contract_fingerprint": self.contract_fingerprint,
            "source_commit_sha": self.source_commit_sha,
            "candidate_identity": dict(self.candidate_identity),
            "execution": dict(self.execution),
            "evidence": [item.to_json_dict() for item in self.evidence],
            "satisfied_obligations": list(self.satisfied_obligations),
            "pending_obligations": list(self.pending_obligations),
        }
