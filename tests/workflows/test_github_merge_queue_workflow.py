from __future__ import annotations

from pathlib import Path

from kis_mcp.workflows.platform import workflow_descriptors


def test_platform_exposes_speculative_landing_queue_workflow() -> None:
    descriptors = {item.workflow_id: item for item in workflow_descriptors()}
    queue = descriptors["speculative-landing-queue"]

    assert queue.required_steps == (
        "github_pull_request_read",
        "kis_github_merge_queue_enqueue",
        "kis_github_merge_queue_reconcile",
        "kis_github_merge_queue_land",
        "kis_github_refresh_registered_default_branch",
    )
    assert "operation.kis_github_merge_queue_land" in queue.capabilities
    assert "registered default-branch tracking equals exact GitHub truth" in queue.completion_criteria


def test_work_management_queue_path_preserves_existing_readiness_gate() -> None:
    descriptors = {item.workflow_id: item for item in workflow_descriptors()}
    queue = descriptors["complete-work-managed-merge-queue"]

    readiness_index = queue.required_steps.index("project_management_merge_readiness")
    enqueue_index = queue.required_steps.index("kis_github_merge_queue_enqueue")
    assert readiness_index < enqueue_index
    assert "kis_github_merge_queue_reconcile" in queue.required_steps
    assert "kis_github_merge_queue_land" in queue.required_steps
    assert queue.required_steps[-1] == "project_management_documentation_reconcile"


def test_canonical_verification_runs_on_queue_candidate_pushes() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github" / "workflows" / "work-management.yml").read_text(encoding="utf-8")

    assert "push:" in workflow
    assert "'kis-readonly-queue/main/**'" in workflow
    assert "KIS_EXACT_SHA: ${{ github.event.pull_request.head.sha || github.sha }}" in workflow
    assert "pwsh -NoProfile -File scripts/verify.ps1 -SkipDependencySync" in workflow
