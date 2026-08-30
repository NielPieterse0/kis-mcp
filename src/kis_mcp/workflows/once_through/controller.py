from __future__ import annotations

import json
import os
import time
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

    def recent_terminal_receipts(self, limit: int = 20) -> tuple[dict[str, Any], ...]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if not self.root.is_dir():
            return ()
        values: list[tuple[int, dict[str, Any]]] = []
        for path in self.root.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                receipt = payload.get("terminal_receipt") if isinstance(payload, dict) else None
                stat = path.stat()
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(receipt, dict) and receipt.get("contract") == "promotion-terminal-receipt-v1":
                completed_at_ns = receipt.get("completed_at_ns")
                ordering = (
                    completed_at_ns
                    if isinstance(completed_at_ns, int) and not isinstance(completed_at_ns, bool) and completed_at_ns > 0
                    else stat.st_mtime_ns
                )
                values.append((ordering, dict(receipt)))
        values.sort(key=lambda item: item[0], reverse=True)
        return tuple(receipt for _, receipt in values[:limit])


def _mapping(observations: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = observations.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _new_telemetry() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stage_timings_ms": {},
        "stage_attempts": {},
        "provider_reads": 0,
        "provider_mutations": 0,
        "list_pages_scanned": 0,
        "tool_calls": 0,
        "verification_invocations": 0,
        "review_invocations": 0,
        "duplicate_verification_attempts": 0,
        "duplicate_review_attempts": 0,
        "promotion_review_invocations": 0,
        "duplicate_proof_attempts": 0,
        "proof_read_fingerprints": [],
        "replay_count": 0,
        "blocked_reasons": [],
        "operation_counts": {},
    }


def _merge_stage_audit(telemetry: dict[str, Any], result: Mapping[str, Any]) -> None:
    audit = result.get("_audit")
    if not isinstance(audit, Mapping):
        return
    for key in (
        "provider_reads", "provider_mutations", "list_pages_scanned", "tool_calls",
        "verification_invocations", "review_invocations", "duplicate_verification_attempts",
        "duplicate_review_attempts", "promotion_review_invocations", "duplicate_proof_attempts",
    ):
        value = audit.get(key, 0)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            telemetry[key] = int(telemetry.get(key, 0)) + value
    proofs = telemetry.setdefault("proof_read_fingerprints", [])
    raw_proofs = audit.get("proof_read_fingerprints")
    if isinstance(proofs, list) and isinstance(raw_proofs, list):
        for value in raw_proofs:
            if isinstance(value, str) and value and value not in proofs and len(proofs) < 128:
                proofs.append(value)
    counts = telemetry.setdefault("operation_counts", {})
    raw_counts = audit.get("operation_counts")
    if isinstance(counts, dict) and isinstance(raw_counts, Mapping):
        for name, value in raw_counts.items():
            if isinstance(name, str) and isinstance(value, int) and value > 0:
                counts[name] = int(counts.get(name, 0)) + value


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
    telemetry: Mapping[str, Any] | None = None,
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
        "completed_at_ns": time.time_ns(),
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
        "verification_lineage": {
            "implementation_revision": source_commit,
            "provider_exact_head_revision": head_sha,
            "reconciled_head_differs": source_commit != head_sha,
            "different_revision_justification": (
                "registered reconciliation preserves the verified source tree on the current remote-default parent; provider-native Actions verifies that exact reconciled PR head"
                if source_commit != head_sha else None
            ),
        },
        "telemetry": dict(telemetry or {}),
        "closeout_projection": {
            "authority": "terminal_receipt",
            "tracked_change_record_role": "historical_pre_merge",
            "checklist": {
                "pull_request": True,
                "exact_head_actions": True,
                "merge": True,
                "documentation": True,
                "work_done": True,
                "source_closed": (not source_close["required"] or source_close["applied"]),
                "cleanup": True,
                "post_land_restart": post_land_restart is None or bool(post_land_restart.get("launched_sha")),
            },
        },
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
        telemetry = _new_telemetry()
        execution = promotion_handoff.get("execution")
        if checkpoint is None and isinstance(execution, Mapping):
            if execution.get("contract") == "change-execution-result-v2":
                telemetry["verification_invocations"] = 1
                reviews = execution.get("reviews")
                if isinstance(reviews, (list, tuple)):
                    review_counts: dict[str, int] = {}
                    for review in reviews:
                        if not isinstance(review, Mapping):
                            continue
                        telemetry["review_invocations"] += 1
                        review_type = str(
                            review.get("review_type")
                            or review.get("type")
                            or review.get("agent_id")
                            or "unknown"
                        ).strip().casefold()
                        review_counts[review_type] = review_counts.get(review_type, 0) + 1
                    telemetry["duplicate_review_attempts"] = sum(
                        count - 1 for count in review_counts.values() if count > 1
                    )
        if checkpoint is not None:
            if checkpoint.get("handoff_fingerprint") != handoff_fingerprint:
                raise ValueError("PROMOTION_STATE_INVALID: handoff identity changed")
            done = list(checkpoint.get("completed", ()))
            observations = dict(checkpoint.get("observations", {}))
            persisted_telemetry = checkpoint.get("telemetry")
            if isinstance(persisted_telemetry, Mapping):
                telemetry.update(dict(persisted_telemetry))
            telemetry["replay_count"] = int(telemetry.get("replay_count", 0)) + 1
            stored_terminal = checkpoint.get("terminal_receipt")
            if isinstance(stored_terminal, Mapping):
                terminal_receipt = dict(stored_terminal)
        if tuple(done) != _STAGES[: len(done)] or len(set(done)) != len(done):
            raise ValueError("PROMOTION_STATE_INVALID: completed stages must be a unique ordered prefix")
        if tuple(done) == _STAGES and terminal_receipt is not None:
            terminal_receipt["telemetry"] = dict(telemetry)
            self._store.save(
                operation_id,
                {
                    **checkpoint,
                    "state": "done",
                    "current_stage": None,
                    "terminal_receipt": terminal_receipt,
                    "telemetry": telemetry,
                },
            )
            return PromotionExecution(
                operation_id, tuple(done), None, "done", observations, terminal_receipt
            )
        for stage in _STAGES[len(done) :]:
            attempts = telemetry.setdefault("stage_attempts", {})
            attempts[stage] = int(attempts.get(stage, 0)) + 1
            self._store.save(operation_id, {
                "handoff_fingerprint": handoff_fingerprint,
                "completed": done,
                "observations": observations,
                "telemetry": telemetry,
                "current_stage": stage,
                "state": "running",
            })
            started_ns = time.perf_counter_ns()
            try:
                result = await self._invoker(stage, dict(promotion_handoff), dict(observations))
            except Exception:
                elapsed_ms = max(0, (time.perf_counter_ns() - started_ns) // 1_000_000)
                timings = telemetry.setdefault("stage_timings_ms", {})
                timings[stage] = int(timings.get(stage, 0)) + elapsed_ms
                persisted = self._store.load(operation_id) or {}
                inflight = persisted.get("inflight_audit")
                if isinstance(inflight, Mapping):
                    _merge_stage_audit(telemetry, {"_audit": inflight})
                self._store.save(operation_id, {
                    "handoff_fingerprint": handoff_fingerprint,
                    "completed": done,
                    "observations": observations,
                    "telemetry": telemetry,
                    "current_stage": stage,
                    "state": "failed",
                })
                raise
            elapsed_ms = max(0, (time.perf_counter_ns() - started_ns) // 1_000_000)
            timings = telemetry.setdefault("stage_timings_ms", {})
            timings[stage] = int(timings.get(stage, 0)) + elapsed_ms
            _merge_stage_audit(telemetry, result)
            observations[stage] = result
            if result.get("status") not in {"passed", "satisfied", "applied"}:
                reason = result.get("reason")
                if isinstance(reason, str) and reason:
                    blocked = telemetry.setdefault("blocked_reasons", [])
                    if reason not in blocked:
                        blocked.append(reason)
                execution = PromotionExecution(operation_id, tuple(done), stage, "blocked", observations)
                self._store.save(operation_id, {
                    **execution.to_json_dict(),
                    "handoff_fingerprint": handoff_fingerprint,
                    "telemetry": telemetry,
                })
                return execution
            done.append(stage)
            self._store.save(operation_id, {
                "handoff_fingerprint": handoff_fingerprint,
                "completed": done,
                "observations": observations,
                "telemetry": telemetry,
            })
        terminal_receipt = build_terminal_receipt(
            operation_id, promotion_handoff, observations, telemetry
        )
        execution = PromotionExecution(
            operation_id, tuple(done), None, "done", observations, terminal_receipt
        )
        self._store.save(
            operation_id,
            {
                **execution.to_json_dict(),
                "handoff_fingerprint": handoff_fingerprint,
                "telemetry": telemetry,
            },
        )
        return execution


__all__ = [
    "PromotionController",
    "PromotionExecution",
    "PromotionStateStore",
    "build_terminal_receipt",
]
