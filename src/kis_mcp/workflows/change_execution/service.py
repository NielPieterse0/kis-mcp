from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from ..change_controls import select_change_controls
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
        complexity: str = "medium",
        risk_triggers: tuple[str, ...] = (),
        max_verifications: int | None = None,
        verification_timeout_ms: int = 120_000,
        review_timeout_ms: int = 120_000,
        review_types: tuple[str, ...] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
    ) -> ChangeExecutionResult:
        project = _required(project, "project")
        controls = select_change_controls(
            complexity=complexity,
            risk_triggers=risk_triggers,
            review_types=review_types or (),
            max_verifications=max_verifications,
        )
        verification_limit = controls.max_verifications
        reviews = _validate_reviews(
            controls.review_types,
            review_backend,
            review_model,
        )
        verification_timeout_ms = _validate_timeout(
            verification_timeout_ms,
            "verification_timeout_ms",
        )
        review_timeout_ms = _validate_timeout(review_timeout_ms, "review_timeout_ms")
        selection = await self._invoker(
            "select_change_verification",
            {
                "project": project,
                "source": source,
                "commit_ref": commit_ref,
                "base_ref": base_ref,
                "head_ref": head_ref,
                "task_terms": list(dict.fromkeys((*task_terms, *controls.risk_triggers))),
                "max_verifications": verification_limit,
            },
        )
        source_fingerprint, verification_ids = _selection_identity(selection)
        verification_results: list[ChangeExecutionStepResult] = []
        verification_failed_count = 0
        verification_incomplete_count = 0
        for verification_id in verification_ids:
            try:
                verification_args: dict[str, Any] = {
                    "project": project,
                    "verification_id": verification_id,
                    "timeout_ms": verification_timeout_ms,
                }
                if source == "commit" and commit_ref is not None:
                    verification_args["exact_revision"] = commit_ref
                payload = await self._invoker("run_verification", verification_args)
                step = _verification_step(
                    verification_id,
                    payload,
                    requested_revision=(commit_ref if source == "commit" else None),
                )
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
        review_deadline = time.monotonic() + (review_timeout_ms / 1000)
        for review_index, review_type in enumerate(reviews):
            remaining_seconds = review_deadline - time.monotonic()
            if remaining_seconds <= 0:
                remaining_reviews = reviews[review_index:]
                review_results.extend(_review_deadline_step(item) for item in remaining_reviews)
                review_error_count += len(remaining_reviews)
                break
            arguments: dict[str, Any] = {
                "path": project,
                "review_type": review_type,
                "source": source,
                "commit_ref": commit_ref,
                "base_ref": base_ref,
                "head_ref": head_ref,
                "deadline_seconds": remaining_seconds,
            }
            if review_backend is not None:
                arguments["backend"] = review_backend
            if review_model is not None:
                arguments["model"] = review_model
            try:
                payload = await asyncio.wait_for(
                    self._invoker("review_change_with_agent", arguments),
                    timeout=remaining_seconds,
                )
                step = _review_step(review_type, payload, source_fingerprint)
                if step.status != "completed":
                    review_error_count += 1
            except TimeoutError:
                remaining_reviews = reviews[review_index:]
                review_results.extend(_review_deadline_step(item) for item in remaining_reviews)
                review_error_count += len(remaining_reviews)
                break
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
            complexity=controls.complexity,
            risk_triggers=controls.risk_triggers,
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


def _review_deadline_step(review_type: str) -> ChangeExecutionStepResult:
    return ChangeExecutionStepResult(
        step_id=review_type,
        kind="review",
        status="error",
        error_code="AGENT_REVIEW_PHASE_DEADLINE_EXCEEDED",
        reason="The aggregate specialist-review deadline was exhausted.",
    )


def _review_step(
    review_type: str,
    payload: Mapping[str, Any],
    source_fingerprint: str,
) -> ChangeExecutionStepResult:
    agent_status = payload.get("status")
    if agent_status == "completed":
        if payload.get("evidence_complete") is not True:
            return ChangeExecutionStepResult(
                step_id=review_type,
                kind="review",
                status="error",
                payload=payload,
                error_code="AGENT_REVIEW_EVIDENCE_INCOMPLETE",
                reason="Reviewer did not prove complete source evidence.",
            )
        if payload.get("source_fingerprint") != source_fingerprint:
            return ChangeExecutionStepResult(
                step_id=review_type,
                kind="review",
                status="error",
                payload=payload,
                error_code="AGENT_REVIEW_SOURCE_MISMATCH",
                reason="Reviewer evidence fingerprint does not match verification selection.",
            )
        return ChangeExecutionStepResult(
            step_id=review_type,
            kind="review",
            status="completed",
            payload=payload,
        )
    diagnostics = payload.get("diagnostics")
    error_code = "AGENT_REVIEW_RESULT_INVALID"
    if isinstance(diagnostics, Sequence) and not isinstance(
        diagnostics, (str, bytes, bytearray)
    ):
        for diagnostic in diagnostics:
            if isinstance(diagnostic, str) and diagnostic.strip():
                error_code = diagnostic.strip()
                break
    summary = payload.get("summary")
    reason = (
        summary.strip()
        if isinstance(summary, str) and summary.strip()
        else f"Reviewer returned non-success status {agent_status!r}."
    )
    return ChangeExecutionStepResult(
        step_id=review_type,
        kind="review",
        status="error",
        payload=payload,
        error_code=error_code,
        reason=reason,
    )


def _verification_step(
    verification_id: str,
    payload: Mapping[str, Any],
    *,
    requested_revision: str | None = None,
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
    if requested_revision is not None:
        source_revision = payload.get("source_revision")
        receipt_sha256 = payload.get("receipt_sha256")
        evidence_reference = payload.get("evidence_reference")
        if payload.get("requested_revision") != requested_revision:
            raise ChangeExecutionInvocationError(
                "CHANGE_EXECUTION_EXACT_VERIFICATION_REQUIRED",
                f"Verification {verification_id!r} did not preserve the requested commit reference.",
            )
        if (
            not isinstance(source_revision, str)
            or len(source_revision) != 40
            or any(character not in "0123456789abcdef" for character in source_revision)
            or not isinstance(receipt_sha256, str)
            or len(receipt_sha256) != 64
            or any(character not in "0123456789abcdef" for character in receipt_sha256)
            or not isinstance(evidence_reference, str)
            or not evidence_reference.startswith("kis-local-verification:")
        ):
            raise ChangeExecutionInvocationError(
                "CHANGE_EXECUTION_EXACT_VERIFICATION_REQUIRED",
                f"Verification {verification_id!r} did not return canonical local receipt evidence.",
            )
        if (
            len(requested_revision) == 40
            and all(character in "0123456789abcdef" for character in requested_revision.lower())
            and source_revision != requested_revision.lower()
        ):
            raise ChangeExecutionInvocationError(
                "CHANGE_EXECUTION_EXACT_VERIFICATION_REQUIRED",
                f"Verification {verification_id!r} executed a different commit.",
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
    if len(review_types) > len(_REVIEW_TYPES):
        raise ValueError("review_types must contain at most seven review_type values")
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


def _validate_timeout(timeout_ms: int, label: str) -> int:
    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
        raise ValueError(f"{label} must be a positive integer")
    if timeout_ms < 1 or timeout_ms > _MAX_TIMEOUT_MS:
        raise ValueError(f"{label} must be between 1 and {_MAX_TIMEOUT_MS}")
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
