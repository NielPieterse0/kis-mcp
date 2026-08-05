from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from kis_mcp.workflows.code_review.evidence import EvidenceError, GitReviewEvidenceCollector


def test_evidence_collector_reads_agents_and_fixed_git_commands(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("repository instructions", encoding="utf-8")
    calls: list[list[str]] = []

    def run(args, **kwargs):
        calls.append(list(args))
        command = tuple(args[1:])
        outputs = {
            ("status", "--short"): " M src/example.py\n",
            ("diff", "--no-ext-diff", "--unified=3"): "diff --git a/src/example.py b/src/example.py\n",
            ("diff", "--cached", "--no-ext-diff", "--unified=3"): "",
        }
        return subprocess.CompletedProcess(args, 0, stdout=outputs[command], stderr="")

    collector = GitReviewEvidenceCollector(
        project_boundary=tmp_path,
        max_chars=5000,
        runner=run,
    )

    evidence = collector.collect(project)

    assert "repository instructions" in evidence
    assert "M src/example.py" in evidence
    assert "diff --git" in evidence
    assert calls == [
        ["git", "status", "--short"],
        ["git", "diff", "--no-ext-diff", "--unified=3"],
        ["git", "diff", "--cached", "--no-ext-diff", "--unified=3"],
    ]


def test_evidence_collector_truncates_to_configured_budget(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    def run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="x" * 500, stderr="")

    collector = GitReviewEvidenceCollector(
        project_boundary=tmp_path,
        max_chars=120,
        runner=run,
    )

    evidence = collector.collect(project)

    assert len(evidence) <= 120
    assert evidence.endswith("[evidence truncated]")


def test_evidence_collector_rejects_path_outside_boundary(tmp_path: Path) -> None:
    boundary = tmp_path / "boundary"
    boundary.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    collector = GitReviewEvidenceCollector(project_boundary=boundary, max_chars=1000)

    with pytest.raises(EvidenceError, match="project boundary"):
        collector.collect(outside)
