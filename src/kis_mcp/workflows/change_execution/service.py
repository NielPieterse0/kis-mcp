from __future__ import annotations

import asyncio
import hashlib
import json
import math
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
_REVIEW_MODEL_IDS = {
    "nano": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "super": "nvidia/nemotron-3-super-120b-a12b",
    "ultra": "nvidia/nemotron-3-ultra-550b-a55b",
}
_MAX_TIMEOUT_MS = 300_000
_MAX_REVIEWERS = 4
_MAX_REVIEW_ROUNDS = 2
_MAX_REVIEW_INVOCATIONS = 28
_MAX_FINDINGS_PER_REVIEW = 20
_MAX_ENSEMBLE_FINDINGS = 200
_MAX_REVIEW_PAYLOAD_CHARS = 64_000
_REVIEW_FINDING_KEYS = frozenset(
    {"severity", "path", "line", "claim", "evidence", "recommendation", "confidence"}
)
_REVIEW_RESULT_REQUIRED_KEYS = frozenset(
    {"status", "backend", "review_type", "source_fingerprint", "evidence_complete", "summary", "findings", "unknowns", "diagnostics"}
)
_REVIEW_RESULT_ALLOWED_KEYS = _REVIEW_RESULT_REQUIRED_KEYS | frozenset(
    {
        "schema_version", "agent_id", "source", "changed_files", "included_files",
        "omitted_files", "ignored_files", "evidence_projector", "evidence_chars",
        "commit_ref", "base_ref", "head_ref", "model_profile", "model", "attempts", "cost",
        "ensemble_provenance",
    }
)


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
        reviewers: tuple[Mapping[str, Any], ...] | None = None,
        review_rounds: int = 1,
        review_adjudication: bool = False,
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
        reviewer_profiles = _validate_reviewer_profiles(
            reviewers,
            review_backend=review_backend,
            review_model=review_model,
            review_rounds=review_rounds,
            review_type_count=len(reviews),
        )
        if not isinstance(review_adjudication, bool):
            raise TypeError("review_adjudication must be a boolean")
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
                payload = await self._invoker(
                    "run_verification",
                    {
                        "project": project,
                        "verification_id": verification_id,
                        "timeout_ms": verification_timeout_ms,
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

        review_results, review_error_count, review_ensemble = await _execute_reviews(
            invoker=self._invoker,
            reviews=reviews,
            reviewer_profiles=reviewer_profiles,
            project=project,
            source=source,
            commit_ref=commit_ref,
            base_ref=base_ref,
            head_ref=head_ref,
            source_fingerprint=source_fingerprint,
            review_timeout_ms=review_timeout_ms,
            review_backend=review_backend,
            review_model=review_model,
            review_rounds=review_rounds,
            review_adjudication=review_adjudication,
        )

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
            review_ensemble=review_ensemble,
        )


def _validate_reviewer_profiles(
    reviewers: tuple[Mapping[str, Any], ...] | None,
    *,
    review_backend: str | None,
    review_model: str | None,
    review_rounds: int,
    review_type_count: int,
) -> tuple[dict[str, str | None], ...] | None:
    if isinstance(review_rounds, bool) or not isinstance(review_rounds, int):
        raise TypeError("review_rounds must be an integer")
    if reviewers is None:
        if review_rounds != 1:
            raise ValueError("review_rounds requires explicit reviewers")
        return None
    if review_backend is not None or review_model is not None:
        raise ValueError("legacy review_backend/review_model cannot be combined with reviewers")
    if not reviewers or len(reviewers) > _MAX_REVIEWERS:
        raise ValueError("reviewers must contain between one and at most four profiles")
    if review_rounds < 1 or review_rounds > _MAX_REVIEW_ROUNDS:
        raise ValueError(f"review_rounds must be between 1 and {_MAX_REVIEW_ROUNDS}")
    normalized: list[dict[str, str | None]] = []
    reviewer_ids: set[str] = set()
    for raw in reviewers:
        if not isinstance(raw, Mapping):
            raise TypeError("each reviewer profile must be an object")
        profile_keys = set(raw)
        if not {"reviewer_id", "backend"}.issubset(profile_keys) or not profile_keys.issubset(
            {"reviewer_id", "backend", "model"}
        ):
            raise ValueError("reviewer profile keys must be reviewer_id, backend, and optional model")
        raw_reviewer_id = raw.get("reviewer_id")
        if not isinstance(raw_reviewer_id, str):
            raise TypeError("reviewer_id must be a string")
        reviewer_id = _required(raw_reviewer_id, "reviewer_id")
        if not all(character.isalnum() or character in "-_" for character in reviewer_id):
            raise ValueError("reviewer_id may contain only letters, digits, '-' and '_'")
        if reviewer_id in reviewer_ids:
            raise ValueError("reviewer_id values must be unique")
        reviewer_ids.add(reviewer_id)
        backend = raw.get("backend")
        model = raw.get("model")
        if not isinstance(backend, str) or backend not in _REVIEW_BACKENDS:
            raise ValueError(f"unsupported review backend {backend!r}")
        if model is not None and (not isinstance(model, str) or model not in _REVIEW_MODELS):
            raise ValueError(f"unsupported review model {model!r}")
        if backend == "codex-cli" and model is not None:
            raise ValueError("review model is invalid with codex-cli reviewer")
        normalized.append({"reviewer_id": reviewer_id, "backend": backend, "model": model})
    invocation_count = len(normalized) * review_rounds * review_type_count
    if invocation_count > _MAX_REVIEW_INVOCATIONS:
        raise ValueError(f"review ensemble exceeds {_MAX_REVIEW_INVOCATIONS} review invocations")
    return tuple(normalized)


async def _execute_reviews(
    *,
    invoker: Invoker,
    reviews: tuple[str, ...],
    reviewer_profiles: tuple[dict[str, str | None], ...] | None,
    project: str,
    source: str,
    commit_ref: str | None,
    base_ref: str | None,
    head_ref: str | None,
    source_fingerprint: str,
    review_timeout_ms: int,
    review_backend: str | None,
    review_model: str | None,
    review_rounds: int,
    review_adjudication: bool,
) -> tuple[list[ChangeExecutionStepResult], int, dict[str, Any] | None]:
    started = time.monotonic()
    deadline = started + (review_timeout_ms / 1000)
    if reviewer_profiles is None:
        jobs = [(review_type, None, 1) for review_type in reviews]
    else:
        jobs = [
            (review_type, profile, round_number)
            for round_number in range(1, review_rounds + 1)
            for review_type in reviews
            for profile in reviewer_profiles
        ]
    results: list[ChangeExecutionStepResult] = []
    error_count = 0
    finding_count = 0
    invocation_count = 0
    for index, (review_type, profile, round_number) in enumerate(jobs):
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            for pending_type, pending_profile, pending_round in jobs[index:]:
                step_id = _review_step_id(pending_type, pending_profile, pending_round)
                results.append(_review_deadline_step(pending_type, step_id=step_id))
            error_count += len(jobs[index:])
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
        if profile is None:
            if review_backend is not None:
                arguments["backend"] = review_backend
            if review_model is not None:
                arguments["model"] = review_model
        else:
            arguments["backend"] = profile["backend"]
            if profile["model"] is not None:
                arguments["model"] = profile["model"]
            arguments["instructions"] = (
                f"reviewer_id={profile['reviewer_id']};round={round_number};"
                "independent=true;advisory_only=true;retain_dissent=true"
            )
        step_id = _review_step_id(review_type, profile, round_number)
        try:
            invocation_count += 1
            payload = await asyncio.wait_for(
                invoker("review_change_with_agent", arguments),
                timeout=remaining_seconds,
            )
            if not isinstance(payload, Mapping):
                step = ChangeExecutionStepResult(
                    step_id=step_id,
                    kind="review",
                    status="error",
                    error_code="AGENT_REVIEW_ENSEMBLE_RESULT_INVALID",
                    reason="Reviewer result must be an object.",
                )
                error_count += 1
                results.append(step)
                continue
            normalized_payload = dict(payload)
            if profile is not None:
                if "ensemble_provenance" in normalized_payload:
                    step = ChangeExecutionStepResult(
                        step_id=step_id,
                        kind="review",
                        status="error",
                        error_code="AGENT_REVIEW_ENSEMBLE_RESULT_INVALID",
                        reason="Reviewer result must not supply ensemble provenance.",
                    )
                    error_count += 1
                    results.append(step)
                    continue
                normalized_payload["ensemble_provenance"] = {
                    "reviewer_id": profile["reviewer_id"],
                    "backend": profile["backend"],
                    "requested_model_profile": profile["model"],
                    "round": round_number,
                    "review_type": review_type,
                    "source": source,
                    "commit_ref": commit_ref,
                    "base_ref": base_ref,
                    "head_ref": head_ref,
                    "source_fingerprint": source_fingerprint,
                }
                retention_error = _review_payload_retention_error(normalized_payload)
                if retention_error is not None:
                    step = ChangeExecutionStepResult(
                        step_id=step_id,
                        kind="review",
                        status="error",
                        error_code="AGENT_REVIEW_ENSEMBLE_RESULT_INVALID",
                        reason=retention_error,
                    )
                    error_count += 1
                    results.append(step)
                    continue
            step = _review_step(
                review_type,
                normalized_payload,
                source_fingerprint,
                step_id=step_id,
            )
            if profile is not None and step.status == "completed":
                payload_error = _ensemble_payload_error(
                    normalized_payload,
                    profile=profile,
                    review_type=review_type,
                    source=source,
                    commit_ref=commit_ref,
                    base_ref=base_ref,
                    head_ref=head_ref,
                )
                if payload_error is not None:
                    step = ChangeExecutionStepResult(
                        step_id=step_id,
                        kind="review",
                        status="error",
                        error_code="AGENT_REVIEW_ENSEMBLE_RESULT_INVALID",
                        reason=payload_error,
                    )
                else:
                    current_findings = len(normalized_payload["findings"])
                    if finding_count + current_findings > _MAX_ENSEMBLE_FINDINGS:
                        step = ChangeExecutionStepResult(
                            step_id=step_id,
                            kind="review",
                            status="error",
                            error_code="AGENT_REVIEW_ENSEMBLE_FINDING_BUDGET_EXCEEDED",
                            reason="The aggregate reviewer finding budget was exhausted.",
                        )
                    else:
                        finding_count += current_findings
            if profile is not None and step.status != "completed" and step.payload is not None:
                step = ChangeExecutionStepResult(
                    step_id=step.step_id,
                    kind=step.kind,
                    status=step.status,
                    error_code=step.error_code,
                    reason=step.reason,
                )
            if step.status != "completed":
                error_count += 1
        except TimeoutError:
            results.append(_review_deadline_step(review_type, step_id=step_id))
            for pending_type, pending_profile, pending_round in jobs[index + 1 :]:
                pending_id = _review_step_id(pending_type, pending_profile, pending_round)
                results.append(_review_deadline_step(pending_type, step_id=pending_id))
            error_count += len(jobs) - index
            break
        except ChangeExecutionInvocationError as exc:
            step = ChangeExecutionStepResult(
                step_id=step_id,
                kind="review",
                status="error",
                error_code=exc.code,
                reason=exc.reason,
            )
            error_count += 1
        results.append(step)
    ensemble = None
    if reviewer_profiles is not None:
        ensemble = _aggregate_review_ensemble(
            results,
            reviewer_count=len(reviewer_profiles),
            round_count=review_rounds,
            invocation_count=invocation_count,
            adjudication_requested=review_adjudication,
            elapsed_ms=max(0, int((time.monotonic() - started) * 1000)),
        )
    return results, error_count, ensemble


def _review_step_id(
    review_type: str,
    profile: Mapping[str, str | None] | None,
    round_number: int,
) -> str:
    if profile is None:
        return review_type
    return f"{review_type}:{profile['reviewer_id']}:r{round_number}"


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


def _review_payload_retention_error(payload: Mapping[str, Any]) -> str | None:
    try:
        payload_chars = len(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        )
    except (TypeError, ValueError):
        return "Reviewer result must be JSON serializable."
    if payload_chars > _MAX_REVIEW_PAYLOAD_CHARS:
        return "Reviewer result exceeds the bounded payload size."
    return None


def _ensemble_payload_error(
    payload: Mapping[str, Any],
    *,
    profile: Mapping[str, str | None],
    review_type: str,
    source: str,
    commit_ref: str | None,
    base_ref: str | None,
    head_ref: str | None,
) -> str | None:
    if payload.get("review_type") != review_type:
        return "Reviewer result review_type does not match the requested review type."
    if payload.get("backend") != profile["backend"]:
        return "Reviewer result backend does not match the requested reviewer profile."
    if "source" in payload and payload.get("source") != source:
        return "Reviewer result source does not match the requested source."
    for field, expected in (
        ("commit_ref", commit_ref),
        ("base_ref", base_ref),
        ("head_ref", head_ref),
    ):
        if field in payload and payload.get(field) != expected:
            return f"Reviewer result {field} does not match the requested source binding."
    keys = set(payload)
    if not _REVIEW_RESULT_REQUIRED_KEYS.issubset(keys) or not keys.issubset(
        _REVIEW_RESULT_ALLOWED_KEYS
    ):
        return "Reviewer result keys do not match the bounded result contract."
    if profile["backend"] == "codex-cli":
        if "model_profile" in payload or "model" in payload:
            return "Codex reviewer results must not claim NVIDIA model provenance."
    else:
        resolved_profile = payload.get("model_profile")
        resolved_model = payload.get("model")
        if not isinstance(resolved_profile, str) or resolved_profile not in _REVIEW_MODELS:
            return "NVIDIA reviewer result must contain a supported resolved model profile."
        if resolved_model != _REVIEW_MODEL_IDS[resolved_profile]:
            return "Reviewer result model does not match its resolved model profile."
        if profile["model"] is not None and resolved_profile != profile["model"]:
            return "Reviewer result model profile does not match the requested reviewer profile."
    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return "Reviewer summary must be non-empty text."
    unknowns = payload.get("unknowns")
    if not isinstance(unknowns, list) or len(unknowns) > _MAX_FINDINGS_PER_REVIEW:
        return "Reviewer unknowns must be a bounded list."
    if any(not isinstance(item, str) or not item.strip() for item in unknowns):
        return "Reviewer unknowns must contain non-empty text values."
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list) or len(diagnostics) > _MAX_FINDINGS_PER_REVIEW:
        return "Reviewer diagnostics must be a bounded list."
    if any(not isinstance(item, str) or not item.strip() for item in diagnostics):
        return "Reviewer diagnostics must contain non-empty text values."
    if "cost" in payload:
        raw_cost = payload["cost"]
        if (
            isinstance(raw_cost, bool)
            or not isinstance(raw_cost, (int, float))
            or raw_cost < 0
            or not math.isfinite(float(raw_cost))
        ):
            return "Reviewer cost must be a finite non-negative number."
    try:
        payload_chars = len(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        )
    except (TypeError, ValueError):
        return "Reviewer result must be JSON serializable."
    if payload_chars > _MAX_REVIEW_PAYLOAD_CHARS:
        return "Reviewer result exceeds the bounded payload size."
    findings = payload.get("findings")
    if not isinstance(findings, list):
        return "Reviewer findings must be a bounded list."
    if len(findings) > _MAX_FINDINGS_PER_REVIEW:
        return f"Reviewer findings must contain at most {_MAX_FINDINGS_PER_REVIEW} items."
    for finding in findings:
        error = _review_finding_error(finding)
        if error is not None:
            return error
    return None


def _review_finding_error(value: Any) -> str | None:
    if not isinstance(value, Mapping) or set(value) != _REVIEW_FINDING_KEYS:
        return "Each reviewer finding must match the strict finding contract."
    for key in ("severity", "path", "claim", "evidence", "recommendation", "confidence"):
        item = value.get(key)
        if not isinstance(item, str) or not item.strip():
            return f"Reviewer finding field {key!r} must be non-empty text."
    line = value.get("line")
    if line is not None and (isinstance(line, bool) or not isinstance(line, int) or line < 1):
        return "Reviewer finding field 'line' must be null or a positive integer."
    return None


def _aggregate_review_ensemble(
    results: Sequence[ChangeExecutionStepResult],
    *,
    reviewer_count: int,
    round_count: int,
    invocation_count: int,
    adjudication_requested: bool,
    elapsed_ms: int,
) -> dict[str, Any]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    rejected_findings = 0
    completed_count = 0
    observed_cost = 0.0
    cost_observation_count = 0
    rejected_cost_observation_count = 0
    for step in results:
        if step.status != "completed" or step.payload is None:
            continue
        completed_count += 1
        raw_cost = step.payload.get("cost")
        if (
            isinstance(raw_cost, (int, float))
            and not isinstance(raw_cost, bool)
            and raw_cost >= 0
            and math.isfinite(float(raw_cost))
        ):
            candidate_cost = observed_cost + float(raw_cost)
            if math.isfinite(candidate_cost):
                observed_cost = candidate_cost
                cost_observation_count += 1
            else:
                rejected_cost_observation_count += 1
        provenance = step.payload.get("ensemble_provenance")
        reviewer_id = None
        if isinstance(provenance, Mapping):
            reviewer_id = provenance.get("reviewer_id")
        findings = step.payload.get("findings", ())
        if not isinstance(findings, Sequence) or isinstance(findings, (str, bytes, bytearray)):
            rejected_findings += 1
            continue
        for finding in findings:
            if not isinstance(finding, Mapping):
                rejected_findings += 1
                continue
            path = str(finding.get("path") or "").strip()
            claim = str(finding.get("claim") or "").strip()
            if not claim:
                rejected_findings += 1
                continue
            key = (path.casefold(), claim.casefold())
            group = groups.setdefault(key, {
                "path": path or None,
                "claim": claim,
                "reviewer_ids": set(),
                "review_types": set(),
                "severities": set(),
                "occurrence_count": 0,
            })
            group["occurrence_count"] += 1
            if isinstance(reviewer_id, str) and reviewer_id:
                group["reviewer_ids"].add(reviewer_id)
            review_type = step.payload.get("review_type")
            if isinstance(review_type, str) and review_type:
                group["review_types"].add(review_type)
            severity = finding.get("severity")
            if isinstance(severity, str) and severity:
                group["severities"].add(severity)

    finding_groups: list[dict[str, Any]] = []
    duplicate_count = 0
    disagreement_count = 0
    for key in sorted(groups):
        group = groups[key]
        occurrence_count = int(group["occurrence_count"])
        duplicate_count += max(0, occurrence_count - 1)
        severities = sorted(group["severities"])
        disagreement = len(severities) > 1
        disagreement_count += int(disagreement)
        identity = f"{key[0]}\n{key[1]}".encode()
        disposition = "single_source"
        if occurrence_count > 1:
            disposition = "corroborated"
        if disagreement:
            disposition = "unresolved_dissent"
        finding_groups.append({
            "finding_key": hashlib.sha256(identity).hexdigest(),
            "path": group["path"],
            "claim": group["claim"],
            "occurrence_count": occurrence_count,
            "reviewer_ids": sorted(group["reviewer_ids"]),
            "review_types": sorted(group["review_types"]),
            "severities": severities,
            "disagreement": disagreement,
            "disposition": disposition,
        })
    return {
        "schema_version": 1,
        "authority": "advisory_evidence_only",
        "reviewer_count": reviewer_count,
        "round_count": round_count,
        "planned_invocation_count": len(results),
        "invocation_count": invocation_count,
        "completed_invocation_count": completed_count,
        "unique_finding_count": len(finding_groups),
        "duplicate_finding_count": duplicate_count,
        "rejected_finding_count": rejected_findings,
        "disagreement_count": disagreement_count,
        "adjudication_requested": adjudication_requested,
        "adjudication_invoked": False,
        "adjudication_completed": False,
        "elapsed_ms": elapsed_ms,
        "provider_cost": {
            "observed": cost_observation_count > 0,
            "observation_count": cost_observation_count,
            "rejected_observation_count": rejected_cost_observation_count,
            "total": observed_cost if cost_observation_count else None,
        },
        "finding_groups": finding_groups,
        "gate_authority": {"verification": False, "merge_readiness": False, "mutation": False},
    }


def _review_deadline_step(
    review_type: str,
    *,
    step_id: str | None = None,
) -> ChangeExecutionStepResult:
    return ChangeExecutionStepResult(
        step_id=step_id or review_type,
        kind="review",
        status="error",
        error_code="AGENT_REVIEW_PHASE_DEADLINE_EXCEEDED",
        reason="The aggregate specialist-review deadline was exhausted.",
    )


def _review_step(
    review_type: str,
    payload: Mapping[str, Any],
    source_fingerprint: str,
    *,
    step_id: str | None = None,
) -> ChangeExecutionStepResult:
    result_step_id = step_id or review_type
    agent_status = payload.get("status")
    if agent_status == "completed":
        if payload.get("evidence_complete") is not True:
            return ChangeExecutionStepResult(
                step_id=result_step_id,
                kind="review",
                status="error",
                payload=payload,
                error_code="AGENT_REVIEW_EVIDENCE_INCOMPLETE",
                reason="Reviewer did not prove complete source evidence.",
            )
        if payload.get("source_fingerprint") != source_fingerprint:
            return ChangeExecutionStepResult(
                step_id=result_step_id,
                kind="review",
                status="error",
                payload=payload,
                error_code="AGENT_REVIEW_SOURCE_MISMATCH",
                reason="Reviewer evidence fingerprint does not match verification selection.",
            )
        return ChangeExecutionStepResult(
            step_id=result_step_id,
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
        step_id=result_step_id,
        kind="review",
        status="error",
        payload=payload,
        error_code=error_code,
        reason=reason,
    )


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
        raise TypeError(f"{label} must be a positive integer")
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
