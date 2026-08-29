from __future__ import annotations

from collections.abc import Mapping

from .contracts import EvidenceReference, EvidenceResolution, EvidenceState

_PHASE_ORDER = {
    "implementation": 0,
    "promotion": 1,
    "pull_request": 2,
    "post_merge": 3,
}


def resolve_evidence(
    references: tuple[EvidenceReference, ...],
    *,
    required_kinds: tuple[str, ...],
    observed_inputs: Mapping[str, str],
    phase: str = "promotion",
) -> tuple[EvidenceResolution, ...]:
    by_kind: dict[str, list[EvidenceReference]] = {}
    for item in references:
        by_kind.setdefault(item.kind, []).append(item)
    results: list[EvidenceResolution] = []
    current_phase = _PHASE_ORDER.get(phase, -1)
    for kind in required_kinds:
        candidates = by_kind.get(kind, [])
        if not candidates:
            results.append(EvidenceResolution(kind, kind, EvidenceState.MISSING, "required evidence is absent"))
            continue
        if len(candidates) != 1:
            results.append(EvidenceResolution(
                kind, kind, EvidenceState.INVALID,
                f"required evidence kind is ambiguous: {len(candidates)} receipts",
            ))
            continue
        item = candidates[0]
        applicable = _PHASE_ORDER.get(item.applicable_phase, 0)
        if current_phase < applicable:
            results.append(EvidenceResolution(item.evidence_id, kind, EvidenceState.NOT_YET_APPLICABLE, f"applies at {item.applicable_phase}", item.receipt_ref))
            continue
        changed = tuple(
            key for key, expected in item.validity_inputs.items()
            if observed_inputs.get(key) != expected
        )
        if changed:
            results.append(EvidenceResolution(
                item.evidence_id, kind, EvidenceState.INVALID,
                "validity inputs changed: " + ", ".join(sorted(changed)),
                item.receipt_ref,
            ))
            continue
        results.append(EvidenceResolution(
            item.evidence_id, kind, EvidenceState.VALID,
            "all declared validity inputs match", item.receipt_ref,
        ))
    return tuple(results)


def minimum_rerun(resolutions: tuple[EvidenceResolution, ...]) -> tuple[str, ...]:
    return tuple(
        item.kind for item in resolutions
        if item.state in {EvidenceState.INVALID, EvidenceState.MISSING}
    )


__all__ = ["minimum_rerun", "resolve_evidence"]
