from __future__ import annotations

import re
from fnmatch import fnmatchcase

from .models import (
    ChangeClassification,
    ClassificationState,
    CommissioningObligation,
    LandedChangeEvidence,
)
from .settings import PostMergeCommissioningSettings

_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_SURFACE_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


def commissioning_key(repository: str, merge_sha: str, surface_id: str) -> str:
    if not isinstance(repository, str) or _REPOSITORY.fullmatch(repository.strip()) is None:
        raise ValueError("repository must be owner/name")
    if not isinstance(merge_sha, str) or _SHA.fullmatch(merge_sha.strip()) is None:
        raise ValueError("merge_sha must be a 40-character hexadecimal SHA")
    if not isinstance(surface_id, str) or _SURFACE_ID.fullmatch(surface_id.strip()) is None:
        raise ValueError("surface_id must be lower-case kebab-case")
    return f"commission:{repository.strip().casefold()}:{merge_sha.strip().casefold()}:{surface_id.strip()}"


def _matches_path(path: str, pattern: str) -> bool:
    return fnmatchcase(path, pattern)


def classify_change(
    evidence: LandedChangeEvidence,
    settings: PostMergeCommissioningSettings,
) -> ChangeClassification:
    obligations: list[CommissioningObligation] = []
    changed_paths = tuple(sorted(set(evidence.changed_paths)))
    risk_triggers = tuple(sorted(set(evidence.risk_triggers)))

    for surface in settings.surfaces:
        matched_paths = tuple(
            path
            for path in changed_paths
            if any(_matches_path(path, pattern) for pattern in surface.path_patterns)
        )
        matched_risks = tuple(
            risk for risk in risk_triggers if risk in set(surface.risk_triggers)
        )
        if not matched_paths and not matched_risks:
            continue
        obligations.append(
            CommissioningObligation(
                surface_id=surface.id,
                commissioning_key=commissioning_key(
                    evidence.repository, evidence.merge_sha, surface.id
                ),
                runtime_instance=surface.runtime_instance,
                refresh_rule=surface.refresh_rule,
                probe_id=surface.probe_id,
                verification_procedure=surface.verification_procedure,
                expected_invariant=surface.expected_invariant,
                evidence_target=surface.evidence_target,
                terminal_success_criterion=surface.terminal_success_criterion,
                matched_paths=matched_paths,
                matched_risk_triggers=matched_risks,
            )
        )

    ordered = tuple(sorted(obligations, key=lambda item: item.surface_id))
    if ordered:
        return ChangeClassification(
            state=ClassificationState.REQUIRED,
            obligations=ordered,
        )

    ambiguous = tuple(
        risk
        for risk in risk_triggers
        if risk in set(settings.ambiguous_risk_triggers)
    )
    if ambiguous:
        return ChangeClassification(
            state=ClassificationState.BLOCKED_AMBIGUOUS,
            ambiguous_risk_triggers=ambiguous,
        )
    return ChangeClassification(state=ClassificationState.NOT_REQUIRED)


__all__ = ["classify_change", "commissioning_key"]
