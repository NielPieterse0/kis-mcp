import asyncio
from pathlib import Path

import pytest
from fastmcp import FastMCP

from kis_mcp.workflows.once_through.contracts import (
    EvidenceReference,
    EvidenceValidityClass,
)
from kis_mcp.workflows.once_through.controller import PromotionStateStore
from kis_mcp.workflows.once_through.lifecycle import LifecycleDecisionService
from kis_mcp.workflows.once_through.lifecycle_tools import register_lifecycle_decision_tool
from kis_mcp.workflows.once_through.state import TaskHandoffStore
from kis_mcp.workflows.once_through.recovery import (
    EvidenceApplicability,
    EvidenceApplicabilityRecord,
    RecoveryState,
    WorkflowCheckpoint,
    abort_state,
    recovery_state_from_json,
    recovery_state_to_json,
    revalidate_retained_evidence,
    rewind_state,
)


def _checkpoints() -> tuple[WorkflowCheckpoint, ...]:
    return (
        WorkflowCheckpoint("A", "implementation", 0),
        WorkflowCheckpoint("B", "review", 1),
        WorkflowCheckpoint("C", "candidate", 2),
        WorkflowCheckpoint("D", "pull_request", 3),
    )


def _reference(evidence_id: str, phase: str, fingerprint: str) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        kind=evidence_id,
        subject="change",
        validity_class=EvidenceValidityClass.CONTENT_STABLE,
        validity_inputs={"tree": fingerprint},
        receipt_ref=f"receipt:{evidence_id}",
        applicable_phase=phase,
    )


def test_rewind_retains_evidence_and_marks_downstream_pending() -> None:
    refs = {
        "a": _reference("a", "implementation", "one"),
        "b": _reference("b", "review", "one"),
        "d": _reference("d", "pull_request", "one"),
    }
    state = RecoveryState(
        "lineage-1",
        "D",
        _checkpoints(),
        tuple(
            EvidenceApplicabilityRecord(key, EvidenceApplicability.CURRENT, "lineage-1")
            for key in refs
        ),
    )

    rewound = rewind_state(state, "A", next_lineage_id="lineage-2", references=refs)

    assert rewound.active_checkpoint == "A"
    assert {item.evidence_id for item in rewound.evidence} == set(refs)
    assert {item.evidence_id: item.status for item in rewound.evidence} == {
        "a": EvidenceApplicability.CURRENT,
        "b": EvidenceApplicability.PENDING_REVALIDATION,
        "d": EvidenceApplicability.PENDING_REVALIDATION,
    }


def test_unchanged_evidence_revalidates_without_recomputation() -> None:
    ref = _reference("b", "review", "same")
    state = RecoveryState(
        "lineage-2",
        "A",
        _checkpoints(),
        (EvidenceApplicabilityRecord("b", EvidenceApplicability.PENDING_REVALIDATION, "lineage-2"),),
    )
    result = revalidate_retained_evidence(
        state, references={"b": ref}, observed_inputs={"tree": "same"}
    )
    assert result.evidence[0].status is EvidenceApplicability.CURRENT
    assert "without recomputation" in str(result.evidence[0].reason)


def test_changed_evidence_is_superseded_when_replacement_exists() -> None:
    ref = _reference("b", "review", "old")
    state = RecoveryState(
        "lineage-2", "A", _checkpoints(),
        (EvidenceApplicabilityRecord("b", EvidenceApplicability.PENDING_REVALIDATION, "lineage-2"),),
    )
    result = revalidate_retained_evidence(
        state,
        references={"b": ref},
        observed_inputs={"tree": "new"},
        replacements={"b": "b2"},
    )
    item = result.evidence[0]
    assert item.status is EvidenceApplicability.SUPERSEDED
    assert item.superseded_by == "b2"


def test_changed_evidence_without_replacement_remains_historical_but_invalid() -> None:
    ref = _reference("b", "review", "old")
    state = RecoveryState(
        "lineage-2", "A", _checkpoints(),
        (EvidenceApplicabilityRecord("b", EvidenceApplicability.PENDING_REVALIDATION, "lineage-2"),),
    )
    result = revalidate_retained_evidence(
        state, references={"b": ref}, observed_inputs={"tree": "new"}
    )
    assert result.evidence[0].status is EvidenceApplicability.INVALID
    assert result.evidence[0].evidence_id == "b"


def test_irreversible_boundary_refuses_false_rewind_and_abort() -> None:
    checkpoints = (*_checkpoints()[:3], WorkflowCheckpoint("D", "pull_request", 3, irreversible=True))
    state = RecoveryState("lineage-1", "D", checkpoints, ())
    with pytest.raises(ValueError, match="RECOVERY_IRREVERSIBLE_BOUNDARY"):
        rewind_state(state, "A", next_lineage_id="lineage-2", references={})
    with pytest.raises(ValueError, match="RECOVERY_ABORT_AFTER_IRREVERSIBLE_BOUNDARY"):
        abort_state(state)


def test_rewind_targets_and_abort_are_deterministic() -> None:
    state = RecoveryState("lineage-1", "C", _checkpoints(), ())
    assert state.available_rewinds() == ("A", "B")
    assert abort_state(state).aborted is True


def test_recovery_state_round_trip_supports_interrupted_resume() -> None:
    state = RecoveryState(
        "lineage-2",
        "B",
        _checkpoints(),
        (EvidenceApplicabilityRecord("a", EvidenceApplicability.CURRENT, "lineage-2"),),
        True,
    )
    restored = recovery_state_from_json(recovery_state_to_json(state))
    assert restored == state
    resumed = RecoveryState(restored.lineage_id, restored.active_checkpoint, restored.checkpoints, restored.evidence, False)
    assert resumed.aborted is False
    assert resumed.lineage_id == "lineage-2"


def test_rewind_creates_new_lineage_without_mutating_predecessor() -> None:
    ref = _reference("d", "pull_request", "tree-1")
    original = RecoveryState(
        "lineage-1",
        "D",
        _checkpoints(),
        (EvidenceApplicabilityRecord("d", EvidenceApplicability.CURRENT, "lineage-1"),),
    )
    rewound = rewind_state(original, "B", next_lineage_id="lineage-2", references={"d": ref})
    assert original.lineage_id == "lineage-1"
    assert original.active_checkpoint == "D"
    assert rewound.lineage_id == "lineage-2"
    assert rewound.evidence[0].status is EvidenceApplicability.PENDING_REVALIDATION


def test_recovery_tool_is_registered_on_existing_lifecycle_surface(tmp_path: Path) -> None:
    root = tmp_path / "once-through"
    service = LifecycleDecisionService(
        TaskHandoffStore(root),
        PromotionStateStore(root / "promotion-controller"),
    )
    server = FastMCP("recovery-test")
    register_lifecycle_decision_tool(server, service, project_boundary=str(tmp_path))
    tools = {item.name: item for item in asyncio.run(server.list_tools())}

    assert {"change_lifecycle_decision", "once_through_recovery"}.issubset(tools)
    assert tools["once_through_recovery"].annotations.read_only_hint is False
    assert tools["once_through_recovery"].annotations.destructive_hint is False
