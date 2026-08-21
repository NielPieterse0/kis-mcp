from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from .models import (
    ChangeClassification,
    ClassificationState,
    CommissioningIntakeOutcome,
    LandedChangeEvidence,
)


class ProjectionInvoker(Protocol):
    async def read(self, operation: str, arguments: dict[str, Any]) -> Any: ...
    async def change(self, operation: str, arguments: dict[str, Any]) -> Any: ...


_LIVE_FIELDS = [
    "Live Verification",
    "Commissioning Key",
    "Live Verification Evidence",
]


def aggregate_commissioning_key(
    repository: str,
    merge_sha: str,
    keys: Sequence[str],
) -> str:
    ordered = tuple(sorted(set(keys)))
    if not ordered:
        raise ValueError("at least one commissioning key is required")
    if len(ordered) == 1:
        return ordered[0]
    digest = hashlib.sha256(("\n".join(ordered) + "\n").encode("utf-8")).hexdigest()[:24]
    return f"commission:{repository.casefold()}:{merge_sha.casefold()}:set-{digest}"


def aggregate_live_state(states: Sequence[str]) -> str:
    normalized = {str(value).casefold() for value in states}
    if "failed" in normalized:
        return "Failed"
    if "blocked" in normalized:
        return "Blocked"
    if "pending" in normalized or not normalized:
        return "Pending"
    return "Passed"


def _classification_projection(
    evidence: LandedChangeEvidence,
    classification: ChangeClassification,
    intake: Sequence[CommissioningIntakeOutcome],
) -> tuple[str, str | None, str]:
    if classification.state is ClassificationState.NOT_REQUIRED:
        if intake:
            raise ValueError("not-required classification cannot have commissioning intake")
        return (
            "Not Required",
            None,
            f"commissioning-classification:{evidence.merge_sha}:not_required",
        )
    if classification.state is ClassificationState.BLOCKED_AMBIGUOUS:
        if intake:
            raise ValueError("blocked classification cannot have commissioning intake")
        digest = hashlib.sha256(
            ("\n".join(classification.ambiguous_risk_triggers) + "\n").encode("utf-8")
        ).hexdigest()[:16]
        return (
            "Blocked",
            None,
            f"commissioning-classification:{evidence.merge_sha}:blocked_ambiguous:{digest}",
        )
    obligation_keys = tuple(item.commissioning_key for item in classification.obligations)
    intake_keys = tuple(item.commissioning_key for item in intake)
    if tuple(sorted(obligation_keys)) != tuple(sorted(intake_keys)):
        raise ValueError("commissioning intake does not match classified obligations")
    aggregate_key = aggregate_commissioning_key(
        evidence.repository, evidence.merge_sha, obligation_keys
    )
    issue_numbers = tuple(sorted(item.issue_number for item in intake))
    issue_linkage = ",".join(str(number) for number in issue_numbers)
    return "Pending", aggregate_key, f"commissioning-issues:{issue_linkage}"


def _source_card(value: Any, repository: str, source_issue: int) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("source board result is invalid")
    provenance = value.get("provenance")
    result = value.get("result")
    if (
        not isinstance(provenance, Mapping)
        or provenance.get("complete") is not True
        or not isinstance(result, Mapping)
        or result.get("complete") is not True
        or result.get("truncated") is not False
    ):
        raise RuntimeError("source board evidence is incomplete")
    cards = result.get("cards")
    if not isinstance(cards, list):
        raise TypeError("source board cards are invalid")
    matches = [
        card for card in cards
        if isinstance(card, Mapping)
        and card.get("number") == source_issue
        and str(card.get("repository", "")).casefold() == repository.casefold()
    ]
    if len(matches) != 1:
        raise RuntimeError("source Work card is not uniquely observable")
    card = matches[0]
    if not isinstance(card.get("item_id"), str) or not isinstance(card.get("authority_revision"), str):
        raise TypeError("source Work card lacks revision evidence")
    return card


async def project_source_live_state(
    invoker: ProjectionInvoker,
    *,
    project_id: str,
    repository: str,
    source_issue: int,
    live_state: str,
    commissioning_key: str | None,
    evidence_reference: str,
    idempotency_key: str,
) -> dict[str, Any]:
    board = await invoker.read(
        "project_management_board_data",
        {
            "project_id": project_id,
            "include_history": True,
            "query": str(source_issue),
            "group_by": "state",
            "item_limit": 1000,
        },
    )
    card = _source_card(board, repository, source_issue)
    fields: dict[str, Any] = {
        "Live Verification": live_state,
        "Commissioning Key": commissioning_key,
        "Live Verification Evidence": evidence_reference,
    }
    desired = [
        {
            "record_id": f"WORK-{source_issue}",
            "fields": fields,
            "expected_revision": card["authority_revision"],
            "source_repository": repository,
            "source_number": source_issue,
            "source_kind": "issue",
        }
    ]
    observed = [
        {
            "record_id": f"WORK-{source_issue}",
            "fields": {},
            "revision": card["authority_revision"],
            "accessible": True,
            "external_id": card["item_id"],
        }
    ]
    result = await invoker.change(
        "project_management_reconcile",
        {
            "project_id": project_id,
            "desired": desired,
            "observed": observed,
            "supported_fields": list(_LIVE_FIELDS),
            "apply": True,
            "idempotency_key": idempotency_key,
        },
    )
    outcomes = result.get("outcomes") if isinstance(result, Mapping) else None
    if not isinstance(outcomes, list) or not outcomes or not all(
        isinstance(item, Mapping) and item.get("success") is True for item in outcomes
    ):
        raise RuntimeError("source live-verification projection failed")
    return {"projected": True, "outcomes": outcomes}


async def project_classification_state(
    invoker: ProjectionInvoker,
    *,
    project_id: str,
    evidence: LandedChangeEvidence,
    classification: ChangeClassification,
    intake: Sequence[CommissioningIntakeOutcome],
) -> dict[str, Any]:
    live_state, commissioning_key, evidence_reference = _classification_projection(
        evidence, classification, intake
    )
    digest = hashlib.sha256(
        f"{evidence.merge_sha}\n{live_state}\n{commissioning_key}\n{evidence_reference}\n".encode()
    ).hexdigest()
    return await project_source_live_state(
        invoker,
        project_id=project_id,
        repository=evidence.repository,
        source_issue=evidence.source_issue,
        live_state=live_state,
        commissioning_key=commissioning_key,
        evidence_reference=evidence_reference,
        idempotency_key=f"commission-classification-{digest}",
    )


__all__ = [
    "aggregate_commissioning_key",
    "aggregate_live_state",
    "project_classification_state",
    "project_source_live_state",
]
