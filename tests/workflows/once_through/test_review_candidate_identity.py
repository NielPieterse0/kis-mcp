from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from kis_mcp.workflows.once_through.candidate_runtime import (
    candidate_binding,
    select_live_verification_scenarios,
)
from kis_mcp.workflows.once_through.contracts import TaskHandoffContract
from kis_mcp.workflows.once_through.review import (
    closure_from_execution,
    targeted_review_domains,
)
from kis_mcp.workflows.once_through.tools import _candidate_matches


def _git_repo(root: Path) -> Path:
    root.mkdir()
    (root / "policy").mkdir()
    (root / "settings").mkdir()
    (root / "policy" / "kis-mcp.policy.json").write_text('{"rule":"v1"}\n', encoding="utf-8")
    (root / "settings" / "kis-mcp.settings.json").write_text('{"runtime":"v1"}\n', encoding="utf-8")
    (root / "source.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True)
    return root


def _contract(port: int = 46010) -> TaskHandoffContract:
    return TaskHandoffContract(
        project_id="kis-mcp", work_id="WORK-587", repository="NielPieterse0/kis-mcp",
        requirements=("implement",), acceptance_criteria=("passes",),
        affected_surfaces=("candidate_identity",), obligations=("review_closed",),
        candidate_port=port, source_identity="github-issue:NielPieterse0/kis-mcp#587",
        change_id="610-review-candidate-identity",
    )


def test_candidate_binding_captures_source_policy_runtime_and_endpoint(tmp_path: Path) -> None:
    root = _git_repo(tmp_path / "repo")
    first = candidate_binding(root, 46010)

    assert len(first["source_commit"]) == 40
    assert len(first["source_tree"]) == 40
    assert len(first["policy_fingerprint"]) == 64
    assert len(first["runtime_fingerprint"]) == 64
    assert first["endpoint"] == "http://127.0.0.1:46010/mcp"

    (root / "policy" / "kis-mcp.policy.json").write_text('{"rule":"v2"}\n', encoding="utf-8")
    second = candidate_binding(root, 46010)
    assert second["source_commit"] == first["source_commit"]
    assert second["policy_fingerprint"] != first["policy_fingerprint"]

    (root / "source.txt").write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "add", "source.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "source drift"], cwd=root, check=True, capture_output=True)
    third = candidate_binding(root, 46010)
    assert third["source_commit"] != first["source_commit"]
    assert third["source_tree"] != first["source_tree"]


def test_exact_candidate_match_rejects_source_or_policy_drift(tmp_path: Path) -> None:
    binding = candidate_binding(_git_repo(tmp_path / "repo"), 46010)
    contract = _contract()
    receipt = {
        "identity_schema_version": 2,
        "work_id": contract.work_id,
        "contract_fingerprint": contract.contract_fingerprint,
        "source_identity": contract.source_identity,
        "source_path": str((tmp_path / "repo").resolve()),
        "change_id": contract.change_id,
        "server_instance_id": "instance-1",
        "pid": 1234,
        **binding,
    }
    identity = dict(receipt)
    assert _candidate_matches(contract, receipt, identity)
    assert not _candidate_matches(contract, receipt, {**identity, "source_tree": "f" * 40})
    assert not _candidate_matches(contract, receipt, {**identity, "policy_fingerprint": "e" * 64})


def test_review_closure_emits_validated_evidence_when_material_findings_are_closed() -> None:
    execution = {
        "source_fingerprint": "a" * 64,
        "reviews": [
            {"step_id": "code-quality", "status": "completed", "payload": {"findings": []}},
            {"step_id": "architecture", "status": "completed", "payload": {"findings": []}},
        ],
    }
    closure = closure_from_execution(
        execution, subject="tree:abc", tree="b" * 40,
        receipt_ref="execution-receipt:123", closed_findings=("F-1",),
        correction_scope=("src/a.py",),
    )
    evidence = closure.to_evidence()
    assert closure.reviewed_domains == ("code-quality", "architecture")
    assert closure.closed_findings == ("F-1",)
    assert evidence.kind == "review_closed"
    assert evidence.validity_inputs == {"tree": "b" * 40}


def test_review_closure_fails_with_open_material_finding() -> None:
    execution = {
        "source_fingerprint": "a" * 64,
        "reviews": [{
            "step_id": "code-quality", "status": "completed",
            "payload": {"findings": [{"id": "F-1", "severity": "high"}]},
        }],
    }
    with pytest.raises(ValueError, match="REVIEW_NOT_CLOSED"):
        closure_from_execution(
            execution, subject="tree:abc", tree="b" * 40,
            receipt_ref="execution-receipt:123",
        )


def test_correction_re_review_is_limited_to_directly_affected_domains() -> None:
    reviews = [
        {"step_id": "code-quality", "payload": {"findings": [
            {"severity": "medium", "affected_paths": ["src/a.py"]},
        ]}},
        {"step_id": "architecture", "payload": {"findings": [
            {"severity": "high", "affected_paths": ["src/b.py"]},
        ]}},
    ]
    assert targeted_review_domains(reviews, ["src/a.py"]) == ("code-quality",)


def test_scenario_selection_is_deterministic_and_effect_aware() -> None:
    schemas = {
        "candidate_identity": {"required": [], "read_only": True},
        "status_tool": {"required": [], "read_only": True},
        "change_tool": {"required": ["value"], "read_only": False},
    }
    first = select_live_verification_scenarios(("status_tool", "change_tool"), schemas)
    second = select_live_verification_scenarios(("change_tool", "status_tool"), schemas)
    assert first == second
    assert first[0] == {"tool": "candidate_identity", "arguments": {}}
    assert {item["tool"] for item in first} == {"candidate_identity", "status_tool", "change_tool"}
    effect = next(item for item in first if item["tool"] == "change_tool")
    assert effect["expect_error"] is True
    assert effect["negative_path"] == "effect_boundary"
