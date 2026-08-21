from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .models import ChangeClassification, ClassificationState, LandedChangeEvidence

_SHA = re.compile(r"^[0-9a-f]{40}$")
_CHANGE = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
_SURFACE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class CommissioningIdentityError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class ParsedCommissioningIssue:
    commissioning_issue: int
    source_issue: int
    source_pr: int
    merge_sha: str
    change_id: str
    surface_id: str
    commissioning_key: str
    runtime_instance: str
    refresh_rule: str
    verification_procedure: str
    expected_invariant: str
    evidence_target: str
    terminal_success_criterion: str


@dataclass(frozen=True, slots=True)
class FrozenCommissioningExecution:
    repository: str
    commissioning_issue: int
    source_issue: int
    source_pr: int
    merge_sha: str
    change_id: str
    surface_id: str
    commissioning_key: str
    runtime_instance: str
    refresh_rule: str
    probe_id: str
    verification_procedure: str
    expected_invariant: str
    evidence_target: str
    terminal_success_criterion: str


def _single(body: str, pattern: str, label: str) -> str:
    matches = re.findall(pattern, body, flags=re.MULTILINE)
    if len(matches) != 1:
        raise CommissioningIdentityError(label, f"expected exactly one {label} marker")
    return str(matches[0]).strip()


def _positive_int(value: str, label: str) -> int:
    try:
        selected = int(value)
    except ValueError as exc:
        raise CommissioningIdentityError(label, f"{label} must be an integer") from exc
    if selected <= 0:
        raise CommissioningIdentityError(label, f"{label} must be positive")
    return selected

def parse_generated_commissioning_issue(issue: Mapping[str, Any]) -> ParsedCommissioningIssue:
    number = issue.get("number")
    if type(number) is not int or number <= 0:
        raise CommissioningIdentityError("commissioning_issue", "issue number is invalid")
    issue_state = str(issue.get("state", "")).casefold()
    if issue_state not in {"open", "closed"}:
        raise CommissioningIdentityError(
            "issue_state", "commissioning issue state must be open or closed"
        )
    body = issue.get("body")
    if not isinstance(body, str):
        raise CommissioningIdentityError("body", "commissioning issue body is missing")

    source_issue = _positive_int(_single(body, r"^Source Issue: #([1-9][0-9]*)\s*$", "source_issue"), "source_issue")
    source_pr = _positive_int(_single(body, r"^Source PR: #([1-9][0-9]*)\s*$", "source_pr"), "source_pr")
    merge_sha = _single(body, r"^Merge SHA: `([0-9a-fA-F]{40})`\s*$", "merge_sha").casefold()
    change_id = _single(body, r"^Change: `([^`]+)`\s*$", "change_id")
    surface_id = _single(body, r"^Live Surface: `([^`]+)`\s*$", "surface_id")
    key = _single(body, r"^Commissioning Key: `([^`]+)`\s*$", "commissioning_key")
    runtime_instance = _single(body, r"^Runtime/Profile: `([^`]+)`\s*$", "runtime_instance")
    refresh_rule = _single(body, r"^Refresh Rule: `([^`]+)`\s*$", "refresh_rule")
    procedure = _single(body, r"^Procedure: (.+)$", "verification_procedure")
    invariant = _single(body, r"^Expected Invariant: (.+)$", "expected_invariant")
    evidence_target = _single(body, r"^Evidence Target: (.+)$", "evidence_target")
    criterion = _single(body, r"^Terminal Success Criterion: (.+)$", "terminal_success_criterion")

    if _SHA.fullmatch(merge_sha) is None or _CHANGE.fullmatch(change_id) is None:
        raise CommissioningIdentityError("identity_shape", "merge/change identity is invalid")
    if _SURFACE.fullmatch(surface_id) is None:
        raise CommissioningIdentityError("surface_id", "surface identity is invalid")
    expected_title = f"Commissioning: {surface_id} for PR #{source_pr} @ {merge_sha[:12]}"
    if issue.get("title") != expected_title:
        raise CommissioningIdentityError("title", "commissioning issue title mismatches body identity")
    return ParsedCommissioningIssue(
        commissioning_issue=number,
        source_issue=source_issue,
        source_pr=source_pr,
        merge_sha=merge_sha,
        change_id=change_id,
        surface_id=surface_id,
        commissioning_key=key,
        runtime_instance=runtime_instance,
        refresh_rule=refresh_rule,
        verification_procedure=procedure,
        expected_invariant=invariant,
        evidence_target=evidence_target,
        terminal_success_criterion=criterion,
    )


def freeze_commissioning_obligation(
    parsed: ParsedCommissioningIssue,
    evidence: LandedChangeEvidence,
    classification: ChangeClassification,
) -> FrozenCommissioningExecution:
    expected = {
        "source_issue": (parsed.source_issue, evidence.source_issue),
        "source_pr": (parsed.source_pr, evidence.source_pr),
        "merge_sha": (parsed.merge_sha, evidence.merge_sha.casefold()),
        "change_id": (parsed.change_id, evidence.change_id),
    }
    for label, (observed, landed) in expected.items():
        if observed != landed:
            raise CommissioningIdentityError(label, f"{label} mismatches landed evidence")
    if classification.state is not ClassificationState.REQUIRED:
        raise CommissioningIdentityError("classification", "landed change has no executable obligation")
    matches = tuple(
        item
        for item in classification.obligations
        if item.surface_id == parsed.surface_id
        and item.commissioning_key == parsed.commissioning_key
    )
    if len(matches) != 1:
        raise CommissioningIdentityError("obligation", "exact commissioning obligation is unavailable")
    obligation = matches[0]
    issue_contract = (
        parsed.runtime_instance,
        parsed.refresh_rule,
        parsed.verification_procedure,
        parsed.expected_invariant,
        parsed.evidence_target,
        parsed.terminal_success_criterion,
    )
    landed_contract = (
        obligation.runtime_instance,
        obligation.refresh_rule,
        obligation.verification_procedure,
        obligation.expected_invariant,
        obligation.evidence_target,
        obligation.terminal_success_criterion,
    )
    if issue_contract != landed_contract:
        raise CommissioningIdentityError(
            "obligation_contract", "commissioning issue contract mismatches landed policy"
        )
    return FrozenCommissioningExecution(
        repository=evidence.repository,
        commissioning_issue=parsed.commissioning_issue,
        source_issue=evidence.source_issue,
        source_pr=evidence.source_pr,
        merge_sha=evidence.merge_sha.casefold(),
        change_id=evidence.change_id,
        surface_id=obligation.surface_id,
        commissioning_key=obligation.commissioning_key,
        runtime_instance=obligation.runtime_instance,
        refresh_rule=obligation.refresh_rule,
        probe_id=obligation.probe_id,
        verification_procedure=obligation.verification_procedure,
        expected_invariant=obligation.expected_invariant,
        evidence_target=obligation.evidence_target,
        terminal_success_criterion=obligation.terminal_success_criterion,
    )


__all__ = [
    "CommissioningIdentityError",
    "FrozenCommissioningExecution",
    "ParsedCommissioningIssue",
    "freeze_commissioning_obligation",
    "parse_generated_commissioning_issue",
]
