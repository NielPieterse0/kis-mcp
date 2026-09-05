from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, Sequence

from .contracts import EvidenceReference


class EvidenceApplicability(StrEnum):
    CURRENT = "current"
    PENDING_REVALIDATION = "pending_revalidation"
    SUPERSEDED = "superseded"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class WorkflowCheckpoint:
    checkpoint_id: str
    phase: str
    ordinal: int
    irreversible: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceApplicabilityRecord:
    evidence_id: str
    status: EvidenceApplicability
    lineage_id: str
    superseded_by: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RecoveryState:
    lineage_id: str
    active_checkpoint: str
    checkpoints: tuple[WorkflowCheckpoint, ...]
    evidence: tuple[EvidenceApplicabilityRecord, ...]
    aborted: bool = False

    def checkpoint(self, checkpoint_id: str) -> WorkflowCheckpoint:
        for item in self.checkpoints:
            if item.checkpoint_id == checkpoint_id:
                return item
        raise ValueError(f"RECOVERY_CHECKPOINT_UNKNOWN: {checkpoint_id}")

    def available_rewinds(self) -> tuple[str, ...]:
        active = self.checkpoint(self.active_checkpoint)
        if active.irreversible:
            return ()
        return tuple(
            item.checkpoint_id
            for item in self.checkpoints
            if item.ordinal < active.ordinal and not item.irreversible
        )


def rewind_state(
    state: RecoveryState,
    target: str,
    *,
    next_lineage_id: str,
    references: Mapping[str, EvidenceReference],
) -> RecoveryState:
    active = state.checkpoint(state.active_checkpoint)
    selected = state.checkpoint(target)
    if selected.ordinal >= active.ordinal:
        raise ValueError("RECOVERY_REWIND_TARGET_NOT_PRIOR")
    crossed = [item for item in state.checkpoints if selected.ordinal < item.ordinal <= active.ordinal and item.irreversible]
    if crossed:
        raise ValueError(f"RECOVERY_IRREVERSIBLE_BOUNDARY: {crossed[0].checkpoint_id}")
    applicability = tuple(
        EvidenceApplicabilityRecord(
            evidence_id=item.evidence_id,
            status=(
                EvidenceApplicability.CURRENT
                if _reference_before_or_at(references[item.evidence_id], selected, state.checkpoints)
                else EvidenceApplicability.PENDING_REVALIDATION
            ),
            lineage_id=next_lineage_id,
            superseded_by=item.superseded_by,
            reason=item.reason,
        )
        for item in state.evidence
    )
    return RecoveryState(next_lineage_id, target, state.checkpoints, applicability, False)


def _reference_before_or_at(
    reference: EvidenceReference,
    selected: WorkflowCheckpoint,
    checkpoints: Sequence[WorkflowCheckpoint],
) -> bool:
    by_phase = {item.phase: item.ordinal for item in checkpoints}
    return by_phase.get(reference.applicable_phase, selected.ordinal + 1) <= selected.ordinal


def revalidate_retained_evidence(
    state: RecoveryState,
    *,
    references: Mapping[str, EvidenceReference],
    observed_inputs: Mapping[str, str],
    replacements: Mapping[str, str] | None = None,
) -> RecoveryState:
    replacements = replacements or {}
    records: list[EvidenceApplicabilityRecord] = []
    for item in state.evidence:
        reference = references[item.evidence_id]
        if item.status is not EvidenceApplicability.PENDING_REVALIDATION:
            records.append(item)
            continue
        changed = tuple(
            key for key, expected in reference.validity_inputs.items()
            if observed_inputs.get(key) != expected
        )
        replacement = replacements.get(item.evidence_id)
        if replacement is not None:
            records.append(EvidenceApplicabilityRecord(item.evidence_id, EvidenceApplicability.SUPERSEDED, state.lineage_id, replacement, "dependency changed; newer evidence supplied"))
        elif changed:
            records.append(EvidenceApplicabilityRecord(item.evidence_id, EvidenceApplicability.INVALID, state.lineage_id, None, "validity inputs changed: " + ", ".join(sorted(changed))))
        else:
            records.append(EvidenceApplicabilityRecord(item.evidence_id, EvidenceApplicability.CURRENT, state.lineage_id, None, "retained evidence revalidated without recomputation"))
    return RecoveryState(state.lineage_id, state.active_checkpoint, state.checkpoints, tuple(records), state.aborted)


def abort_state(state: RecoveryState) -> RecoveryState:
    if state.checkpoint(state.active_checkpoint).irreversible:
        raise ValueError("RECOVERY_ABORT_AFTER_IRREVERSIBLE_BOUNDARY")
    return RecoveryState(state.lineage_id, state.active_checkpoint, state.checkpoints, state.evidence, True)


def recovery_state_to_json(state: RecoveryState) -> dict[str, object]:
    return {
        "schema_version": 1,
        "lineage_id": state.lineage_id,
        "active_checkpoint": state.active_checkpoint,
        "aborted": state.aborted,
        "checkpoints": [
            {"checkpoint_id": item.checkpoint_id, "phase": item.phase, "ordinal": item.ordinal, "irreversible": item.irreversible}
            for item in state.checkpoints
        ],
        "evidence": [
            {"evidence_id": item.evidence_id, "status": item.status.value, "lineage_id": item.lineage_id,
             "superseded_by": item.superseded_by, "reason": item.reason}
            for item in state.evidence
        ],
    }


def recovery_state_from_json(value: Mapping[str, object]) -> RecoveryState:
    checkpoints = tuple(
        WorkflowCheckpoint(str(item["checkpoint_id"]), str(item["phase"]), int(item["ordinal"]), bool(item.get("irreversible", False)))
        for item in value.get("checkpoints", []) if isinstance(item, Mapping)
    )
    evidence = tuple(
        EvidenceApplicabilityRecord(str(item["evidence_id"]), EvidenceApplicability(str(item["status"])), str(item["lineage_id"]),
                                    str(item["superseded_by"]) if item.get("superseded_by") is not None else None,
                                    str(item["reason"]) if item.get("reason") is not None else None)
        for item in value.get("evidence", []) if isinstance(item, Mapping)
    )
    return RecoveryState(str(value["lineage_id"]), str(value["active_checkpoint"]), checkpoints, evidence, bool(value.get("aborted", False)))
