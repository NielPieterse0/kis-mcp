from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .models import ReservationAdmissionError

ResolveGitHubProvenance = Callable[[Mapping[str, Any]], Mapping[str, Any]]
_SHA = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = (
    "provider",
    "repository",
    "issue_number",
    "pull_number",
    "head_sha",
    "merge_sha",
)
_CORE_FIELDS = ("provider", "repository", "issue_number", "pull_number", "head_sha")


def normalize_github_provenance(
    value: Mapping[str, Any], label: str = "provenance"
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_INVALID", f"{label} must be an object"
        )
    unknown_keys = set(value) - set(_FIELDS)
    if unknown_keys:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_INVALID",
            f"{label} contains unknown keys: {', '.join(sorted(str(key) for key in unknown_keys))}",
        )
    provider = value.get("provider")
    if provider != "github":
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_INVALID", f"{label}.provider must be github"
        )
    repository = value.get("repository")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_INVALID", f"{label}.repository must be owner/repo"
        )
    owner, repo = (part.strip().casefold() for part in repository.split("/", 1))
    if not owner or not repo:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_INVALID", f"{label}.repository must be owner/repo"
        )
    normalized: dict[str, Any] = {
        "provider": "github",
        "repository": f"{owner}/{repo}",
    }
    for field in ("issue_number", "pull_number"):
        item = value.get(field)
        if isinstance(item, bool) or not isinstance(item, int) or item < 1:
            raise ReservationAdmissionError(
                "GITHUB_PROVENANCE_INVALID",
                f"{label}.{field} must be a positive integer",
            )
        normalized[field] = item
    head = value.get("head_sha")
    if not isinstance(head, str) or _SHA.fullmatch(head.casefold()) is None:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_INVALID", f"{label}.head_sha must be an exact Git SHA"
        )
    normalized["head_sha"] = head.casefold()
    merge = value.get("merge_sha")
    if merge is not None and (
        not isinstance(merge, str) or _SHA.fullmatch(merge.casefold()) is None
    ):
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_INVALID",
            f"{label}.merge_sha must be null or an exact Git SHA",
        )
    normalized["merge_sha"] = None if merge is None else merge.casefold()
    return normalized


def validate_provenance_evidence(
    value: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_EVIDENCE_INVALID",
            "verified provenance must be an object or null",
        )
    allowed_keys = {"schema_version", "contract", "status", "tuple", "claim_sha256"}
    unknown_keys = set(value) - allowed_keys
    if unknown_keys:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_EVIDENCE_INVALID",
            "verified provenance contains unknown keys: "
            + ", ".join(sorted(str(key) for key in unknown_keys)),
        )
    if (
        value.get("schema_version") != 1
        or value.get("contract") != "github-provenance-evidence-v1"
        or value.get("status") != "verified"
    ):
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_EVIDENCE_INVALID",
            "verified provenance contract identity is invalid",
        )
    claim_sha256 = value.get("claim_sha256")
    if not isinstance(claim_sha256, str) or _DIGEST.fullmatch(claim_sha256) is None:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_EVIDENCE_INVALID",
            "verified provenance claim digest is invalid",
        )
    tuple_value = value.get("tuple")
    if not isinstance(tuple_value, Mapping):
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_EVIDENCE_INVALID", "verified provenance tuple is missing"
        )
    normalized = normalize_github_provenance(tuple_value, "verified provenance tuple")
    expected_digest = hashlib.sha256(_canonical(normalized).encode("utf-8")).hexdigest()
    if claim_sha256 != expected_digest:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_EVIDENCE_INVALID",
            "verified provenance claim digest does not match its immutable tuple",
        )
    return {
        "schema_version": 1,
        "contract": "github-provenance-evidence-v1",
        "status": "verified",
        "tuple": normalized,
        "claim_sha256": claim_sha256,
    }


def validate_external_provenance(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ReservationAdmissionError(
            "EXTERNAL_PROVENANCE_INVALID", "external provenance must be an object or null"
        )
    if value.get("contract") == "github-provenance-evidence-v1":
        return validate_provenance_evidence(value)
    if value.get("provider") == "github":
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_EVIDENCE_INVALID",
            "raw GitHub claims are not trusted lifecycle evidence",
        )
    return {str(key): item for key, item in value.items() if isinstance(key, str)}


def github_provenance_evidence(value: Any) -> dict[str, Any] | None:
    normalized = validate_external_provenance(value)
    if normalized is None or normalized.get("contract") != "github-provenance-evidence-v1":
        return None
    return validate_provenance_evidence(normalized)


def validate_delivery_provenance(
    frozen: Mapping[str, Any], observed: Mapping[str, Any]
) -> dict[str, Any]:
    evidence = validate_provenance_evidence(frozen)
    if evidence is None:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_EVIDENCE_INVALID",
            "delivery provenance requires frozen verified evidence",
        )
    observed_tuple = normalize_github_provenance(
        observed, "delivery provider provenance"
    )
    frozen_tuple = evidence["tuple"]
    mismatches = [
        field for field in _CORE_FIELDS if frozen_tuple[field] != observed_tuple[field]
    ]
    if mismatches:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_DELIVERY_MISMATCH",
            "delivery provider identity differs from frozen provenance: "
            + ", ".join(mismatches),
        )
    merge_sha = observed_tuple["merge_sha"]
    if merge_sha is None:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_MERGE_SHA_REQUIRED",
            "delivery provider provenance must include the observed merge SHA",
        )
    frozen_merge = frozen_tuple["merge_sha"]
    if frozen_merge is not None and frozen_merge != merge_sha:
        raise ReservationAdmissionError(
            "GITHUB_PROVENANCE_DELIVERY_MISMATCH",
            "delivery merge SHA differs from frozen provenance",
        )
    return {
        "schema_version": 1,
        "contract": "github-provenance-delivery-v1",
        "status": "verified",
        "frozen_claim_sha256": evidence["claim_sha256"],
        "tuple": observed_tuple,
    }


class GitHubProvenanceService:
    def __init__(self, *, resolve_provider: ResolveGitHubProvenance) -> None:
        self._resolve_provider = resolve_provider

    def verify(self, claim: Mapping[str, Any]) -> dict[str, Any]:
        normalized_claim = normalize_github_provenance(claim, "claimed provenance")
        observed_value = self._resolve_provider(dict(normalized_claim))
        if not isinstance(observed_value, Mapping):
            raise ReservationAdmissionError(
                "GITHUB_PROVENANCE_PROVIDER_INVALID",
                "GitHub provenance resolver did not return an object",
            )
        observed = normalize_github_provenance(observed_value, "provider provenance")
        mismatches = [
            field for field in _FIELDS if normalized_claim[field] != observed[field]
        ]
        if mismatches:
            raise ReservationAdmissionError(
                "GITHUB_PROVENANCE_MISMATCH",
                "claimed GitHub provenance differs from provider identity: "
                + ", ".join(mismatches),
            )
        digest = hashlib.sha256(
            _canonical(normalized_claim).encode("utf-8")
        ).hexdigest()
        return {
            "schema_version": 1,
            "contract": "github-provenance-evidence-v1",
            "status": "verified",
            "tuple": observed,
            "claim_sha256": digest,
        }

    def aggregate(
        self, claims: Sequence[Mapping[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        accepted_by_identity: dict[str, dict[str, Any]] = {}
        conflicted_identities: set[str] = set()
        quarantined: list[dict[str, Any]] = []
        ordered = sorted((dict(item) for item in claims), key=_canonical)
        for claim in ordered:
            try:
                evidence = self.verify(claim)
            except ReservationAdmissionError as exc:
                quarantined.append(
                    {
                        "status": "quarantined",
                        "code": exc.code,
                        "reason": exc.reason,
                        "claim": _best_effort_claim(claim),
                    }
                )
                continue
            tuple_value = evidence["tuple"]
            key = _canonical(
                {
                    "repository": tuple_value["repository"],
                    "pull_number": tuple_value["pull_number"],
                }
            )
            if key in conflicted_identities:
                quarantined.append(_conflict_record(evidence["tuple"]))
                continue
            previous = accepted_by_identity.get(key)
            if previous is None:
                accepted_by_identity[key] = evidence
                continue
            if previous["tuple"] == evidence["tuple"]:
                continue
            accepted_by_identity.pop(key)
            conflicted_identities.add(key)
            quarantined.extend(
                (
                    _conflict_record(previous["tuple"]),
                    _conflict_record(evidence["tuple"]),
                )
            )
        return {
            "accepted": sorted(accepted_by_identity.values(), key=_canonical),
            "quarantined": sorted(quarantined, key=_canonical),
        }


def _conflict_record(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "quarantined",
        "code": "GITHUB_PROVENANCE_CONFLICT",
        "reason": "concurrent claims resolved to conflicting provider identities for one pull request",
        "claim": dict(value),
    }


def _best_effort_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return normalize_github_provenance(value, "claimed provenance")
    except ReservationAdmissionError:
        return {str(key): item for key, item in value.items() if isinstance(key, str)}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


__all__ = [
    "GitHubProvenanceService",
    "ResolveGitHubProvenance",
    "github_provenance_evidence",
    "normalize_github_provenance",
    "validate_delivery_provenance",
    "validate_external_provenance",
    "validate_provenance_evidence",
]
