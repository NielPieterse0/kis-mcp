from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from kis_mcp.workflows.once_through.contracts import TaskHandoffContract
from kis_mcp.workflows.once_through.promotion import PromotionStageService

HEAD = "a" * 40
BASE = "b" * 40
PUBLISHED = "c" * 40
LANDED = "d" * 40


class FakeInvoker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.responses: dict[str, dict[str, Any]] = {}
        self.action_runs: dict[str, dict[str, Any]] = {}

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        operation = str(arguments.get("operation", tool_name))
        resource_id = arguments.get("resource_id")
        if operation == "github_actions_get" and isinstance(resource_id, str) and resource_id in self.action_runs:
            return dict(self.action_runs[resource_id])
        return dict(self.responses[operation])


def _contract(tmp_path: Path) -> TaskHandoffContract:
    return TaskHandoffContract(
        project_id="kis-mcp", work_id="WORK-585", repository="NielPieterse0/kis-mcp",
        requirements=("converge",), acceptance_criteria=("done",), affected_surfaces=("mcp",),
        obligations=("verification",), candidate_port=46000, source_identity=str(tmp_path),
        change_id="263-test",
    )


def _scope(tmp_path: Path) -> dict[str, Any]:
    return {
        "change_id": "263-test", "branch": "change/263-test",
        "worktree": str(tmp_path), "base": "main", "outcome": "Converge to Done",
        "base_evidence": {"local_sha": BASE, "upstream_sha": BASE},
        "work_management": {
            "project_id": "kis-mcp", "record_id": "WORK-585",
            "source_repository": "NielPieterse0/kis-mcp", "source_number": 585,
        },
    }


def _record() -> dict[str, Any]:
    return {
        "schema_version": 1, "record_id": "SPEC-585", "project_id": "kis-mcp",
        "title": "Converge", "record_type": "specification_slice", "state": "active",
        "priority": "critical", "effort": "large", "delivery_stage": "ci_passed",
        "execution_owner": "codex", "complexity": "large", "risk_triggers": [],
        "documentation_mode": "required", "documentation_impact": "pre_merge_complete",
        "traceability_required": True,
    }


def _service(tmp_path: Path, invoker: FakeInvoker) -> PromotionStageService:
    settings = tmp_path / "settings"
    settings.mkdir(parents=True, exist_ok=True)
    (settings / "github-merge-queue.settings.json").write_text(
        '{"verification_workflow":"work-management.yml"}\n', encoding="utf-8"
    )
    return PromotionStageService(
        invoker=invoker, contract=_contract(tmp_path), scope=_scope(tmp_path),
        work_record=_record(), approved=True,
    )


def _handoff() -> dict[str, Any]:
    return {"status": "promotion_ready", "source_commit_sha": HEAD}


def test_refresh_and_reconcile_use_authoritative_exact_shas(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    invoker.responses = {
        "github_get_commit": {"sha": BASE},
        "kis_github_refresh_registered_default_branch": {"github_default_sha": BASE},
        "kis_github_reconcile_registered_commit": {
            "state": "published", "source_commit_sha": HEAD,
            "commit_sha": PUBLISHED, "branch": "change/263-test",
        },
    }
    stage = _service(tmp_path, invoker)
    refresh = asyncio.run(stage.invoke("refresh_default", _handoff(), {}))
    reconcile = asyncio.run(stage.invoke(
        "reconcile_candidate", _handoff(), {"refresh_default": refresh}
    ))
    assert refresh["github_default_sha"] == BASE
    assert reconcile["commit_sha"] == PUBLISHED
    envelope = next(args for _, args in invoker.calls
                    if args.get("operation") == "kis_github_reconcile_registered_commit")
    assert envelope["arguments"]["commit"] == HEAD
    assert envelope["arguments"]["expected_remote_default"] == BASE


def test_exact_head_actions_blocks_until_provider_actions_complete(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    invoker.responses.update({
        "github_pull_request_read": {"head": {"sha": PUBLISHED}},
        "github_actions_list": {
            "workflow_runs": [{"id": 11, "head_sha": PUBLISHED, "status": "in_progress", "path": ".github/workflows/work-management.yml"}],
        },
        "github_actions_get": {
            "id": 11, "head_sha": PUBLISHED, "event": "pull_request", "pull_requests": [{"number": 9}], "status": "in_progress", "conclusion": None,
        },
    })
    result = asyncio.run(_service(tmp_path, invoker).invoke(
        "exact_head_actions", _handoff(),
        {"create_pull_request": {"pull_number": 9, "head_sha": PUBLISHED}},
    ))
    assert result["status"] == "blocked"
    assert result["reason"] == "github_actions_pending"


def test_merge_readiness_blocks_without_canonical_ready_result(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    invoker.responses["project_management_merge_readiness"] = {
        "ready": False, "blocking_reasons": ["documentation_pre_merge_incomplete"]
    }
    result = asyncio.run(_service(tmp_path, invoker).invoke(
        "merge_readiness", _handoff(), {
            "create_pull_request": {"pull_number": 9, "head_sha": PUBLISHED},
            "exact_head_actions": {"status": "passed", "reference": "actions:11"},
        },
    ))
    assert result["status"] == "blocked"


def test_merge_uses_exact_ready_head_and_never_restarts_review(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    invoker.responses["kis_github_merge_registered_pull_request"] = {
        "state": "merged", "pull_number": 9,
        "authorized_head": PUBLISHED, "merge_commit_sha": LANDED,
    }
    result = asyncio.run(_service(tmp_path, invoker).invoke(
        "merge_exact_head", _handoff(), {
            "merge_readiness": {
                "status": "satisfied", "ready": True,
                "pull_number": 9, "head_sha": PUBLISHED,
            }
        },
    ))
    assert result["status"] == "applied"
    assert result["merge_commit_sha"] == LANDED
    envelope = next(args for _, args in invoker.calls
                    if args.get("operation") == "kis_github_merge_registered_pull_request")
    assert envelope["arguments"]["expected_head"] == PUBLISHED
    called = {str(args.get("operation", name)) for name, args in invoker.calls}
    assert "execute_change_workflow" not in called
    assert "review_change_with_agent" not in called


def test_exact_head_actions_accepts_only_matching_successful_runs(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    invoker.responses.update({
        "github_pull_request_read": {"head": {"sha": PUBLISHED}},
        "github_actions_list": {
            "workflow_runs": [
                {"id": 10, "head_sha": "f" * 40, "status": "completed"},
                {"id": 11, "head_sha": PUBLISHED, "status": "completed", "path": ".github/workflows/work-management.yml"},
            ],
        },
        "github_actions_get": {
            "id": 11, "head_sha": PUBLISHED, "event": "pull_request", "pull_requests": [{"number": 9}], "status": "completed", "conclusion": "success",
        },
    })
    result = asyncio.run(_service(tmp_path, invoker).invoke(
        "exact_head_actions", _handoff(),
        {"create_pull_request": {"pull_number": 9, "head_sha": PUBLISHED}},
    ))
    assert result["status"] == "passed"
    assert result["run_ids"] == [11]
    assert result["reference"] == "github-actions:11"


def test_refresh_landed_accepts_merge_commit_in_newer_default_history(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    newer = "e" * 40
    invoker.responses.update({
        "github_get_commit": {"sha": newer},
        "kis_github_refresh_registered_default_branch": {"github_default_sha": newer},
        "github_list_commits": {"commits": [{"sha": newer}, {"sha": LANDED}]},
    })
    result = asyncio.run(_service(tmp_path, invoker).invoke(
        "refresh_landed", _handoff(),
        {"merge_exact_head": {"merge_commit_sha": LANDED}},
    ))
    assert result["status"] == "applied"
    assert result["landed_sha"] == newer
    assert result["merge_commit_sha"] == LANDED


def test_exact_head_actions_rejects_non_pr_run_at_same_sha(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    invoker.responses.update({
        "github_pull_request_read": {"head": {"sha": PUBLISHED}},
        "github_actions_list": {"workflow_runs": [{
            "id": 12, "head_sha": PUBLISHED, "status": "completed",
            "path": ".github/workflows/work-management.yml",
        }]},
        "github_actions_get": {
            "id": 12, "head_sha": PUBLISHED, "event": "workflow_dispatch",
            "status": "completed", "conclusion": "success",
        },
    })
    result = asyncio.run(_service(tmp_path, invoker).invoke(
        "exact_head_actions", _handoff(),
        {"create_pull_request": {"pull_number": 9, "head_sha": PUBLISHED}},
    ))
    assert result["status"] == "blocked"
    assert result["reason"] == "github_actions_pull_request_run_missing"


def test_exact_head_actions_ignores_newer_unrelated_run(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    invoker.responses.update({
        "github_pull_request_read": {"head": {"sha": PUBLISHED}},
        "github_actions_list": {"workflow_runs": [
            {"id": 13, "head_sha": PUBLISHED, "path": ".github/workflows/work-management.yml"},
            {"id": 12, "head_sha": PUBLISHED, "path": ".github/workflows/work-management.yml"},
        ]},
    })
    invoker.action_runs = {
        "13": {"id": 13, "head_sha": PUBLISHED, "event": "workflow_dispatch", "status": "completed", "conclusion": "success"},
        "12": {"id": 12, "head_sha": PUBLISHED, "event": "pull_request", "pull_requests": [{"number": 9}], "status": "completed", "conclusion": "success"},
    }
    result = asyncio.run(_service(tmp_path, invoker).invoke(
        "exact_head_actions", _handoff(),
        {"create_pull_request": {"pull_number": 9, "head_sha": PUBLISHED}},
    ))
    assert result["status"] == "passed"
    assert result["run_ids"] == [12]


def test_exact_head_actions_rejects_pr_run_without_pr_association(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    invoker.responses.update({
        "github_pull_request_read": {"head": {"sha": PUBLISHED}},
        "github_actions_list": {"workflow_runs": [{
            "id": 14, "head_sha": PUBLISHED,
            "path": ".github/workflows/work-management.yml",
        }]},
        "github_actions_get": {
            "id": 14, "head_sha": PUBLISHED, "event": "pull_request",
            "pull_requests": [], "status": "completed", "conclusion": "success",
        },
    })
    result = asyncio.run(_service(tmp_path, invoker).invoke(
        "exact_head_actions", _handoff(),
        {"create_pull_request": {"pull_number": 9, "head_sha": PUBLISHED}},
    ))
    assert result["status"] == "blocked"
    assert result["reason"] == "github_actions_pull_request_run_missing"


def test_merge_exact_head_blocks_until_merge_identity_exists(tmp_path: Path) -> None:
    invoker = FakeInvoker()
    invoker.responses["kis_github_merge_registered_pull_request"] = {
        "state": "merged", "pull_number": 9, "authorized_head": PUBLISHED,
        "merge_commit_sha": None,
    }
    result = asyncio.run(_service(tmp_path, invoker).invoke(
        "merge_exact_head", _handoff(), {
            "merge_readiness": {
                "status": "satisfied", "ready": True,
                "pull_number": 9, "head_sha": PUBLISHED,
            }
        },
    ))
    assert result["status"] == "blocked"
    assert result["reason"] == "merge_identity_pending"


def test_trace_preserves_source_and_typed_specification_identity(tmp_path: Path) -> None:
    service = _service(tmp_path, FakeInvoker())
    trace = service._trace({
        "create_pull_request": {"pull_number": 9, "head_sha": PUBLISHED},
        "exact_head_actions": {"status": "passed", "reference": "github-actions:11"},
    })
    assert trace["implementation_record_id"] == "WORK-585"
    assert trace["specification_record_id"] == "SPEC-585"
