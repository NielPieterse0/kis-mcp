from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from kis_mcp.workflows.coordinator import LocalGovernanceAdapter, ReservationAdmissionError


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


def test_local_governance_adapter_amends_scope_with_exact_cas(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "change-workflow.ps1").write_text("# test\n", encoding="utf-8")
    scope = tmp_path / ".work" / "changes" / "123-example" / "scope.json"
    scope.parent.mkdir(parents=True)
    payload = {
        "change_id": "123-example",
        "owned_paths": ["src/old.py"],
        "shared_paths": [],
        "dependencies": [],
        "integration_owner": "123-example",
    }
    scope.write_text(json.dumps(payload), encoding="utf-8")
    adapter = LocalGovernanceAdapter(tmp_path)

    adapter.amend_change(
        {
            "change_id": "123-example",
            "expected_claim": {key: payload[key] for key in ("owned_paths", "shared_paths", "dependencies", "integration_owner")},
            "proposed_claim": {**payload, "owned_paths": ["src/new.py"]},
        }
    )
    updated = json.loads(scope.read_text(encoding="utf-8"))
    assert updated["owned_paths"] == ["src/new.py"]


def test_local_governance_adapter_rejects_stale_scope_cas(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "change-workflow.ps1").write_text("# test\n", encoding="utf-8")
    scope = tmp_path / ".work" / "changes" / "123-example" / "scope.json"
    scope.parent.mkdir(parents=True)
    payload = {
        "change_id": "123-example",
        "owned_paths": ["src/current.py"],
        "shared_paths": [],
        "dependencies": [],
        "integration_owner": "123-example",
    }
    scope.write_text(json.dumps(payload), encoding="utf-8")
    adapter = LocalGovernanceAdapter(tmp_path)

    with pytest.raises(ReservationAdmissionError) as captured:
        adapter.amend_change(
            {
                "change_id": "123-example",
                "expected_claim": {**payload, "owned_paths": ["src/stale.py"]},
                "proposed_claim": {**payload, "owned_paths": ["src/new.py"]},
            }
        )
    assert captured.value.code == "GOVERNED_SCOPE_CAS_CONFLICT"
