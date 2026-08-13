from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

from .contracts import CompletionResult

Invoker = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
ProjectResolver = Callable[[str], str]
_SHA = re.compile(r"^[0-9a-f]{40}$")


class CompletionInvocationError(RuntimeError):
    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"{code}: {reason}")


class CompletionCoordinator:
    def __init__(self, invoker: Invoker, project_resolver: ProjectResolver) -> None:
        self._invoker = invoker
        self._project_resolver = project_resolver

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
        risk_profile: str = "standard",
        max_verifications: int | None = None,
        verification_timeout_ms: int = 120_000,
        review_types: tuple[str, ...] | None = None,
        review_backend: str | None = None,
        review_model: str | None = None,
        documentation_impact: str = "not_assessed",
        residual_state: str = "none declared",
    ) -> CompletionResult:
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
        if risk_profile not in {"lean", "standard", "rigorous"}:
            raise ValueError("risk_profile must be lean, standard, or rigorous")
        documentation_impact = _required(documentation_impact, "documentation_impact")
        if documentation_impact not in {
            "not_assessed", "none", "planned", "in_progress", "pre_merge_complete", "post_merge_complete"
        }:
            raise ValueError("documentation_impact is unsupported")
        residual_state = _required(residual_state, "residual_state")
        if approved is not True:
            raise ValueError("approved must be true")
        try:
            project_root = _required(self._project_resolver(project_key), "project root")
        except (KeyError, ValueError) as exc:
            raise CompletionInvocationError(
                "COMPLETION_PROJECT_UNKNOWN",
                f"registered project {project_key!r} could not be resolved",
            ) from exc

        execution_args: dict[str, Any] = {
            "project": project_root,
            "source": "commit",
            "commit_ref": commit_sha,
            "task_terms": list(task_terms),
            "risk_profile": risk_profile,
            "verification_timeout_ms": verification_timeout_ms,
        }
        if max_verifications is not None:
            execution_args["max_verifications"] = max_verifications
        if review_types is not None:
            execution_args["review_types"] = list(review_types)
        if review_backend is not None:
            execution_args["review_backend"] = review_backend
        if review_model is not None:
            execution_args["review_model"] = review_model
        execution = await self._invoker("execute_change_workflow", execution_args)
        if execution.get("contract") != "change-execution-result-v1":
            raise CompletionInvocationError(
                "COMPLETION_EXECUTION_INVALID",
                "change execution returned an unexpected contract",
            )
        if execution.get("status") != "passed":
            raise ValueError("change execution must pass before external mutation")

        publication = await self._invoker(
            "execute_external_action",
            {
                "operation": "kis_github_reconcile_registered_commit",
                "arguments": {
                    "project_id": project_key,
                    "commit": commit_sha,
                    "source_base": source_base_sha,
                    "branch": branch_name,
                    "expected_remote_default": default_sha,
                    "expected_remote_branch": branch_base,
                    "approved": True,
                },
            },
        )
        published_head = str(publication.get("commit_sha", "")).lower()
        if (
            publication.get("state") != "published"
            or publication.get("source_commit_sha") != commit_sha
            or _SHA.fullmatch(published_head) is None
            or publication.get("branch") != branch_name
        ):
            raise CompletionInvocationError(
                "COMPLETION_PUBLICATION_INVALID",
                "registered reconciliation did not preserve the exact source commit/tree and review branch",
            )

        pull_request_body = _render_pull_request_body(
            outcome=title_text,
            summary=body,
            branch=branch_name,
            task_terms=task_terms,
            risk_profile=risk_profile,
            source_commit=commit_sha,
            published_head=published_head,
            execution=execution,
            documentation_impact=documentation_impact,
            residual_state=residual_state,
        )
        if len(pull_request_body) > 20_000:
            raise ValueError("generated pull request body exceeds 20000 characters")

        pull_request = await self._invoker(
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
                },
            },
        )
        if (
            pull_request.get("state") != "open"
            or pull_request.get("head_sha") != published_head
            or pull_request.get("branch") != branch_name
        ):
            raise CompletionInvocationError(
                "COMPLETION_PULL_REQUEST_INVALID",
                "registered pull request did not return the exact reconciled head and branch",
            )
        return CompletionResult(
            project_id=project_key,
            source_commit_sha=commit_sha,
            published_head_sha=published_head,
            branch=branch_name,
            execution=execution,
            publication=publication,
            pull_request=pull_request,
        )


def _render_pull_request_body(
    *,
    outcome: str,
    summary: str,
    branch: str,
    task_terms: tuple[str, ...],
    risk_profile: str,
    source_commit: str,
    published_head: str,
    execution: dict[str, Any],
    documentation_impact: str,
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
        f"- Risk profile: `{risk_profile}`\n"
        f"- Branch: `{branch}`\n"
        f"- Scope: {scope}\n"
        f"- Source commit: `{source_commit}`\n"
        f"- Published head: `{published_head}`\n"
        f"- Verification: {verification}\n"
        f"- Review: {reviews}\n"
        f"- Documentation impact: `{documentation_impact}`\n"
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
