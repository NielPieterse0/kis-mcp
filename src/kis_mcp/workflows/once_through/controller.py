from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import fingerprint

PromotionInvoker = Callable[[str, dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]

_STAGES = (
    "refresh_default",
    "reconcile_candidate",
    "create_pull_request",
    "exact_head_actions",
    "merge_readiness",
    "merge_exact_head",
    "refresh_landed",
    "documentation_reconcile",
    "work_done",
    "cleanup",
)


@dataclass(frozen=True, slots=True)
class PromotionExecution:
    operation_id: str
    completed: tuple[str, ...]
    current_stage: str | None
    state: str
    observations: Mapping[str, Any]
    terminal_receipt: Mapping[str, Any] | None = None

    def to_json_dict(self) -> dict[str, Any]:
        payload = {
            "contract": "promotion-execution-v1", "operation_id": self.operation_id,
            "completed": list(self.completed), "current_stage": self.current_stage,
            "state": self.state, "observations": dict(self.observations),
        }
        if self.terminal_receipt is not None:
            payload["terminal_receipt"] = dict(self.terminal_receipt)
        return payload


class PromotionStateStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, operation_id: str) -> Path:
        return self.root / f"{fingerprint(operation_id)[:24]}.json"

    def load(self, operation_id: str) -> dict[str, Any] | None:
        try:
            value = json.loads(self.path(operation_id).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        if not isinstance(value, dict):
            raise ValueError("PROMOTION_STATE_INVALID: checkpoint is not an object")
        return value

    def save(self, operation_id: str, payload: Mapping[str, Any]) -> None:
        path = self.path(operation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(dict(payload), sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        os.replace(temporary, path)


def _mapping(observations: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = observations.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _terminal_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"PROMOTION_TERMINAL_RECEIPT_INVALID: {label} is missing")
    return value.strip()


def _terminal_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"PROMOTION_TERMINAL_RECEIPT_INVALID: {label} is invalid")
    return value


def build_terminal_receipt(
    operation_id: str,
    handoff: Mapping[str, Any],
    observations: Mapping[str, Any],
) -> dict[str, Any]:
    created = _mapping(observations, "create_pull_request")
    actions = _mapping(observations, "exact_head_actions")
    merge = _mapping(observations, "merge_exact_head")
    landed = _mapping(observations, "refresh_landed")
    documentation = _mapping(observations, "documentation_reconcile")
    work_done = _mapping(observations, "work_done")
    cleanup = _mapping(observations, "cleanup")
    work_id = _terminal_text(handoff.get("work_id"), "Work ID")
    change_id = _terminal_text(handoff.get("change_id"), "Change ID")
    source_commit = _terminal_text(handoff.get("source_commit_sha"), "source commit")
    pull_number = _terminal_int(created.get("pull_number"), "pull request number")
    head_sha = _terminal_text(created.get("head_sha"), "pull request head")
    run_ids = actions.get("run_ids")
    if not isinstance(run_ids, list) or len(run_ids) != 1:
        raise ValueError("PROMOTION_TERMINAL_RECEIPT_INVALID: exact Actions run identity is missing")
    actions_run_id = _terminal_int(run_ids[0], "Actions run ID")
    actions_reference = _terminal_text(actions.get("reference"), "Actions reference")
    merge_sha = _terminal_text(
        merge.get("merge_commit_sha") or merge.get("merge_commit"), "merge commit"
    )
    landed_sha = _terminal_text(landed.get("landed_sha"), "landed SHA")
    documentation_revision = _terminal_text(
        documentation.get("completion_revision"), "documentation completion revision"
    )
    if documentation_revision != landed_sha:
        raise ValueError("PROMOTION_TERMINAL_RECEIPT_INVALID: documentation revision differs from landed SHA")
    documentation_event = _mapping(documentation, "event")
    _terminal_text(documentation_event.get("event_id"), "documentation event ID")
    if _terminal_text(
        documentation_event.get("completion_revision"), "documentation event completion revision"
    ) != landed_sha:
        raise ValueError("PROMOTION_TERMINAL_RECEIPT_INVALID: documentation event revision differs from landed SHA")
    record = _mapping(work_done, "record") or _mapping(documentation, "record")
    typed_record_id = _terminal_text(record.get("record_id"), "typed Work record ID")
    work_completion = work_done.get("work_completion")
    if not isinstance(work_completion, Mapping):
        raise ValueError("PROMOTION_TERMINAL_RECEIPT_INVALID: Work completion receipt is missing")
    source_close = {
        "required": work_done.get("source_close_required") is True,
        "applied": work_done.get("source_close_applied") is True,
        "reconciled_after_error": work_done.get("source_close_reconciled_after_error") is True,
    }
    if source_close["required"] and not source_close["applied"]:
        raise ValueError("PROMOTION_TERMINAL_RECEIPT_INVALID: required source closure is incomplete")
    if cleanup.get("status") not in {"applied", "satisfied", "passed"}:
        raise ValueError("PROMOTION_TERMINAL_RECEIPT_INVALID: cleanup is incomplete")
    post_land_restart = cleanup.get("post_land_restart")
    if post_land_restart is not None:
        if not isinstance(post_land_restart, Mapping):
            raise ValueError("PROMOTION_TERMINAL_RECEIPT_INVALID: post-land restart receipt is invalid")
        if _terminal_text(post_land_restart.get("landed_sha"), "post-land landed SHA") != landed_sha:
            raise ValueError("PROMOTION_TERMINAL_RECEIPT_INVALID: post-land landed SHA mismatch")
        if _terminal_text(post_land_restart.get("launched_sha"), "post-land launched SHA") != landed_sha:
            raise ValueError("PROMOTION_TERMINAL_RECEIPT_INVALID: post-land launched SHA mismatch")
    return {
        "contract": "promotion-terminal-receipt-v1",
        "operation_id": operation_id,
        "status": "done",
        "work_id": work_id,
        "typed_record_id": typed_record_id,
        "specification_record_id": typed_record_id if typed_record_id.startswith("SPEC-") else None,
        "change_id": change_id,
        "source_commit_sha": source_commit,
        "pull_number": pull_number,
        "head_sha": head_sha,
        "actions_run_ids": [actions_run_id],
        "actions_reference": actions_reference,
        "merge_commit_sha": merge_sha,
        "landed_sha": landed_sha,
        "documentation_completion_revision": documentation_revision,
        "documentation_event": documentation_event,
        "work_completion": dict(work_completion),
        "source_close": source_close,
        "cleanup": cleanup,
        "post_land_restart": dict(post_land_restart) if isinstance(post_land_restart, Mapping) else None,
    }


class PromotionController:
    def __init__(self, invoker: PromotionInvoker, store: PromotionStateStore) -> None:
        self._invoker = invoker
        self._store = store

    async def converge(
        self,
        *,
        operation_id: str,
        promotion_handoff: Mapping[str, Any],
    ) -> PromotionExecution:
        if promotion_handoff.get("status") != "promotion_ready":
            raise ValueError("PROMOTION_HANDOFF_INVALID: status is not promotion_ready")
        handoff_fingerprint = fingerprint(dict(promotion_handoff))
        done: list[str] = []
        observations: dict[str, Any] = {}
        checkpoint = self._store.load(operation_id)
        terminal_receipt: dict[str, Any] | None = None
        if checkpoint is not None:
            if checkpoint.get("handoff_fingerprint") != handoff_fingerprint:
                raise ValueError("PROMOTION_STATE_INVALID: handoff identity changed")
            done = list(checkpoint.get("completed", ()))
            observations = dict(checkpoint.get("observations", {}))
            stored_terminal = checkpoint.get("terminal_receipt")
            if isinstance(stored_terminal, Mapping):
                terminal_receipt = dict(stored_terminal)
        if tuple(done) != _STAGES[: len(done)] or len(set(done)) != len(done):
            raise ValueError("PROMOTION_STATE_INVALID: completed stages must be a unique ordered prefix")
        if tuple(done) == _STAGES and terminal_receipt is not None:
            return PromotionExecution(
                operation_id, tuple(done), None, "done", observations, terminal_receipt
            )
        for stage in _STAGES[len(done) :]:
            result = await self._invoker(stage, dict(promotion_handoff), dict(observations))
            observations[stage] = result
            if result.get("status") not in {"passed", "satisfied", "applied"}:
                execution = PromotionExecution(operation_id, tuple(done), stage, "blocked", observations)
                self._store.save(operation_id, {**execution.to_json_dict(), "handoff_fingerprint": handoff_fingerprint})
                return execution
            done.append(stage)
            self._store.save(operation_id, {
                "handoff_fingerprint": handoff_fingerprint,
                "completed": done,
                "observations": observations,
            })
        terminal_receipt = build_terminal_receipt(operation_id, promotion_handoff, observations)
        execution = PromotionExecution(
            operation_id, tuple(done), None, "done", observations, terminal_receipt
        )
        self._store.save(
            operation_id,
            {**execution.to_json_dict(), "handoff_fingerprint": handoff_fingerprint},
        )
        return execution


__all__ = [
    "PromotionController",
    "PromotionExecution",
    "PromotionStateStore",
    "build_terminal_receipt",
]
