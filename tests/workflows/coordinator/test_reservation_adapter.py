from __future__ import annotations

import subprocess
from pathlib import Path

from kis_mcp.workflows.coordinator import LocalGovernanceAdapter


ROOT = Path(__file__).parents[3]


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip().lower()


def test_local_governance_adapter_resolves_exact_git_commit_and_tree() -> None:
    adapter = LocalGovernanceAdapter(ROOT)
    identity = adapter.resolve_base("HEAD")

    assert identity == {
        "commit_sha": _git("rev-parse", "--verify", "HEAD^{commit}"),
        "tree_sha": _git("rev-parse", "--verify", "HEAD^{tree}"),
    }
