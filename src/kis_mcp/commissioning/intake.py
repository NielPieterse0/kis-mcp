from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from .models import (
    ChangeClassification,
    ClassificationState,
    CommissioningIntakeOutcome,
    CommissioningObligation,
    IntakeDisposition,
    LandedChangeEvidence,
)


class ExternalOperationInvoker(Protocol):
    async def external(self, operation: str, arguments: dict[str, Any]) -> Any: ...


class CommissioningIntakeError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _repository_parts(repository: str) -> tuple[str, str]:
    parts = repository.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise CommissioningIntakeError("repository_invalid", "repository must be owner/name")
    return parts[0], parts[1]


def _items(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        if value.get("incomplete_results") is not False:
            raise CommissioningIntakeError(
                "issue_search_invalid", "issue search is incomplete"
            )
        total_count = value.get("total_count")
        if type(total_count) is not int or total_count < 0:
            raise CommissioningIntakeError(
                "issue_search_invalid", "issue search total_count is invalid"
            )
        selected: Any = value.get("items")
    else:
        total_count = None
        selected = value
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise CommissioningIntakeError("issue_search_invalid", "issue search result must contain items")
    if total_count is not None and total_count != len(selected):
        raise CommissioningIntakeError(
            "issue_search_invalid", "issue search exceeds the bounded result page"
        )
    result: list[Mapping[str, Any]] = []
    for item in selected:
        if not isinstance(item, Mapping):
            raise CommissioningIntakeError("issue_search_invalid", "issue search item must be an object")
        result.append(item)
    return tuple(result)


def _contains_key(body: Any, key: str) -> bool:
    if not isinstance(body, str):
        return False
    expected = f"Commissioning Key: `{key}`"
    return any(line.strip() == expected for line in body.splitlines())


def _render_title(obligation: CommissioningObligation, evidence: LandedChangeEvidence) -> str:
    return (
        f"Commissioning: {obligation.surface_id} for PR #{evidence.source_pr} "
        f"@ {evidence.merge_sha[:12]}"
    )


def _render_body(obligation: CommissioningObligation, evidence: LandedChangeEvidence) -> str:
    return "\n".join(
        (
            "## Deterministic commissioning obligation",
            "",
            f"Source Issue: #{evidence.source_issue}",
            f"Source PR: #{evidence.source_pr}",
            f"Merge SHA: `{evidence.merge_sha}`",
            f"Change: `{evidence.change_id}`",
            f"Live Surface: `{obligation.surface_id}`",
            f"Commissioning Key: `{obligation.commissioning_key}`",
            "",
            "## Required live verification",
            "",
            f"Runtime/Profile: `{obligation.runtime_instance}`",
            f"Refresh Rule: `{obligation.refresh_rule}`",
            f"Procedure: {obligation.verification_procedure}",
            f"Expected Invariant: {obligation.expected_invariant}",
            f"Evidence Target: {obligation.evidence_target}",
            f"Terminal Success Criterion: {obligation.terminal_success_criterion}",
            "",
            (
                "This issue is generated deterministically from landed merge evidence. "
                "Source delivery remains complete independently of this commissioning work."
            ),
        )
    )


class CommissioningIntakeService:
    def __init__(self, invoker: ExternalOperationInvoker) -> None:
        self._invoker = invoker

    async def _search(
        self, evidence: LandedChangeEvidence, obligation: CommissioningObligation
    ) -> tuple[Mapping[str, Any], ...]:
        owner, repo = _repository_parts(evidence.repository)
        result = await self._invoker.external(
            "github_search_issues",
            {
                "owner": owner,
                "repo": repo,
                "query": (
                    f'repo:{evidence.repository} "{obligation.commissioning_key}" in:body'
                ),
                "perPage": 100,
                "fields": ["number", "title", "body", "state", "html_url"],
            },
        )
        return tuple(
            item for item in _items(result) if _contains_key(item.get("body"), obligation.commissioning_key)
        )

    @staticmethod
    def _existing_outcome(
        obligation: CommissioningObligation,
        matches: tuple[Mapping[str, Any], ...],
    ) -> CommissioningIntakeOutcome:
        ordered = sorted(
            matches,
            key=lambda item: item.get("number") if isinstance(item.get("number"), int) else 2**31,
        )
        numbers = tuple(
            item["number"] for item in ordered if isinstance(item.get("number"), int)
        )
        if not numbers:
            raise CommissioningIntakeError(
                "issue_search_invalid", "matching commissioning issue has no issue number"
            )
        selected = ordered[0]
        url = selected.get("html_url")
        return CommissioningIntakeOutcome(
            surface_id=obligation.surface_id,
            commissioning_key=obligation.commissioning_key,
            disposition=IntakeDisposition.EXISTING,
            issue_number=numbers[0],
            issue_url=url if isinstance(url, str) else None,
            matching_issue_numbers=numbers,
        )

    async def _create(
        self,
        evidence: LandedChangeEvidence,
        obligation: CommissioningObligation,
    ) -> CommissioningIntakeOutcome:
        owner, repo = _repository_parts(evidence.repository)
        expected_title = _render_title(obligation, evidence)
        expected_body = _render_body(obligation, evidence)
        created = await self._invoker.external(
            "github_issue_write",
            {
                "method": "create",
                "owner": owner,
                "repo": repo,
                "title": expected_title,
                "body": expected_body,
            },
        )
        if not isinstance(created, Mapping) or not isinstance(created.get("number"), int):
            raise CommissioningIntakeError(
                "issue_create_invalid", "created commissioning issue has no issue number"
            )
        issue_number = created["number"]
        verified = await self._invoker.external(
            "github_issue_read",
            {
                "method": "get",
                "owner": owner,
                "repo": repo,
                "issue_number": issue_number,
            },
        )
        if (
            not isinstance(verified, Mapping)
            or verified.get("number") != issue_number
            or verified.get("title") != expected_title
            or verified.get("body") != expected_body
        ):
            raise CommissioningIntakeError(
                "created_issue_verification_failed",
                "created commissioning issue did not retain its deterministic contract",
            )
        url = verified.get("html_url") or created.get("html_url")
        return CommissioningIntakeOutcome(
            surface_id=obligation.surface_id,
            commissioning_key=obligation.commissioning_key,
            disposition=IntakeDisposition.CREATED,
            issue_number=issue_number,
            issue_url=url if isinstance(url, str) else None,
            matching_issue_numbers=(issue_number,),
        )

    async def intake(
        self,
        evidence: LandedChangeEvidence,
        classification: ChangeClassification,
    ) -> tuple[CommissioningIntakeOutcome, ...]:
        if classification.state is not ClassificationState.REQUIRED:
            return ()
        outcomes: list[CommissioningIntakeOutcome] = []
        for obligation in classification.obligations:
            matches = await self._search(evidence, obligation)
            if matches:
                outcomes.append(self._existing_outcome(obligation, matches))
                continue
            outcomes.append(await self._create(evidence, obligation))
        return tuple(outcomes)


__all__ = ["CommissioningIntakeError", "CommissioningIntakeService"]
