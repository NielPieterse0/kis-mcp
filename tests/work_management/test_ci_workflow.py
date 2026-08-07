from __future__ import annotations

from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "work-management.yml"
)


def test_work_management_workflow_is_reusable_and_exact_revision_aware() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_call:" in text
    assert "workflow_dispatch:" in text
    assert "permissions:\n  contents: read" in text
    assert "--revision $env:GITHUB_SHA" in text
    assert "scripts/change-workflow.ps1 validate" in text
    assert "scripts/verify.ps1" in text
    assert "UV_CACHE_DIR: C:\\Projects\\.kis-mcp\\uv-cache" in text
    assert "git worktree add --detach C:\\Projects\\kis-mcp HEAD" in text
    assert "working-directory: C:\\Projects\\kis-mcp" in text
    assert "persist-credentials: false" in text


def test_workflow_uses_pinned_or_versioned_official_actions() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/checkout@v7.0.1" in text
    assert (
        "astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b"
        in text
    )
    assert "pull-requests: write" not in text
    assert "issues: write" not in text
    assert "projects: write" not in text
