from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .contracts import EvidenceReference, EvidenceValidityClass

_MATERIAL = frozenset({"critical", "high", "medium"})


def _review_domain(review: Mapping[str, Any]) -> str:
    value = review.get("review_type") or review.get("step_id") or "review"
    return str(value).strip()


def _material_finding_ids(review: Mapping[str, Any]) -> tuple[str, ...]:
    payload = review.get("payload")
    if not isinstance(payload, Mapping):
        return ()
    result: list[str] = []
    for index, finding in enumerate(payload.get("findings", ())):
        if not isinstance(finding, Mapping):
            continue
        if str(finding.get("severity", "")).casefold() not in _MATERIAL:
            continue
        identity = finding.get("finding_id") or finding.get("id") or finding.get("title")
        result.append(str(identity or f"{_review_domain(review)}:{index}"))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class ReviewClosure:
    review_cycle_id: str
    subject: str
    reviewed_domains: tuple[str, ...]
    closed_findings: tuple[str, ...]
    open_material_findings: tuple[str, ...]
    correction_scope: tuple[str, ...]
    receipt_ref: str
    validity_inputs: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.open_material_findings:
            raise ValueError("REVIEW_NOT_CLOSED: material findings remain open")
        if not self.reviewed_domains:
            raise ValueError("review closure requires at least one reviewed domain")
        if len(set(self.reviewed_domains)) != len(self.reviewed_domains):
            raise ValueError("reviewed domains must be unique")

    def to_evidence(self) -> EvidenceReference:
        return EvidenceReference(
            evidence_id=f"review-closed:{self.review_cycle_id}", kind="review_closed",
            subject=self.subject, validity_class=EvidenceValidityClass.CONTENT_STABLE,
            validity_inputs=self.validity_inputs, receipt_ref=self.receipt_ref,
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "contract": "review-closure-v1", "status": "review_closed",
            "review_cycle_id": self.review_cycle_id, "subject": self.subject,
            "reviewed_domains": list(self.reviewed_domains),
            "closed_findings": list(self.closed_findings), "open_material_findings": [],
            "correction_scope": list(self.correction_scope), "receipt_ref": self.receipt_ref,
            "validity_inputs": dict(self.validity_inputs),
        }


def closure_from_execution(
    execution: Mapping[str, Any], *, subject: str, tree: str, receipt_ref: str,
    closed_findings: Sequence[str] = (), correction_scope: Sequence[str] = (),
) -> ReviewClosure:
    reviews = execution.get("reviews")
    if not isinstance(reviews, (list, tuple)) or not reviews:
        raise ValueError("REVIEW_NOT_CLOSED: substantive review evidence is missing")
    domains: list[str] = []
    open_findings: list[str] = []
    for review in reviews:
        if not isinstance(review, Mapping) or review.get("status") != "completed":
            raise ValueError("REVIEW_NOT_CLOSED: specialist review is incomplete")
        domain = _review_domain(review)
        if domain not in domains:
            domains.append(domain)
        open_findings.extend(_material_finding_ids(review))
    cycle = str(execution.get("source_fingerprint") or tree)[:24]
    return ReviewClosure(
        review_cycle_id=cycle,
        subject=subject,
        reviewed_domains=tuple(domains),
        closed_findings=tuple(dict.fromkeys(str(item) for item in closed_findings)),
        open_material_findings=tuple(open_findings),
        correction_scope=tuple(dict.fromkeys(str(item) for item in correction_scope)),
        receipt_ref=receipt_ref,
        validity_inputs={"tree": tree},
    )


def targeted_review_domains(
    previous_reviews: Sequence[Mapping[str, Any]],
    correction_delta: Sequence[str],
) -> tuple[str, ...]:
    """Return only review domains whose material findings intersect a correction delta."""
    changed = {str(item).replace("\\", "/").casefold() for item in correction_delta}
    selected: list[str] = []
    for review in previous_reviews:
        payload = review.get("payload")
        if not isinstance(payload, Mapping):
            continue
        affected = False
        for finding in payload.get("findings", ()):
            if not isinstance(finding, Mapping):
                continue
            if str(finding.get("severity", "")).casefold() not in _MATERIAL:
                continue
            surfaces = finding.get("affected_paths") or finding.get("paths") or ()
            normalized = {str(item).replace("\\", "/").casefold() for item in surfaces}
            if not changed or not normalized or changed & normalized:
                affected = True
                break
        domain = _review_domain(review)
        if affected and domain not in selected:
            selected.append(domain)
    return tuple(selected)


__all__ = ["ReviewClosure", "closure_from_execution", "targeted_review_domains"]
