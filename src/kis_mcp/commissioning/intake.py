from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
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


Sleep = Callable[[float], Awaitable[None]]
_CONFIRMATION_DELAYS_SECONDS = (0.0, 0.25, 0.75, 1.5)


def _normalized_contract_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip()


def _matches_created_contract(
    value: Any,
    *,
    expected_title: str,
    expected_body: str,
    expected_number: int | None = None,
) -> bool:
    if not isinstance(value, Mapping):
        return False
    number = value.get("number")
    if type(number) is not int or number <= 0:
        return False
    if expected_number is not None and number != expected_number:
        return False
    return (
        _normalized_contract_text(value.get("title"))
        == _normalized_contract_text(expected_title)
        and _normalized_contract_text(value.get("body"))
        == _normalized_contract_text(expected_body)
    )


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
    def __init__(
        self,
        invoker: ExternalOperationInvoker,
        *,
        sleep: Sleep = asyncio.sleep,
        confirmation_delays: tuple[float, ...] = _CONFIRMATION_DELAYS_SECONDS,
    ) -> None:
        self._invoker = invoker
        self._sleep = sleep
        self._confirmation_delays = confirmation_delays

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

    async def _confirm_created(
        self,
        evidence: LandedChangeEvidence,
        obligation: CommissioningObligation,
        *,
        created: Any,
        create_error: Exception | None,
        expected_title: str,
        expected_body: str,
    ) -> CommissioningIntakeOutcome:
        owner, repo = _repository_parts(evidence.repository)
        created_number = (
            created.get("number")
            if isinstance(created, Mapping)
            and type(created.get("number")) is int
            and created.get("number") > 0
            else None
        )
        created_url = created.get("html_url") if isinstance(created, Mapping) else None
        last_detail = "provider write was not yet observable"

        for delay in self._confirmation_delays or (0.0,):
            if delay > 0:
                await self._sleep(delay)

            if created_number is not None:
                try:
                    verified = await self._invoker.external(
                        "github_issue_read",
                        {
                            "method": "get",
                            "owner": owner,
                            "repo": repo,
                            "issue_number": created_number,
                        },
                    )
                except (RuntimeError, TypeError, ValueError) as exc:
                    last_detail = f"direct read-back raised {type(exc).__name__}"
                else:
                    if _matches_created_contract(
                        verified,
                        expected_title=expected_title,
                        expected_body=expected_body,
                        expected_number=created_number,
                    ):
                        url = verified.get("html_url") or created_url
                        return CommissioningIntakeOutcome(
                            surface_id=obligation.surface_id,
                            commissioning_key=obligation.commissioning_key,
                            disposition=IntakeDisposition.CREATED,
                            issue_number=created_number,
                            issue_url=url if isinstance(url, str) else None,
                            matching_issue_numbers=(created_number,),
                        )
                    last_detail = "direct read-back did not yet match the deterministic contract"

            try:
                matches = await self._search(evidence, obligation)
            except (RuntimeError, TypeError, ValueError) as exc:
                last_detail = f"deterministic-key search raised {type(exc).__name__}"
                continue

            confirmed = tuple(
                item
                for item in matches
                if _matches_created_contract(
                    item,
                    expected_title=expected_title,
                    expected_body=expected_body,
                )
            )
            if confirmed:
                ordered = sorted(confirmed, key=lambda item: item["number"])
                numbers = tuple(item["number"] for item in ordered)
                selected = ordered[0]
                url = selected.get("html_url") or created_url
                return CommissioningIntakeOutcome(
                    surface_id=obligation.surface_id,
                    commissioning_key=obligation.commissioning_key,
                    disposition=IntakeDisposition.CREATED,
                    issue_number=numbers[0],
                    issue_url=url if isinstance(url, str) else None,
                    matching_issue_numbers=numbers,
                )
            if matches:
                last_detail = "deterministic key was visible but required contract content was not"

        if create_error is not None or created_number is None:
            raise CommissioningIntakeError(
                "issue_create_unconfirmed",
                f"provider write outcome could not be reconciled: {last_detail}",
            ) from create_error
        raise CommissioningIntakeError(
            "created_issue_verification_failed",
            f"created commissioning issue could not be confirmed: {last_detail}",
        )

    async def _create(
        self,
        evidence: LandedChangeEvidence,
        obligation: CommissioningObligation,
    ) -> CommissioningIntakeOutcome:
        owner, repo = _repository_parts(evidence.repository)
        expected_title = _render_title(obligation, evidence)
        expected_body = _render_body(obligation, evidence)
        create_error: Exception | None = None
        try:
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
        except (RuntimeError, TypeError, ValueError) as exc:
            created = None
            create_error = exc

        return await self._confirm_created(
            evidence,
            obligation,
            created=created,
            create_error=create_error,
            expected_title=expected_title,
            expected_body=expected_body,
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
