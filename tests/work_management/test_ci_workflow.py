from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "work-management.yml"
WRAPPER = ROOT / "scripts" / "project-workflow.ps1"


def test_work_management_workflow_is_reusable_and_exact_revision_aware() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "pull_request:" in text
    assert "workflow_call:" in text
    assert "workflow_dispatch:" in text
    assert "permissions:\n  contents: read" in text
    assert "KIS_EXACT_SHA: ${{ github.event.pull_request.head.sha || github.sha }}" in text
    assert "ref: ${{ env.KIS_EXACT_SHA }}" in text
    assert "EXACT_HEAD_MISMATCH" in text
    assert "uv sync --locked --all-groups" in text
    assert "scripts/verify.ps1 -SkipDependencySync" in text
    assert text.count("uv sync --locked --all-groups") == 1
    assert text.count("scripts/verify.ps1 -SkipDependencySync") == 1
    assert "UV_CACHE_DIR: C:\\Projects\\.kis-mcp\\uv-cache" in text
    assert "Copy-Item -Destination C:\\Projects\\kis-mcp -Recurse -Force" in text
    assert "C:\\Projects\\.agents\\skills" not in text
    assert "Get-ChildItem -Force C:\\Projects\\kis-mcp\\.agents\\skills" not in text
    assert "working-directory: C:\\Projects\\kis-mcp" in text
    assert "persist-credentials: false" in text


def test_workflow_uses_immutable_official_action_revisions() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in text
    assert "# v7.0.1" in text
    assert (
        "astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b"
        in text
    )
    assert "pull-requests: write" not in text
    assert "issues: write" not in text
    assert "projects: write" not in text


def test_project_workflow_wrapper_imports_the_selected_worktree_source() -> None:
    text = WRAPPER.read_text(encoding="utf-8")

    assert "$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'" in text
    assert "uv run --offline --no-sync python scripts\\project_workflow.py" in text
