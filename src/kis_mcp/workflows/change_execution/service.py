from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from .contracts import ChangeExecutionResult, ChangeExecutionStepResult

Invoker = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

_REVIEW_TYPES = frozenset({
    "code-quality",
    "safety-security",
    "architecture",
    "performance",
    "test-quality",
    "documentation",
    "api-contracts",
})
_REVIEW_BACKENDS = frozenset({"nvidia-nim", "codex-cli"})
_REVIEW_MODELS = frozenset({"nano", "super", "ultra"})
_MAX_TIMEOUT_MS = 300_000


class ChangeExecutionInvocationError(RuntimeError):
    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"{code}: {reason}")


class ChangeExecutionService:
    def __init__(self, invoker: Invoker) -> None:
        self._invoker = invoker
    async def execute(
        self,
        *,
        project: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        task_terms: tuple[str, ...] = (),
        max_verifications: int = 20,
        verification_timeout_ms: int = 120_000,
        review_types: tuple[str, ...] = ("code-quality",),
        review_backend: str | None = None,
        review_model: str | None = None,
    ) -> ChangeExecutionResult:
        project = _required(project, "project")
        reviews = _validate_reviews(review_types, review_backend, review_model)
        timeout_ms = _validate_timeout(verification_timeout_ms)
        selection = await self._invoker(
            "select_change_verification",
            {
                "project": project,
                "source": source,
                "commit_ref": commit_ref,
                "base_ref": base_ref,
                "head_ref": head_ref,
                "task_terms": list(task_terms),
                "max_verifications": max_verifications,
            },
        )
        source_fingerprint, verification_ids = _selection_identity(selection)
        verification_results: list[ChangeExecutionStepResult] = []
        verification_failed_count = 0
        verification_incomplete_count = 0
        for verification_id in verification_ids:
            try:
                payload = await self._invoker(
                    "run_verification",
                    {
                        "project": project,
                        "verification_id": verification_id,
                        "timeout_ms": timeout_ms,
                    },
                )
                step = _verification_step(verification_id, payload)
            except ChangeExecutionInvocationError as exc:
                step = ChangeExecutionStepResult(
                    step_id=verification_id,
                    kind="verification",
                    status="error",
                    error_code=exc.code,
                    reason=exc.reason,
                )
            verification_results.append(step)
            if step.status == "failed":
                verification_failed_count += 1
            elif step.status in {"incomplete", "error"}:
                verification_incomplete_count += 1

        review_results: list[ChangeExecutionStepResult] = []
        review_error_count = 0
        for review_type in reviews:
            arguments: dict[str, Any] = {"path": project, "review_type": review_type}
            if review_backend is not None:
                arguments["backend"] = review_backend
            if review_model is not None:
                arguments["model"] = review_model
            try:
                payload = await self._invoker("review_change_with_agent", arguments)
                step = ChangeExecutionStepResult(
                    step_id=review_type,
                    kind="review",
                    status="completed",
                    payload=payload,
                )
            except ChangeExecutionInvocationError as exc:
                step = ChangeExecutionStepResult(
                    step_id=review_type,
                    kind="review",
                    status="error",
                    error_code=exc.code,
                    reason=exc.reason,
                )
                review_error_count += 1
            review_results.append(step)

        if verification_failed_count:
            status = "failed"
        elif verification_incomplete_count or review_error_count:
            status = "incomplete"
        else:
            status = "passed"
        return ChangeExecutionResult(
            project=project,
            source_fingerprint=source_fingerprint,
            selection=selection,
            verifications=tuple(verification_results),
            reviews=tuple(review_results),
            status=status,
            verification_failed_count=verification_failed_count,
            verification_incomplete_count=verification_incomplete_count,
            review_error_count=review_error_count,
        )
def _selection_identity(selection: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    if selection.get("contract") != "verification-selection-v1":
        raise ChangeExecutionInvocationError(
            "CHANGE_EXECUTION_SELECTION_INVALID",
            "Verification selection returned an unexpected contract.",
        )
    fingerprint = selection.get("source_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(
        character not in "0123456789abcdef" for character in fingerprint
    ):
        raise ChangeExecutionInvocationError(
            "CHANGE_EXECUTION_SELECTION_INVALID",
            "Verification selection returned an invalid source fingerprint.",
        )
    raw_selected = selection.get("selected", ())
    if not isinstance(raw_selected, Sequence) or isinstance(
        raw_selected, (str, bytes, bytearray)
    ):
        raise ChangeExecutionInvocationError(
            "CHANGE_EXECUTION_SELECTION_INVALID",
            "Verification selection returned an invalid selected list.",
        )
    identifiers: list[str] = []
    for item in raw_selected:
        if not isinstance(item, Mapping):
            raise ChangeExecutionInvocationError(
                "CHANGE_EXECUTION_SELECTION_INVALID",
                "Verification selection item is not an object.",
            )
        identifier = item.get("verification_id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ChangeExecutionInvocationError(
                "CHANGE_EXECUTION_SELECTION_INVALID",
                "Verification selection item has no verification_id.",
            )
        identifiers.append(identifier.strip())
    return fingerprint, tuple(identifiers)
def _verification_step(
    verification_id: str,
    payload: Mapping[str, Any],
) -> ChangeExecutionStepResult:
    if payload.get("contract") != "verification-result-v1":
        raise ChangeExecutionInvocationError(
            "CHANGE_EXECUTION_VERIFICATION_RESULT_INVALID",
            f"Verification {verification_id!r} returned an unexpected contract.",
        )
    status = payload.get("status")
    if status not in {"passed", "failed", "incomplete"}:
        raise ChangeExecutionInvocationError(
            "CHANGE_EXECUTION_VERIFICATION_RESULT_INVALID",
            f"Verification {verification_id!r} returned an invalid status.",
        )
    return ChangeExecutionStepResult(
        step_id=verification_id,
        kind="verification",
        status=str(status),
        payload=payload,
    )


def _validate_reviews(
    review_types: tuple[str, ...],
    review_backend: str | None,
    review_model: str | None,
) -> tuple[str, ...]:
    if not review_types or len(review_types) > len(_REVIEW_TYPES):
        raise ValueError("review_types must contain between one and seven review_type values")
    if len(set(review_types)) != len(review_types):
        raise ValueError("review_types must not contain duplicate review_type values")
    for review_type in review_types:
        if review_type not in _REVIEW_TYPES:
            raise ValueError(f"unsupported review_type {review_type!r}")
    if review_backend is not None and review_backend not in _REVIEW_BACKENDS:
        raise ValueError(f"unsupported review backend {review_backend!r}")
    if review_model is not None and review_model not in _REVIEW_MODELS:
        raise ValueError(f"unsupported review model {review_model!r}")
    if review_backend == "codex-cli" and review_model is not None:
        raise ValueError("review_model is invalid with review_backend='codex-cli'")
    return review_types


def _validate_timeout(timeout_ms: int) -> int:
    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
        raise ValueError("verification_timeout_ms must be a positive integer")
    if timeout_ms < 1 or timeout_ms > _MAX_TIMEOUT_MS:
        raise ValueError(
            f"verification_timeout_ms must be between 1 and {_MAX_TIMEOUT_MS}"
        )
    return timeout_ms


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


__all__ = [
    "ChangeExecutionInvocationError",
    "ChangeExecutionService",
    "Invoker",
]
