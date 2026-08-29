from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from .contracts import TaskHandoffContract

PromotionOperationInvoker = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
CleanupInvoker = Callable[[str, Path], Awaitable[dict[str, Any]]]

_SUCCESS = {"passed", "satisfied", "applied"}


def _required_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return dict(value)


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty")
    return value.strip()


def _required_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value

class PromotionStageService:
    def __init__(
        self,
        *,
        invoker: PromotionOperationInvoker,
        contract: TaskHandoffContract,
        scope: Mapping[str, Any],
        work_record: Mapping[str, Any],
        approved: bool,
        cleanup: CleanupInvoker | None = None,
    ) -> None:
        if approved is not True:
            raise ValueError("APPROVAL_REQUIRED: approved must be true")
        self.invoker = invoker
        self.contract = contract
        self.scope = dict(scope)
        self.work_record = dict(work_record)
        self.approved = True
        self.cleanup = cleanup
        repository = contract.repository.split("/", 1)
        if len(repository) != 2 or not all(repository):
            raise ValueError("contract repository must be owner/repo")
        self.owner, self.repo = repository
        self.branch = f"change/{_required_text(contract.change_id, 'change_id')}"
        self.base_branch = _required_text(self.scope.get("base"), "scope base branch")
        self.source_root = Path(contract.source_identity).resolve()

    def _verification_workflow(self) -> str:
        path = self.source_root / "settings" / "github-merge-queue.settings.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("PROMOTION_VERIFICATION_SETTINGS_INVALID")
        return _required_text(payload.get("verification_workflow"), "verification workflow")

    @staticmethod
    def _workflow_matches(run: Mapping[str, Any], workflow: str) -> bool:
        path = run.get("path")
        return isinstance(path, str) and Path(path).name.casefold() == workflow.casefold()

    async def invoke(
        self,
        stage: str,
        handoff: dict[str, Any],
        observations: dict[str, Any],
    ) -> dict[str, Any]:
        handler = getattr(self, f"_{stage}", None)
        if handler is None:
            raise ValueError(f"PROMOTION_STAGE_UNSUPPORTED: {stage}")
        return await handler(handoff, observations)

    async def _external(self, operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.invoker(
            "execute_external_action",
            {"operation": operation, "arguments": arguments},
        )

    async def _refresh_default(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        current = await self.invoker(
            "github_get_commit",
            {"owner": self.owner, "repo": self.repo, "sha": self.base_branch, "detail": "none"},
        )
        expected = _required_text(current.get("sha"), "GitHub default SHA")
        result = await self._external(
            "kis_github_refresh_registered_default_branch",
            {"project_id": self.contract.project_id, "expected_remote_default": expected, "approved": True},
        )
        return {"status": "applied", **result, "github_default_sha": result.get("github_default_sha", expected)}

    def _base_sha(self) -> str:
        evidence = _required_mapping(self.scope.get("base_evidence"), "scope base_evidence")
        return _required_text(evidence.get("local_sha") or evidence.get("upstream_sha"), "source base SHA")

    def _source_commit(self, handoff: Mapping[str, Any]) -> str:
        return _required_text(handoff.get("source_commit_sha"), "PromotionReady source commit")

    async def _remote_branch_head(self) -> str | None:
        try:
            result = await self.invoker(
                "github_get_commit",
                {"owner": self.owner, "repo": self.repo, "sha": self.branch, "detail": "none"},
            )
        except Exception as exc:
            detail = str(exc).casefold()
            if "not found" in detail or "404" in detail:
                return None
            raise
        value = result.get("sha")
        return value.strip().lower() if isinstance(value, str) and value.strip() else None

    async def _reconcile_candidate(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        refresh = _required_mapping(observations.get("refresh_default"), "refresh_default observation")
        expected_default = _required_text(refresh.get("github_default_sha"), "GitHub default SHA")
        result = await self._external(
            "kis_github_reconcile_registered_commit",
            {
                "project_id": self.contract.project_id,
                "commit": self._source_commit(handoff),
                "source_base": self._base_sha(),
                "branch": self.branch,
                "expected_remote_default": expected_default,
                "expected_remote_branch": await self._remote_branch_head(),
                "approved": True,
            },
        )
        published = _required_text(result.get("commit_sha"), "published head SHA")
        return {"status": "applied", **result, "commit_sha": published, "branch": self.branch}

    def _source_number(self) -> int:
        work = _required_mapping(self.scope.get("work_management"), "scope work_management")
        return _required_int(work.get("source_number"), "source issue number")

    async def _issue(self) -> dict[str, Any]:
        return await self.invoker(
            "github_issue_read",
            {"method": "get", "owner": self.owner, "repo": self.repo, "issue_number": self._source_number()},
        )

    async def _create_pull_request(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        refresh = _required_mapping(observations.get("refresh_default"), "refresh_default observation")
        published = _required_mapping(observations.get("reconcile_candidate"), "reconcile_candidate observation")
        issue = await self._issue()
        expected_head = _required_text(published.get("commit_sha"), "published head SHA")
        result = await self._external(
            "kis_github_create_registered_pull_request",
            {
                "project_id": self.contract.project_id,
                "branch": self.branch,
                "expected_head": expected_head,
                "expected_remote_default": _required_text(refresh.get("github_default_sha"), "GitHub default SHA"),
                "title": _required_text(issue.get("title"), "issue title"),
                "body": self._pull_request_body(issue, handoff),
                "approved": True,
            },
        )
        pull_number = _required_int(result.get("pull_number"), "pull request number")
        head_sha = _required_text(result.get("head_sha") or expected_head, "pull request head SHA")
        if head_sha != expected_head:
            raise ValueError("PROMOTION_PULL_REQUEST_HEAD_MISMATCH")
        return {"status": "applied", **result, "pull_number": pull_number, "head_sha": head_sha}

    def _pull_request_body(self, issue: Mapping[str, Any], handoff: Mapping[str, Any]) -> str:
        return (
            f"## Outcome\n{_required_text(issue.get('title'), 'issue title')}\n\n"
            f"## Work\n- Work ID: `{self.contract.work_id}`\n"
            f"- Change ID: `{self.contract.change_id}`\n"
            f"- PromotionReady source: `{self._source_commit(handoff)}`\n\n"
            "Implementation verification and substantive KIS review are already closed in PromotionReady."
        )

    async def _exact_head_actions(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        created = _required_mapping(observations.get("create_pull_request"), "create_pull_request observation")
        pull_number = _required_int(created.get("pull_number"), "pull request number")
        expected_head = _required_text(created.get("head_sha"), "pull request head SHA")
        pull = await self.invoker(
            "github_pull_request_read",
            {"method": "get", "owner": self.owner, "repo": self.repo, "pullNumber": pull_number},
        )
        head = _required_mapping(pull.get("head"), "pull request head")
        actual_head = _required_text(head.get("sha"), "provider pull request head SHA")
        if actual_head != expected_head:
            raise ValueError("PROMOTION_PULL_REQUEST_HEAD_CHANGED")
        workflow = self._verification_workflow()
        detail: dict[str, Any] | None = None
        run_id: int | None = None
        saw_exact_workflow = False
        exhausted = False
        for page in range(1, 11):
            listed = await self.invoker(
                "github_actions_list",
                {
                    "method": "list_workflow_runs", "owner": self.owner, "repo": self.repo,
                    "per_page": 100, "page": page,
                    "workflow_runs_filter": {"branch": self.branch},
                },
            )
            raw_runs = listed.get("workflow_runs")
            if not isinstance(raw_runs, list):
                raw_runs = []
            exact_runs = [
                dict(item) for item in raw_runs
                if isinstance(item, Mapping)
                and item.get("head_sha") == expected_head
                and self._workflow_matches(item, workflow)
            ]
            saw_exact_workflow = saw_exact_workflow or bool(exact_runs)
            for candidate in sorted(
                exact_runs,
                key=lambda item: _required_int(item.get("id"), "GitHub Actions run ID"),
                reverse=True,
            ):
                candidate_id = _required_int(candidate.get("id"), "GitHub Actions run ID")
                candidate_detail = await self.invoker(
                    "github_actions_get",
                    {
                        "method": "get_workflow_run", "owner": self.owner, "repo": self.repo,
                        "resource_id": str(candidate_id),
                    },
                )
                if candidate_detail.get("head_sha") != expected_head:
                    raise ValueError("PROMOTION_ACTIONS_HEAD_MISMATCH")
                if candidate_detail.get("event") != "pull_request":
                    continue
                run_pull_requests = candidate_detail.get("pull_requests")
                if not isinstance(run_pull_requests, list) or not run_pull_requests:
                    continue
                numbers = {
                    item.get("number") for item in run_pull_requests if isinstance(item, Mapping)
                }
                if pull_number not in numbers:
                    continue
                detail = candidate_detail
                run_id = candidate_id
                break
            if detail is not None:
                break
            if len(raw_runs) < 100:
                exhausted = True
                break
        if detail is None or run_id is None:
            reason = (
                "github_actions_required_workflow_missing" if not saw_exact_workflow
                else "github_actions_pull_request_run_missing" if exhausted
                else "github_actions_search_truncated"
            )
            return {
                "status": "blocked", "reason": reason,
                "pull_number": pull_number, "head_sha": expected_head,
                "workflow": workflow,
            }
        if detail.get("status") != "completed":
            return {
                "status": "blocked", "reason": "github_actions_pending",
                "pull_number": pull_number, "head_sha": expected_head,
                "workflow": workflow, "run_ids": [run_id],
            }
        if detail.get("conclusion") != "success":
            return {
                "status": "blocked", "reason": "github_actions_failed",
                "pull_number": pull_number, "head_sha": expected_head,
                "workflow": workflow, "run_ids": [run_id],
            }
        return {
            "status": "passed", "pull_number": pull_number, "head_sha": expected_head,
            "workflow": workflow, "reference": f"github-actions:{run_id}",
            "run_ids": [run_id],
        }

    def _trace(self, observations: Mapping[str, Any], *, merged: bool = False) -> dict[str, Any]:
        created = _required_mapping(observations.get("create_pull_request"), "create_pull_request observation")
        actions = _required_mapping(observations.get("exact_head_actions"), "exact_head_actions observation")
        pull_number = _required_int(created.get("pull_number"), "pull request number")
        head_sha = _required_text(created.get("head_sha"), "pull request head SHA")
        trace: dict[str, Any] = {
            "schema_version": 1,
            "project_id": self.contract.project_id,
            "implementation_record_id": _required_text(self.contract.work_id, "Work handoff ID"),
            "specification_record_id": (
                _required_text(self.work_record.get("record_id"), "Work record ID")
                if self.work_record.get("record_type") == "specification_slice"
                else None
            ),
            "change_id": _required_text(self.contract.change_id, "change_id"),
            "branch": self.branch,
            "worktree": _required_text(self.scope.get("worktree"), "scope worktree"),
            "pull_requests": [{
                "repository": self.contract.repository, "number": pull_number,
                "head_branch": self.branch, "head_revision": head_sha,
                "base_branch": self.base_branch, "state": "merged" if merged else "open",
            }],
            "verifications": [{
                "evidence_id": f"github-actions-pr-{pull_number}",
                "pull_request_number": pull_number, "revision": head_sha,
                "status": "passed", "command": "provider-native GitHub Actions",
                "source": "github_actions", "reference": actions.get("reference"),
            }],
            "merges": [], "documentation_events": [],
        }
        if merged:
            merge = _required_mapping(observations.get("merge_exact_head"), "merge_exact_head observation")
            merge_sha = _required_text(merge.get("merge_commit_sha") or merge.get("merge_commit"), "merge commit SHA")
            trace["merges"] = [{
                "pull_request_number": pull_number,
                "merge_commit": merge_sha,
                "head_revision": head_sha,
            }]
        return trace

    async def _merge_readiness(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        created = _required_mapping(observations.get("create_pull_request"), "create_pull_request observation")
        pull_number = _required_int(created.get("pull_number"), "pull request number")
        result = await self.invoker(
            "project_management_merge_readiness",
            {"record": dict(self.work_record), "trace": self._trace(observations), "pull_request_number": pull_number},
        )
        if result.get("ready") is not True:
            return {"status": "blocked", "reason": "work_merge_readiness_blocked", **result}
        return {"status": "satisfied", **result, "pull_number": pull_number, "head_sha": created["head_sha"]}

    async def _merge_exact_head(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        readiness = _required_mapping(observations.get("merge_readiness"), "merge_readiness observation")
        if readiness.get("ready") is not True or readiness.get("status") not in _SUCCESS:
            return {"status": "blocked", "reason": "work_merge_readiness_blocked"}
        pull_number = _required_int(readiness.get("pull_number"), "pull request number")
        head_sha = _required_text(readiness.get("head_sha"), "pull request head SHA")
        result = await self._external(
            "kis_github_merge_registered_pull_request",
            {
                "project_id": self.contract.project_id,
                "pull_number": pull_number,
                "expected_head": head_sha,
                "merge_method": "merge",
                "approved": True,
            },
        )
        merge_sha = result.get("merge_commit_sha") or result.get("merge_commit")
        if not isinstance(merge_sha, str) or not merge_sha.strip():
            return {
                "status": "blocked", "reason": "merge_identity_pending",
                **result, "pull_number": pull_number, "head_sha": head_sha,
            }
        return {"status": "applied", **result, "pull_number": pull_number, "head_sha": head_sha}

    async def _default_contains_commit(self, default_sha: str, target_sha: str) -> bool:
        if default_sha == target_sha:
            return True
        for page in range(1, 11):
            result = await self.invoker(
                "github_list_commits",
                {"owner": self.owner, "repo": self.repo, "sha": default_sha,
                 "page": page, "perPage": 100, "fields": ["sha"]},
            )
            commits = result.get("commits", result) if isinstance(result, Mapping) else result
            if isinstance(commits, Mapping):
                commits = commits.get("items", commits.get("data", []))
            if not isinstance(commits, list):
                raise ValueError("PROMOTION_DEFAULT_HISTORY_INVALID")
            shas = {str(item.get("sha", "")).strip().lower()
                    for item in commits if isinstance(item, Mapping)}
            if target_sha.lower() in shas:
                return True
            if len(commits) < 100:
                return False
        return False

    async def _refresh_landed(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        merged = _required_mapping(observations.get("merge_exact_head"), "merge_exact_head observation")
        merge_sha = _required_text(merged.get("merge_commit_sha") or merged.get("merge_commit"), "merge commit SHA")
        current = await self.invoker(
            "github_get_commit",
            {"owner": self.owner, "repo": self.repo, "sha": self.base_branch, "detail": "none"},
        )
        current_default = _required_text(current.get("sha"), "current GitHub default SHA")
        result = await self._external(
            "kis_github_refresh_registered_default_branch",
            {"project_id": self.contract.project_id, "expected_remote_default": current_default, "approved": True},
        )
        landed = _required_text(result.get("github_default_sha") or current_default, "landed default SHA")
        if landed != current_default:
            raise ValueError("PROMOTION_LANDED_SHA_MISMATCH")
        if not await self._default_contains_commit(landed, merge_sha):
            return {
                "status": "blocked", "reason": "merge_commit_not_in_default_history",
                **result, "landed_sha": landed, "merge_commit_sha": merge_sha,
            }
        return {"status": "applied", **result, "landed_sha": landed, "merge_commit_sha": merge_sha}

    async def _documentation_reconcile(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        created = _required_mapping(observations.get("create_pull_request"), "create_pull_request observation")
        landed = _required_mapping(observations.get("refresh_landed"), "refresh_landed observation")
        pull_number = _required_int(created.get("pull_number"), "pull request number")
        landed_sha = _required_text(landed.get("landed_sha"), "landed SHA")
        trace = self._trace(observations, merged=True)
        if self.work_record.get("documentation_impact") != "pre_merge_complete":
            return {
                "status": "blocked", "reason": "documentation_pre_merge_evidence_missing",
                "documentation_impact": self.work_record.get("documentation_impact"),
            }
        due = await self.invoker(
            "project_management_documentation_reconcile",
            {
                "record": dict(self.work_record), "trace": trace,
                "pull_request_number": pull_number,
                "documentation_task_id": f"docs-{self.contract.change_id}",
                "required_updates": [],
            },
        )
        event = _required_mapping(due.get("event"), "documentation due event")
        trace["documentation_events"] = [event]
        completed = await self.invoker(
            "project_management_documentation_reconcile",
            {
                "record": _required_mapping(due.get("record"), "documentation due record"),
                "trace": trace, "pull_request_number": pull_number,
                "documentation_task_id": f"docs-{self.contract.change_id}",
                "required_updates": list(event.get("required_updates", ())),
                "completion_revision": landed_sha,
            },
        )
        completed_event = _required_mapping(completed.get("event"), "documentation completed event")
        completed_record = _required_mapping(completed.get("record"), "documentation completed record")
        if completed.get("phase") != "post_merge_complete":
            return {"status": "blocked", "reason": "documentation_reconciliation_incomplete", **completed}
        if completed_event.get("completion_revision") != landed_sha:
            return {"status": "blocked", "reason": "documentation_revision_mismatch", **completed}
        if completed_record.get("documentation_impact") != "post_merge_complete":
            return {"status": "blocked", "reason": "documentation_work_state_incomplete", **completed}
        return {"status": "satisfied", **completed, "trace": trace, "completion_revision": landed_sha}

    async def _work_done(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        documentation = _required_mapping(observations.get("documentation_reconcile"), "documentation_reconcile observation")
        record = _required_mapping(documentation.get("record"), "post-merge Work record")
        result = await self.invoker(
            "project_management_complete_work",
            {
                "project_id": self.contract.project_id,
                "repository": self.contract.repository,
                "issue_number": self._source_number(),
                "record": record,
                "apply": True,
                "idempotency_key": f"promotion-done-{self.contract.work_id}-{self._source_commit(handoff)}",
            },
        )
        if result.get("mode") == "blocked":
            return {"status": "blocked", "reason": "work_completion_blocked", **result}
        if result.get("source_close_required") is True:
            await self.invoker(
                "github_issue_write",
                {"method": "update", "owner": self.owner, "repo": self.repo,
                 "issue_number": self._source_number(), "state": "closed", "state_reason": "completed"},
            )
        return {"status": "applied", **result, "record": record}

    async def _cleanup(
        self, handoff: dict[str, Any], observations: dict[str, Any]
    ) -> dict[str, Any]:
        if self.cleanup is None:
            return {"status": "blocked", "reason": "cleanup_service_unavailable"}
        worktree = Path(self.contract.source_identity).resolve()
        result = await self.cleanup(_required_text(self.contract.change_id, "change_id"), worktree)
        return {"status": "applied", **result}


__all__ = ["CleanupInvoker", "PromotionOperationInvoker", "PromotionStageService"]
