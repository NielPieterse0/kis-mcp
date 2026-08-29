from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import EvidenceReference, EvidenceValidityClass


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

    def to_evidence(self) -> EvidenceReference:
        return EvidenceReference(
            evidence_id=f"review-closed:{self.review_cycle_id}",
            kind="review_closed", subject=self.subject,
            validity_class=EvidenceValidityClass.CONTENT_STABLE,
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


__all__ = ["ReviewClosure"]
