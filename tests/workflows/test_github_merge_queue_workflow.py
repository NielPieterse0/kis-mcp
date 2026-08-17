from __future__ import annotations

from pathlib import Path

from kis_mcp.workflows.platform import workflow_descriptors


def test_actions_backed_queue_workflows_are_not_canonical() -> None:
    workflow_ids = {item.workflow_id for item in workflow_descriptors()}

    assert "speculative-landing-queue" not in workflow_ids
    assert "complete-work-managed-merge-queue" not in workflow_ids


def test_historical_actions_queue_workflow_remains_untouched() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github" / "workflows" / "work-management.yml").read_text(encoding="utf-8")

    assert "push:" in workflow
    assert "'kis-readonly-queue/main/**'" in workflow
    assert "KIS_EXACT_SHA: ${{ github.event.pull_request.head.sha || github.sha }}" in workflow
    assert "pwsh -NoProfile -File scripts/verify.ps1 -SkipDependencySync" in workflow
