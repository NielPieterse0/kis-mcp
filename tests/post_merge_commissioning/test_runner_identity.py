from __future__ import annotations

from dataclasses import replace

import pytest

from kis_mcp.commissioning.models import (
    ChangeClassification,
    ClassificationState,
    CommissioningObligation,
    LandedChangeEvidence,
)
from kis_mcp.commissioning.runner import (
    CommissioningIdentityError,
    freeze_commissioning_obligation,
    parse_generated_commissioning_issue,
)

MERGE_SHA = "a" * 40
KEY = f"commission:nielpieterse0/kis-mcp:{MERGE_SHA}:work-management"


def _obligation() -> CommissioningObligation:
    return CommissioningObligation(
        surface_id="work-management",
        commissioning_key=KEY,
        runtime_instance="kis-op",
        refresh_rule="restart",
        probe_id="work-management-contract",
        verification_procedure="Restart kis-op and exercise Work Management.",
        expected_invariant="Work Management uses the landed contract.",
        evidence_target="linked commissioning issue evidence",
        terminal_success_criterion="The exposed Work path passes.",
        matched_paths=("src/kis_mcp/work_management/service.py",),
        matched_risk_triggers=(),
    )

def _issue() -> dict[str, object]:
    return {
        "number": 460,
        "state": "open",
        "title": f"Commissioning: work-management for PR #456 @ {MERGE_SHA[:12]}",
        "body": "\n".join(
            (
                "## Deterministic commissioning obligation",
                "",
                "Source Issue: #454",
                "Source PR: #456",
                f"Merge SHA: `{MERGE_SHA}`",
                "Change: `229-commissioning-runner-evidence-lifecycle`",
                "Live Surface: `work-management`",
                f"Commissioning Key: `{KEY}`",
                "",
                "## Required live verification",
                "",
                "Runtime/Profile: `kis-op`",
                "Refresh Rule: `restart`",
                "Procedure: Restart kis-op and exercise Work Management.",
                "Expected Invariant: Work Management uses the landed contract.",
                "Evidence Target: linked commissioning issue evidence",
                "Terminal Success Criterion: The exposed Work path passes.",
                "",
                "This issue is generated deterministically from landed merge evidence. Source delivery remains complete independently of this commissioning work.",
            )
        ),
    }


def _evidence() -> LandedChangeEvidence:
    return LandedChangeEvidence(
        repository="NielPieterse0/kis-mcp",
        source_issue=454,
        source_pr=456,
        merge_sha=MERGE_SHA,
        change_id="229-commissioning-runner-evidence-lifecycle",
        changed_paths=("src/kis_mcp/work_management/service.py",),
        risk_triggers=("public_contract",),
    )

def test_generated_issue_parses_to_exact_identity() -> None:
    parsed = parse_generated_commissioning_issue(_issue())

    assert parsed.commissioning_issue == 460
    assert parsed.source_issue == 454
    assert parsed.source_pr == 456
    assert parsed.merge_sha == MERGE_SHA
    assert parsed.change_id == "229-commissioning-runner-evidence-lifecycle"
    assert parsed.surface_id == "work-management"
    assert parsed.commissioning_key == KEY
    assert parsed.runtime_instance == "kis-op"
    assert parsed.refresh_rule == "restart"


def test_generated_issue_rejects_duplicate_or_contradictory_markers() -> None:
    issue = _issue()
    issue["body"] = str(issue["body"]) + "\nSource PR: #999"
    with pytest.raises(CommissioningIdentityError, match="source_pr"):
        parse_generated_commissioning_issue(issue)

    issue = _issue()
    issue["title"] = "Commissioning: provider-runtime for PR #456 @ aaaaaaaaaaaa"
    with pytest.raises(CommissioningIdentityError, match="title"):
        parse_generated_commissioning_issue(issue)


def test_freeze_requires_exact_landed_identity_and_obligation_contract() -> None:
    parsed = parse_generated_commissioning_issue(_issue())
    frozen = freeze_commissioning_obligation(
        parsed,
        _evidence(),
        ChangeClassification(state=ClassificationState.REQUIRED, obligations=(_obligation(),)),
    )

    assert frozen.commissioning_key == KEY
    assert frozen.probe_id == "work-management-contract"
    assert frozen.merge_sha == MERGE_SHA

def test_freeze_rejects_stale_merge_and_issue_contract() -> None:
    parsed = parse_generated_commissioning_issue(_issue())
    stale = replace(_evidence(), merge_sha="b" * 40)
    with pytest.raises(CommissioningIdentityError, match="merge_sha"):
        freeze_commissioning_obligation(
            parsed,
            stale,
            ChangeClassification(state=ClassificationState.REQUIRED, obligations=(_obligation(),)),
        )

    changed = replace(_obligation(), expected_invariant="different")
    with pytest.raises(CommissioningIdentityError, match="obligation_contract"):
        freeze_commissioning_obligation(
            parsed,
            _evidence(),
            ChangeClassification(state=ClassificationState.REQUIRED, obligations=(changed,)),
        )


def test_closed_generated_issue_still_parses_for_terminal_replay() -> None:
    issue = _issue()
    issue["state"] = "closed"
    parsed = parse_generated_commissioning_issue(issue)
    assert parsed.commissioning_issue == 460
    assert parsed.commissioning_key == KEY
