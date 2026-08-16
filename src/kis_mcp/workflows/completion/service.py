from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from .contracts import CompletionReceipt, CompletionResult

Invoker = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
ProjectResolver = Callable[[str], str]
_SHA = re.compile(r"^[0-9a-f]{40}$")
_OPERATION_STATES = frozenset({"not_started", "in_progress", "applied", "failed", "unknown"})
_DEFAULT_COMPLETION_DEADLINE_MS = 120_000
_MAX_COMPLETION_DEADLINE_MS = 300_000
_NESTED_MUTATION_DEADLINE_MS = 30_000
_NESTED_RETURN_RESERVE_MS = 5_000


class _Deadline:
    def __init__(self, timeout_ms: int, clock: Callable[[], float]) -> None:
        self.timeout_ms = timeout_ms
        self._clock = clock
        self._started = clock()
        self._ends = self._started + (timeout_ms / 1000)

    def remaining_seconds(self) -> float:
        remaining = self._ends - self._clock()
        if remaining <= 0:
            raise TimeoutError("completion deadline exhausted")
        return max(0.001, remaining)

    def remaining_ms(self) -> int:
        return max(0, int((self._ends - self._clock()) * 1000))

    def elapsed_ms(self) -> int:
        return max(0, int(round((self._clock() - self._started) * 1000)))


def _operation_id(intent: Mapping[str, object]) -> str:
    canonical = json.dumps(
        dict(intent),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "prp-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_deadline_ms(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("deadline_ms must be a positive integer")
    if value < 1 or value > _MAX_COMPLETION_DEADLINE_MS:
        raise ValueError(
            f"deadline_ms must be between 1 and {_MAX_COMPLETION_DEADLINE_MS}"
        )
    return value


def _nested_deadline_ms(deadline: _Deadline) -> int:
    remaining = deadline.remaining_ms()
    if remaining <= _NESTED_RETURN_RESERVE_MS:
        raise TimeoutError("completion deadline has no nested-operation budget remaining")
    return min(
        _NESTED_MUTATION_DEADLINE_MS,
        remaining - _NESTED_RETURN_RESERVE_MS,
    )


class CompletionInvocationError(RuntimeError):
    def __init__(
        self,
        code: str,
        reason: str,
        *,
        retryable: bool = False,
        stage: str | None = None,
        completed_steps: tuple[str, ...] = (),
        operation_id: str | None = None,
        operation_state: str | None = None,
        elapsed_ms: int = 0,
        stage_timings_ms: Mapping[str, int] | None = None,
    ) -> None:
        self.code = code
        self.reason = reason
        self.retryable = retryable
        self.stage = stage
        self.completed_steps = completed_steps
        self.operation_id = operation_id
        self.operation_state = operation_state
        self.elapsed_ms = elapsed_ms
        self.stage_timings_ms = dict(stage_timings_ms or {})
        super().__init__(f"{code}: {reason}")


class CompletionCoordinator:
    def __init__(
        self,
        invoker: Invoker,
        project_resolver: ProjectResolver,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._invoker = invoker
        self._project_resolver = project_resolver
        self._clock = clock

    async def _invoke_step(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        stage: str,
        completed_steps: tuple[str, ...],
        deadline: _Deadline,
        stage_timings_ms: dict[str, int],
        operation_id: str,
        timeout_state: str,
    ) -> dict[str, Any]:
        started = self._clock()
        try:
            remaining = deadline.remaining_seconds()
            result = await asyncio.wait_for(
                self._invoker(tool_name, arguments),
                timeout=remaining,
            )
        except TimeoutError as exc:
            stage_timings_ms[stage] = max(
                0, int(round((self._clock() - started) * 1000))
            )
            raise CompletionInvocationError(
                "COMPLETION_DEADLINE_EXCEEDED",
                f"aggregate completion deadline expired during {stage}",
                retryable=True,
                stage=stage,
                completed_steps=completed_steps,
                operation_id=operation_id,
                operation_state=timeout_state,
                elapsed_ms=deadline.elapsed_ms(),
                stage_timings_ms=stage_timings_ms,
            ) from exc
        except CompletionInvocationError:
            raise
        except Exception as exc:
            stage_timings_ms[stage] = max(
                0, int(round((self._clock() - started) * 1000))
            )
            raise CompletionInvocationError(
                f"COMPLETION_{stage.upper()}_FAILED",
                f"{type(exc).__name__}: {exc}",
                retryable=_is_retryable_failure(exc),
                stage=stage,
                completed_steps=completed_steps,
                operation_id=operation_id,
                operation_state=timeout_state if _is_retryable_failure(exc) else "failed",
                elapsed_ms=deadline.elapsed_ms(),
                stage_timings_ms=stage_timings_ms,
            ) from exc
        stage_timings_ms[stage] = max(
            0, int(round((self._clock() - started) * 1000))
        )
        return result

    def _error(
        self,
        code: str,
        reason: str,
        *,
        retryable: bool,
        stage: str,
        completed_steps: tuple[str, ...],
        operation_id: str,
        operation_state: str,
        deadline: _Deadline,
        stage_timings_ms: Mapping[str, int],
    ) -> CompletionInvocationError:
        return CompletionInvocationError(
            code,
            reason,
            retryable=retryable,
            stage=stage,
            completed_steps=completed_steps,
            operation_id=operation_id,
            operation_state=operation_state,
            elapsed_ms=deadline.elapsed_ms(),
            stage_timings_ms=stage_timings_ms,
        )

    def _nested_budget(
        self,
        *,
        deadline: _Deadline,
        stage: str,
        completed_steps: tuple[str, ...],
        operation_id: str,
        operation_state: str,
        stage_timings_ms: Mapping[str, int],
    ) -> int:
        try:
            return _nested_deadline_ms(deadline)
        except TimeoutError as exc:
            raise self._error(
                "COMPLETION_DEADLINE_EXCEEDED",
                str(exc),
                retryable=True,
                stage=stage,
                completed_steps=completed_steps,
                operation_id=operation_id,
                operation_state=operation_state,
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
            ) from exc

    async def prepare(
        self,
        *,
        project_id: str,
        commit: str,
        source_base: str,
        branch: str,
        expected_remote_branch: str | None,
        expected_remote_default: str,
        title: str,
        body: str,
        approved: bool,
        task_terms: tuple[str, ...] = (),
        complexity: str = "medium",
        risk_triggers: tuple[str, ...] = (),
        max_verifications: int | None = None,
        verification_timeout_ms: int = 120_000,
        review_types: tuple[str, ...] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
        documentation_impact: str = "not_assessed",
        residual_state: str = "none declared",
        deadline_ms: int = _DEFAULT_COMPLETION_DEADLINE_MS,
        reconcile_only: bool = False,
    ) -> CompletionResult | CompletionReceipt:
        project_key = _required(project_id, "project_id")
        commit_sha = _sha(commit, "commit")
        source_base_sha = _sha(source_base, "source_base")
        branch_name = _required(branch, "branch")
        default_sha = _sha(expected_remote_default, "expected_remote_default")
        branch_base = None if expected_remote_branch is None else _sha(
            expected_remote_branch, "expected_remote_branch"
        )
        title_text = _required(title, "title")
        if len(title_text) > 256:
            raise ValueError("title must contain at most 256 characters")
        if not isinstance(body, str) or len(body) > 10_000:
            raise ValueError("body must be a string of at most 10000 characters")
        documentation_impact = _required(documentation_impact, "documentation_impact")
        if documentation_impact not in {
            "not_assessed",
            "none",
            "planned",
            "in_progress",
            "pre_merge_complete",
            "post_merge_complete",
        }:
            raise ValueError("documentation_impact is unsupported")
        residual_state = _required(residual_state, "residual_state")
        if approved is not True:
            raise ValueError("approved must be true")
        if not isinstance(reconcile_only, bool):
            raise ValueError("reconcile_only must be a boolean")
        deadline_ms = _validate_deadline_ms(deadline_ms)
        operation_id = _operation_id(
            {
                "project_id": project_key,
                "commit": commit_sha,
                "source_base": source_base_sha,
                "branch": branch_name,
                "expected_remote_branch": branch_base,
                "expected_remote_default": default_sha,
                "title": title_text,
                "body": body,
                "task_terms": list(task_terms),
                "complexity": complexity,
                "risk_triggers": list(risk_triggers),
                "max_verifications": max_verifications,
                "review_types": None if review_types is None else list(review_types),
                "review_backend": review_backend,
                "review_model": review_model,
                "documentation_impact": documentation_impact,
                "residual_state": residual_state,
            }
        )
        deadline = _Deadline(deadline_ms, self._clock)
        stage_timings_ms: dict[str, int] = {}
        try:
            project_root = _required(self._project_resolver(project_key), "project root")
        except (KeyError, ValueError) as exc:
            raise CompletionInvocationError(
                "COMPLETION_PROJECT_UNKNOWN",
                f"registered project {project_key!r} could not be resolved",
                operation_id=operation_id,
                operation_state="not_started",
                elapsed_ms=deadline.elapsed_ms(),
            ) from exc

        publication_args: dict[str, Any] = {
            "project_id": project_key,
            "commit": commit_sha,
            "source_base": source_base_sha,
            "branch": branch_name,
            "expected_remote_default": default_sha,
            "expected_remote_branch": branch_base,
            "approved": True,
        }

        if reconcile_only:
            publication_args["deadline_ms"] = self._nested_budget(
                deadline=deadline,
                stage="publication",
                completed_steps=(),
                operation_id=operation_id,
                operation_state="unknown",
                stage_timings_ms=stage_timings_ms,
            )
            publication_args["status_only"] = True
            publication = await self._invoke_step(
                "execute_external_action",
                {
                    "operation": "kis_github_reconcile_registered_commit",
                    "arguments": publication_args,
                },
                stage="publication",
                completed_steps=(),
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
                operation_id=operation_id,
                timeout_state="unknown",
            )
            publication_state = _operation_state(publication)
            if publication_state != "applied":
                return CompletionReceipt(
                    project_id=project_key,
                    source_commit_sha=commit_sha,
                    branch=branch_name,
                    operation_id=operation_id,
                    operation_state=publication_state,
                    stage="publication",
                    elapsed_ms=deadline.elapsed_ms(),
                    stage_timings_ms=stage_timings_ms,
                    publication=publication,
                )
            published_head = _published_head(publication, commit_sha, branch_name)
            if published_head is None:
                return CompletionReceipt(
                    project_id=project_key,
                    source_commit_sha=commit_sha,
                    branch=branch_name,
                    operation_id=operation_id,
                    operation_state="failed",
                    stage="publication",
                    elapsed_ms=deadline.elapsed_ms(),
                    stage_timings_ms=stage_timings_ms,
                    publication=publication,
                )
            execution = await self._execute_verification(
                project_root=project_root,
                commit_sha=commit_sha,
                task_terms=task_terms,
                complexity=complexity,
                risk_triggers=risk_triggers,
                max_verifications=max_verifications,
                verification_timeout_ms=verification_timeout_ms,
                review_types=review_types,
                review_backend=review_backend,
                review_model=review_model,
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
                operation_id=operation_id,
                completed_steps=("publication",),
                timeout_state="unknown",
            )
            if not _execution_passed(execution):
                return CompletionReceipt(
                    project_id=project_key,
                    source_commit_sha=commit_sha,
                    branch=branch_name,
                    operation_id=operation_id,
                    operation_state="unknown",
                    stage="verification",
                    completed_steps=("publication",),
                    elapsed_ms=deadline.elapsed_ms(),
                    stage_timings_ms=stage_timings_ms,
                    execution=execution,
                    publication=publication,
                )
            pull_request_body = _render_pull_request_body(
                outcome=title_text,
                summary=body,
                branch=branch_name,
                task_terms=task_terms,
                complexity=complexity,
                risk_triggers=risk_triggers,
                source_commit=commit_sha,
                published_head=published_head,
                execution=execution,
                documentation_impact=documentation_impact,
                reconciliation_base=str(publication.get("base_relation") or "not_reported"),
                residual_state=residual_state,
            )
            if len(pull_request_body) > 20_000:
                raise ValueError("generated pull request body exceeds 20000 characters")
            pull_request_args = {
                "project_id": project_key,
                "branch": branch_name,
                "expected_head": published_head,
                "expected_remote_default": default_sha,
                "title": title_text,
                "body": pull_request_body,
                "approved": True,
                "status_only": True,
                "deadline_ms": self._nested_budget(
                    deadline=deadline,
                    stage="pull_request",
                    completed_steps=("publication",),
                    operation_id=operation_id,
                    operation_state="in_progress",
                    stage_timings_ms=stage_timings_ms,
                ),
            }
            pull_request = await self._invoke_step(
                "execute_external_action",
                {
                    "operation": "kis_github_create_registered_pull_request",
                    "arguments": pull_request_args,
                },
                stage="pull_request",
                completed_steps=("publication",),
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
                operation_id=operation_id,
                timeout_state="unknown",
            )
            pr_state = _operation_state(pull_request)
            overall_state = "in_progress" if pr_state == "not_started" else pr_state
            completed = (
                ("publication", "pull_request")
                if pr_state == "applied"
                else ("publication",)
            )
            return CompletionReceipt(
                project_id=project_key,
                source_commit_sha=commit_sha,
                branch=branch_name,
                operation_id=operation_id,
                operation_state=overall_state,
                stage="pull_request",
                completed_steps=completed,
                elapsed_ms=deadline.elapsed_ms(),
                stage_timings_ms=stage_timings_ms,
                execution=execution,
                publication=publication,
                pull_request=pull_request,
            )

        execution = await self._execute_verification(
            project_root=project_root,
            commit_sha=commit_sha,
            task_terms=task_terms,
            complexity=complexity,
            risk_triggers=risk_triggers,
            max_verifications=max_verifications,
            verification_timeout_ms=verification_timeout_ms,
            review_types=review_types,
            review_backend=review_backend,
            review_model=review_model,
            deadline=deadline,
            stage_timings_ms=stage_timings_ms,
            operation_id=operation_id,
            completed_steps=(),
            timeout_state="not_started",
        )
        if execution.get("contract") != "change-execution-result-v2":
            raise self._error(
                "COMPLETION_EXECUTION_INVALID",
                "change execution returned an unexpected contract",
                retryable=False,
                stage="verification",
                completed_steps=(),
                operation_id=operation_id,
                operation_state="not_started",
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
            )
        if execution.get("status") != "passed":
            raise self._error(
                "COMPLETION_VERIFICATION_NOT_PASSED",
                "change execution must pass before external mutation",
                retryable=False,
                stage="verification",
                completed_steps=(),
                operation_id=operation_id,
                operation_state="not_started",
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
            )

        publication_args["status_only"] = False
        publication_args["deadline_ms"] = self._nested_budget(
            deadline=deadline,
            stage="publication",
            completed_steps=("verification",),
            operation_id=operation_id,
            operation_state="not_started",
            stage_timings_ms=stage_timings_ms,
        )
        publication = await self._invoke_step(
            "execute_external_action",
            {
                "operation": "kis_github_reconcile_registered_commit",
                "arguments": publication_args,
            },
            stage="publication",
            completed_steps=("verification",),
            deadline=deadline,
            stage_timings_ms=stage_timings_ms,
            operation_id=operation_id,
            timeout_state="unknown",
        )
        publication_state = _operation_state(publication)
        if publication_state != "applied":
            raise self._error(
                "COMPLETION_PUBLICATION_NOT_APPLIED",
                f"registered reconciliation reported {publication_state}",
                retryable=publication_state in {"not_started", "unknown"},
                stage="publication",
                completed_steps=("verification",),
                operation_id=operation_id,
                operation_state=publication_state,
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
            )
        published_head = _published_head(publication, commit_sha, branch_name)
        if published_head is None:
            raise self._error(
                "COMPLETION_PUBLICATION_INVALID",
                "registered reconciliation did not preserve the exact source commit identity and review branch",
                retryable=True,
                stage="publication",
                completed_steps=("verification",),
                operation_id=operation_id,
                operation_state="unknown",
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
            )

        pull_request_body = _render_pull_request_body(
            outcome=title_text,
            summary=body,
            branch=branch_name,
            task_terms=task_terms,
            complexity=complexity,
            risk_triggers=risk_triggers,
            source_commit=commit_sha,
            published_head=published_head,
            execution=execution,
            documentation_impact=documentation_impact,
            reconciliation_base=str(publication.get("base_relation") or "not_reported"),
            residual_state=residual_state,
        )
        if len(pull_request_body) > 20_000:
            raise ValueError("generated pull request body exceeds 20000 characters")

        pull_request = await self._invoke_step(
            "execute_external_action",
            {
                "operation": "kis_github_create_registered_pull_request",
                "arguments": {
                    "project_id": project_key,
                    "branch": branch_name,
                    "expected_head": published_head,
                    "expected_remote_default": default_sha,
                    "title": title_text,
                    "body": pull_request_body,
                    "approved": True,
                    "status_only": False,
                    "deadline_ms": self._nested_budget(
                        deadline=deadline,
                        stage="pull_request",
                        completed_steps=("verification", "publication"),
                        operation_id=operation_id,
                        operation_state="in_progress",
                        stage_timings_ms=stage_timings_ms,
                    ),
                },
            },
            stage="pull_request",
            completed_steps=("verification", "publication"),
            deadline=deadline,
            stage_timings_ms=stage_timings_ms,
            operation_id=operation_id,
            timeout_state="unknown",
        )
        pr_state = _operation_state(pull_request)
        if pr_state != "applied":
            overall_state = "in_progress" if pr_state == "not_started" else pr_state
            raise self._error(
                "COMPLETION_PULL_REQUEST_NOT_APPLIED",
                f"registered pull request reported {pr_state}",
                retryable=pr_state in {"not_started", "unknown"},
                stage="pull_request",
                completed_steps=("verification", "publication"),
                operation_id=operation_id,
                operation_state=overall_state,
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
            )
        if (
            pull_request.get("state") != "open"
            or pull_request.get("head_sha") != published_head
            or pull_request.get("branch") != branch_name
        ):
            raise self._error(
                "COMPLETION_PULL_REQUEST_INVALID",
                "registered pull request did not return the exact reconciled head and branch",
                retryable=True,
                stage="pull_request",
                completed_steps=("verification", "publication"),
                operation_id=operation_id,
                operation_state="unknown",
                deadline=deadline,
                stage_timings_ms=stage_timings_ms,
            )
        return CompletionResult(
            project_id=project_key,
            source_commit_sha=commit_sha,
            published_head_sha=published_head,
            branch=branch_name,
            execution=execution,
            publication=publication,
            pull_request=pull_request,
            operation_id=operation_id,
            operation_state="applied",
            elapsed_ms=deadline.elapsed_ms(),
            stage_timings_ms=stage_timings_ms,
        )

    async def _execute_verification(
        self,
        *,
        project_root: str,
        commit_sha: str,
        task_terms: tuple[str, ...],
        complexity: str,
        risk_triggers: tuple[str, ...],
        max_verifications: int | None,
        verification_timeout_ms: int,
        review_types: tuple[str, ...] | None,
        review_backend: str | None,
        review_model: str | None,
        deadline: _Deadline,
        stage_timings_ms: dict[str, int],
        operation_id: str,
        completed_steps: tuple[str, ...],
        timeout_state: str,
    ) -> dict[str, Any]:
        remaining_ms = max(1, deadline.remaining_ms())
        execution_args: dict[str, Any] = {
            "project": project_root,
            "source": "commit",
            "commit_ref": commit_sha,
            "task_terms": list(task_terms),
            "complexity": complexity,
            "risk_triggers": list(risk_triggers),
            "verification_timeout_ms": min(verification_timeout_ms, remaining_ms),
            "review_timeout_ms": min(120_000, remaining_ms),
        }
        if max_verifications is not None:
            execution_args["max_verifications"] = max_verifications
        if review_types is not None:
            execution_args["review_types"] = list(review_types)
        if review_backend is not None:
            execution_args["review_backend"] = review_backend
        if review_model is not None:
            execution_args["review_model"] = review_model
        return await self._invoke_step(
            "execute_change_workflow",
            execution_args,
            stage="verification",
            completed_steps=completed_steps,
            deadline=deadline,
            stage_timings_ms=stage_timings_ms,
            operation_id=operation_id,
            timeout_state=timeout_state,
        )


_NON_RETRYABLE_EXTERNAL_CODES = frozenset({
    "APPROVAL_REQUIRED",
    "DEFAULT_BRANCH_PUBLICATION_BLOCKED",
    "DEFAULT_BRANCH_PULL_REQUEST_BLOCKED",
    "LOCAL_BASE_NOT_ANCESTOR",
    "OPEN_PULL_REQUEST_EXISTS",
    "REMOTE_BRANCH_CHANGED",
    "REMOTE_BRANCH_CONFLICT",
    "REMOTE_BRANCH_MISMATCH",
    "REMOTE_DEFAULT_CHANGED",
    "REMOTE_DEFAULT_MISMATCH",
    "REMOTE_HEAD_MISMATCH",
})
_RETRYABLE_EXTERNAL_CODES = frozenset({
    "PUBLICATION_NOT_VERIFIED",
    "PULL_REQUEST_CREATE_NOT_VERIFIED",
    "PULL_REQUEST_CREATE_UNVERIFIABLE",
    "PULL_REQUEST_STATE_UNVERIFIABLE",
    "REGISTERED_GITHUB_COMMAND_TIMEOUT",
    "REGISTERED_GITHUB_DEADLINE_EXCEEDED",
})
_ERROR_CODE_PREFIX = re.compile(r"^\s*([A-Z][A-Z0-9_]+):")


def _operation_state(payload: Mapping[str, Any]) -> str:
    state = payload.get("operation_state")
    if state in _OPERATION_STATES:
        return str(state)
    legacy = payload.get("state")
    if legacy in {"published", "open"}:
        return "applied"
    return "unknown"


def _published_head(
    publication: Mapping[str, Any],
    commit_sha: str,
    branch_name: str,
) -> str | None:
    published_head = str(publication.get("commit_sha", "")).lower()
    if (
        publication.get("state") != "published"
        or publication.get("source_commit_sha") != commit_sha
        or _SHA.fullmatch(published_head) is None
        or publication.get("branch") != branch_name
    ):
        return None
    return published_head


def _execution_passed(execution: Mapping[str, Any]) -> bool:
    return (
        execution.get("contract") == "change-execution-result-v2"
        and execution.get("status") == "passed"
    )


def _failure_code(exc: Exception) -> str | None:
    value = getattr(exc, "code", None)
    if isinstance(value, str) and value:
        return value
    text = str(exc).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        code = payload.get("code")
        if isinstance(code, str) and code:
            return code
    match = _ERROR_CODE_PREFIX.match(text)
    return None if match is None else match.group(1)


def _is_retryable_failure(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    code = _failure_code(exc)
    if code in _RETRYABLE_EXTERNAL_CODES:
        return True
    if code in _NON_RETRYABLE_EXTERNAL_CODES:
        return False
    return False


def _render_pull_request_body(
    *,
    outcome: str,
    summary: str,
    branch: str,
    task_terms: tuple[str, ...],
    complexity: str,
    risk_triggers: tuple[str, ...],
    source_commit: str,
    published_head: str,
    execution: dict[str, Any],
    documentation_impact: str,
    reconciliation_base: str,
    residual_state: str,
) -> str:
    verification = ", ".join(
        f"{item.get('step_id', 'unknown')}:{item.get('status', 'unknown')}"
        for item in execution.get("verifications", ())
        if isinstance(item, dict)
    ) or "none selected"
    reviews = ", ".join(
        f"{item.get('step_id', 'unknown')}:{item.get('status', 'unknown')}"
        for item in execution.get("reviews", ())
        if isinstance(item, dict)
    ) or "none"
    scope = ", ".join(task_terms) if task_terms else "exact source commit"
    detail = summary.strip() or "No additional summary supplied."
    return (
        f"## Outcome\n{outcome}\n\n"
        f"## Summary\n{detail}\n\n"
        "## Change metadata\n"
        f"- Complexity: `{complexity}`\n"
        f"- Risk triggers: `{', '.join(risk_triggers) or 'none'}`\n"
        f"- Branch: `{branch}`\n"
        f"- Scope: {scope}\n"
        f"- Source commit: `{source_commit}`\n"
        f"- Published head: `{published_head}`\n"
        f"- Verification: {verification}\n"
        f"- Review: {reviews}\n"
        f"- Documentation impact: `{documentation_impact}`\n"
        f"- Reconciliation base: `{reconciliation_base}`\n"
        f"- Residual state: {residual_state}\n"
    )


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _sha(value: str, label: str) -> str:
    normalized = _required(value, label).lower()
    if _SHA.fullmatch(normalized) is None:
        raise ValueError(f"{label} must be a full 40-character SHA")
    return normalized


__all__ = [
    "CompletionCoordinator",
    "CompletionInvocationError",
    "Invoker",
    "ProjectResolver",
]
