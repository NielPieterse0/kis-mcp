from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Protocol

from kis_mcp.commissioning.classifier import classify_change
from kis_mcp.commissioning.evidence import MergedChangeResolver
from kis_mcp.commissioning.models import ChangeClassification, LandedChangeEvidence
from kis_mcp.commissioning.projection import (
    aggregate_commissioning_key,
    aggregate_live_state,
    project_source_live_state,
)
from kis_mcp.commissioning.runner import (
    FrozenCommissioningExecution,
    freeze_commissioning_obligation,
    parse_generated_commissioning_issue,
)
from kis_mcp.commissioning.settings import (
    PostMergeCommissioningSettings,
    PostMergeTargetSettings,
)

from .probes import execute_probe, runtime_generation_gate
from .state import (
    CommissioningStateError,
    CommissioningStateStore,
    ExecutionResult,
    ExecutionState,
)


class RunnerInvoker(Protocol):
    async def external(self, operation: str, arguments: dict[str, Any]) -> Any: ...
    async def read(self, operation: str, arguments: dict[str, Any]) -> Any: ...
    async def change(self, operation: str, arguments: dict[str, Any]) -> Any: ...


IdentityResolver = Callable[
    [str, int, RunnerInvoker],
    Awaitable[tuple[FrozenCommissioningExecution, LandedChangeEvidence, ChangeClassification]],
]


def _fingerprint(frozen: FrozenCommissioningExecution) -> str:
    encoded = json.dumps(
        asdict(frozen), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _repository_parts(repository: str) -> tuple[str, str]:
    owner, separator, repo = repository.partition("/")
    if separator != "/" or not owner or not repo:
        raise ValueError("repository must be owner/name")
    return owner, repo


def _target(
    settings: PostMergeCommissioningSettings, repository: str
) -> PostMergeTargetSettings:
    for item in settings.targets:
        if item.repository.casefold() == repository.casefold():
            return item
    raise ValueError("repository is not a commissioning target")


def _result_payload(state: ExecutionState, *, replayed: bool) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "commissioning_key": state.commissioning_key,
        "attempt": state.attempt,
        "phase": state.phase,
        "result": state.result.value,
        "receipt_id": state.receipt_id,
        "replayed": replayed,
    }


class CommissioningRunnerService:
    def __init__(
        self,
        settings: PostMergeCommissioningSettings,
        store: CommissioningStateStore,
        *,
        invoker: RunnerInvoker,
        identity_resolver: IdentityResolver | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.invoker = invoker
        self.identity_resolver = identity_resolver

    async def _resolve_identity(
        self, repository: str, commissioning_issue: int
    ) -> tuple[FrozenCommissioningExecution, LandedChangeEvidence, ChangeClassification]:
        if self.identity_resolver is not None:
            return await self.identity_resolver(repository, commissioning_issue, self.invoker)
        owner, repo = _repository_parts(repository)
        issue = await self.invoker.external(
            "github_issue_read",
            {
                "method": "get",
                "owner": owner,
                "repo": repo,
                "issue_number": commissioning_issue,
            },
        )
        if not isinstance(issue, Mapping):
            raise TypeError("commissioning issue read returned invalid evidence")
        parsed = parse_generated_commissioning_issue(issue)
        evidence = await MergedChangeResolver(self.invoker, self.settings).resolve(
            repository, parsed.source_pr
        )
        classification = classify_change(evidence, self.settings)
        frozen = freeze_commissioning_obligation(parsed, evidence, classification)
        return frozen, evidence, classification

    async def _work_card(
        self,
        target: PostMergeTargetSettings,
        frozen: FrozenCommissioningExecution,
    ) -> Mapping[str, Any]:
        value = await self.invoker.read(
            "project_management_board_data",
            {
                "project_id": target.project_id,
                "include_history": False,
                "query": str(frozen.commissioning_issue),
                "group_by": "state",
                "item_limit": 1000,
            },
        )
        result = value.get("result") if isinstance(value, Mapping) else None
        cards = result.get("cards") if isinstance(result, Mapping) else None
        if (
            not isinstance(value, Mapping)
            or not isinstance(value.get("provenance"), Mapping)
            or value["provenance"].get("complete") is not True
            or not isinstance(result, Mapping)
            or result.get("complete") is not True
            or result.get("truncated") is not False
            or not isinstance(cards, list)
        ):
            raise RuntimeError("commissioning Work evidence is incomplete")
        matches = [
            card
            for card in cards
            if isinstance(card, Mapping)
            and card.get("number") == frozen.commissioning_issue
            and str(card.get("repository", "")).casefold()
            == frozen.repository.casefold()
        ]
        if len(matches) != 1:
            raise RuntimeError("commissioning issue Work card is not uniquely observable")
        return matches[0]

    async def _claim_card(
        self,
        target: PostMergeTargetSettings,
        frozen: FrozenCommissioningExecution,
        execution_owner: str,
    ) -> Mapping[str, Any]:
        card = await self._work_card(target, frozen)
        if (
            card.get("source_state") != "open"
            or card.get("work_state") != "active"
            or card.get("execution_owner") != execution_owner
        ):
            raise RuntimeError(
                "commissioning issue must be open, uniquely Active, and claimed"
            )
        return card

    def _proof_receipt(
        self,
        frozen: FrozenCommissioningExecution,
        state: ExecutionState,
        *,
        result: ExecutionResult,
        code: str,
        runtime_source_revision: str | None,
        probe_operation: str | None,
        response_fingerprint: str | None,
        evidence: Mapping[str, Any],
    ) -> str:
        occurred_at = datetime.now(UTC)
        payload = {
            "schema_version": 1,
            "kind": "execution",
            "repository": frozen.repository,
            "commissioning_issue": frozen.commissioning_issue,
            "source_issue": frozen.source_issue,
            "source_pr": frozen.source_pr,
            "merge_sha": frozen.merge_sha,
            "surface_id": frozen.surface_id,
            "commissioning_key": frozen.commissioning_key,
            "attempt": state.attempt,
            "probe_id": frozen.probe_id,
            "probe_operation": probe_operation,
            "result": result.value,
            "code": code,
            "runtime_source_revision": runtime_source_revision,
            "response_fingerprint": response_fingerprint,
            "evidence": dict(evidence),
            "occurred_at": occurred_at.isoformat(),
        }
        return self.store.persist_receipt(payload, occurred_at).receipt_id

    async def _project_aggregate(
        self,
        target: PostMergeTargetSettings,
        evidence: LandedChangeEvidence,
        classification: ChangeClassification,
    ) -> tuple[str, str]:
        keys = tuple(item.commissioning_key for item in classification.obligations)
        aggregate_key = aggregate_commissioning_key(
            evidence.repository, evidence.merge_sha, keys
        )
        obligation_evidence: list[dict[str, Any]] = []
        states: list[str] = []
        for obligation in classification.obligations:
            execution = self.store.load_execution_state(obligation.commissioning_key)
            if execution is None:
                states.append("pending")
                obligation_evidence.append(
                    {"commissioning_key": obligation.commissioning_key, "state": "pending", "receipt_id": None}
                )
                continue
            states.append(execution.result.value)
            obligation_evidence.append(
                {
                    "commissioning_key": obligation.commissioning_key,
                    "state": execution.result.value,
                    "receipt_id": execution.receipt_id,
                }
            )
        live_state = aggregate_live_state(states)
        occurred_at = datetime.now(UTC)
        payload = {
            "schema_version": 1,
            "kind": "aggregate",
            "repository": evidence.repository,
            "source_issue": evidence.source_issue,
            "source_pr": evidence.source_pr,
            "merge_sha": evidence.merge_sha,
            "commissioning_key": aggregate_key,
            "live_verification": live_state,
            "obligations": obligation_evidence,
        }
        aggregate_ref = self.store.persist_receipt(payload, occurred_at)
        await project_source_live_state(
            self.invoker,
            project_id=target.project_id,
            repository=evidence.repository,
            source_issue=evidence.source_issue,
            live_state=live_state,
            commissioning_key=aggregate_key,
            evidence_reference=f"commissioning-evidence:{aggregate_ref.sha256}",
            idempotency_key=f"commission-source-{aggregate_ref.sha256}",
        )
        return live_state, aggregate_ref.receipt_id

    async def _block_work(
        self,
        target: PostMergeTargetSettings,
        frozen: FrozenCommissioningExecution,
        state: ExecutionState,
    ) -> None:
        result = await self.invoker.change(
            "project_management_transition_work",
            {
                "project_id": target.project_id,
                "repository": frozen.repository,
                "issue_number": frozen.commissioning_issue,
                "target": "blocked",
                "apply": True,
                "idempotency_key": f"commission-block-{state.attempt}-{hashlib.sha256(frozen.commissioning_key.encode()).hexdigest()[:24]}",
            },
        )
        outcomes = result.get("outcomes") if isinstance(result, Mapping) else None
        if not isinstance(outcomes, list) or not outcomes or not all(
            isinstance(item, Mapping) and item.get("success") is True for item in outcomes
        ):
            raise RuntimeError("commissioning Work blocked transition failed")

    async def _complete_work(
        self,
        target: PostMergeTargetSettings,
        frozen: FrozenCommissioningExecution,
        state: ExecutionState,
        claim: Mapping[str, Any],
        execution_owner: str,
    ) -> None:
        record = {
            "record_id": f"TASK-{frozen.commissioning_issue}",
            "project_id": target.project_id,
            "title": str(claim.get("title") or f"Commissioning {frozen.surface_id}"),
            "record_type": str(claim.get("record_type") or "task"),
            "state": "active",
            "priority": str(claim.get("priority") or "medium"),
            "effort": str(claim.get("effort") or "medium"),
            "execution_owner": execution_owner,
            "documentation_mode": "required",
            "documentation_impact": "none",
            "documentation_rationale": "Commissioning work is operational-only; no repository documentation artifact is required.",
            "documentation_reviewer": "commissioning-runner",
            "traceability_required": False,
        }
        result = await self.invoker.change(
            "project_management_complete_work",
            {
                "project_id": target.project_id,
                "repository": frozen.repository,
                "issue_number": frozen.commissioning_issue,
                "record": record,
                "apply": True,
                "idempotency_key": f"commission-complete-{state.attempt}-{hashlib.sha256(frozen.commissioning_key.encode()).hexdigest()[:24]}",
            },
        )
        outcomes = result.get("outcomes") if isinstance(result, Mapping) else None
        if (
            not isinstance(result, Mapping)
            or result.get("source_close_required") is not True
            or not isinstance(outcomes, list)
            or not outcomes
            or not all(
                isinstance(item, Mapping) and item.get("success") is True
                for item in outcomes
            )
        ):
            raise RuntimeError("commissioning Work completion was not authorized")

    async def _close_issue(
        self,
        frozen: FrozenCommissioningExecution,
    ) -> None:
        owner, repo = _repository_parts(frozen.repository)
        await self.invoker.external(
            "github_issue_write",
            {
                "method": "update",
                "owner": owner,
                "repo": repo,
                "issue_number": frozen.commissioning_issue,
                "state": "closed",
                "state_reason": "completed",
            },
        )
        verified = await self.invoker.external(
            "github_issue_read",
            {
                "method": "get",
                "owner": owner,
                "repo": repo,
                "issue_number": frozen.commissioning_issue,
            },
        )
        if (
            not isinstance(verified, Mapping)
            or verified.get("number") != frozen.commissioning_issue
            or verified.get("state") != "closed"
        ):
            raise RuntimeError("commissioning issue close was not confirmed")

    def execution(self, commissioning_key: str) -> dict[str, Any]:
        state = self.store.load_execution_state(commissioning_key)
        if state is None:
            raise KeyError(commissioning_key)
        result = _result_payload(state, replayed=True)
        if state.receipt_id is not None:
            result["receipt"] = self.store.load_receipt(state.receipt_id)
        return result

    async def run(
        self,
        repository: str,
        commissioning_issue: int,
        *,
        execution_owner: str,
        retry: bool = False,
    ) -> dict[str, Any]:
        target = _target(self.settings, repository)
        frozen, evidence, classification = await self._resolve_identity(
            repository, commissioning_issue
        )
        if frozen.commissioning_issue != commissioning_issue:
            raise RuntimeError("resolved commissioning issue identity changed")
        now = datetime.now(UTC)
        fingerprint = _fingerprint(frozen)
        existing = self.store.load_execution_state(frozen.commissioning_key)
        claim: Mapping[str, Any] | None = None
        if existing is not None:
            if existing.contract_fingerprint != fingerprint:
                raise CommissioningStateError(
                    "execution_contract_mismatch",
                    "frozen commissioning contract changed",
                )
            if existing.phase == "terminal":
                if not retry or existing.result is ExecutionResult.PASSED:
                    return _result_payload(existing, replayed=True)
                claim = await self._claim_card(target, frozen, execution_owner)
                state = self.store.begin_execution(
                    frozen.commissioning_key,
                    fingerprint,
                    now,
                    retry=True,
                )
            else:
                state = existing
        else:
            claim = await self._claim_card(target, frozen, execution_owner)
            state = self.store.begin_execution(
                frozen.commissioning_key,
                fingerprint,
                now,
                retry=False,
            )

        if state.phase == "initialized":
            claim = claim or await self._claim_card(target, frozen, execution_owner)
            gate = await runtime_generation_gate(
                frozen,
                self.invoker,
                project_id=target.project_id,
            )
            if not gate.ready:
                receipt_id = self._proof_receipt(
                    frozen,
                    state,
                    result=ExecutionResult.BLOCKED,
                    code=gate.code,
                    runtime_source_revision=gate.source_revision,
                    probe_operation=None,
                    response_fingerprint=None,
                    evidence={"refresh_rule": frozen.refresh_rule},
                )
                state = self.store.update_execution(
                    state,
                    phase="proof_persisted",
                    result=ExecutionResult.BLOCKED,
                    receipt_id=receipt_id,
                    updated_at=datetime.now(UTC),
                )
            else:
                probe = await execute_probe(
                    frozen,
                    self.invoker,
                    project_id=target.project_id,
                    execution_owner=execution_owner,
                )
                proof_result = (
                    ExecutionResult.PASSED if probe.passed else ExecutionResult.FAILED
                )
                receipt_id = self._proof_receipt(
                    frozen,
                    state,
                    result=proof_result,
                    code=probe.code,
                    runtime_source_revision=gate.source_revision,
                    probe_operation=probe.operation,
                    response_fingerprint=probe.response_fingerprint,
                    evidence=probe.evidence,
                )
                state = self.store.update_execution(
                    state,
                    phase="proof_persisted",
                    result=proof_result,
                    receipt_id=receipt_id,
                    updated_at=datetime.now(UTC),
                )

        if state.phase == "proof_persisted":
            await self._project_aggregate(target, evidence, classification)
            state = self.store.update_execution(
                state,
                phase="source_projected",
                result=state.result,
                receipt_id=state.receipt_id,
                updated_at=datetime.now(UTC),
            )

        if state.result is ExecutionResult.FAILED:
            state = self.store.update_execution(
                state,
                phase="terminal",
                result=ExecutionResult.FAILED,
                receipt_id=state.receipt_id,
                updated_at=datetime.now(UTC),
            )
            return _result_payload(state, replayed=False)

        if state.result is ExecutionResult.BLOCKED:
            card = await self._work_card(target, frozen)
            if card.get("work_state") == "blocked":
                pass
            elif (
                card.get("work_state") == "active"
                and card.get("execution_owner") == execution_owner
            ):
                await self._block_work(target, frozen, state)
            else:
                raise RuntimeError(
                    "commissioning Work cannot resume blocked closeout from current state"
                )
            state = self.store.update_execution(
                state,
                phase="terminal",
                result=ExecutionResult.BLOCKED,
                receipt_id=state.receipt_id,
                updated_at=datetime.now(UTC),
            )
            return _result_payload(state, replayed=False)

        if state.phase == "source_projected":
            card = claim or await self._work_card(target, frozen)
            if card.get("work_state") == "done":
                pass
            elif (
                card.get("work_state") == "active"
                and card.get("execution_owner") == execution_owner
            ):
                await self._complete_work(
                    target, frozen, state, card, execution_owner
                )
            else:
                raise RuntimeError(
                    "commissioning Work cannot resume successful closeout from current state"
                )
            state = self.store.update_execution(
                state,
                phase="work_completed",
                result=ExecutionResult.PASSED,
                receipt_id=state.receipt_id,
                updated_at=datetime.now(UTC),
            )

        if state.phase == "work_completed":
            await self._close_issue(frozen)
            state = self.store.update_execution(
                state,
                phase="terminal",
                result=ExecutionResult.PASSED,
                receipt_id=state.receipt_id,
                updated_at=datetime.now(UTC),
            )
        return _result_payload(state, replayed=False)


__all__ = ["CommissioningRunnerService", "IdentityResolver", "RunnerInvoker"]
