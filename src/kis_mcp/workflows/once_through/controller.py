from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import fingerprint

PromotionInvoker = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

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

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "contract": "promotion-execution-v1", "operation_id": self.operation_id,
            "completed": list(self.completed), "current_stage": self.current_stage,
            "state": self.state, "observations": dict(self.observations),
        }


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
        if checkpoint is not None:
            if checkpoint.get("handoff_fingerprint") != handoff_fingerprint:
                raise ValueError("PROMOTION_STATE_INVALID: handoff identity changed")
            done = list(checkpoint.get("completed", ()))
            observations = dict(checkpoint.get("observations", {}))
        if tuple(done) != _STAGES[: len(done)] or len(set(done)) != len(done):
            raise ValueError("PROMOTION_STATE_INVALID: completed stages must be a unique ordered prefix")
        for stage in _STAGES[len(done) :]:
            result = await self._invoker(stage, dict(promotion_handoff))
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
        execution = PromotionExecution(operation_id, tuple(done), None, "done", observations)
        self._store.save(operation_id, {**execution.to_json_dict(), "handoff_fingerprint": handoff_fingerprint})
        return execution


__all__ = ["PromotionController", "PromotionExecution", "PromotionStateStore"]
