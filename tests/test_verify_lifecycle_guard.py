from __future__ import annotations

import json
import subprocess
from pathlib import Path

SHA = "a" * 40
TREE = "b" * 40


def _promotion(root: Path) -> Path:
    promotions = root / "promotions"
    promotions.mkdir(parents=True)
    path = promotions / "WORK-650.json"
    path.write_text(json.dumps({
        "schema_version": 2,
        "status": "promotion_ready",
        "work_id": "WORK-650",
        "change_id": "621-lifecycle-decision-auto-recovery",
        "source_commit_sha": SHA,
        "evidence": [
            {"evidence_id": "verification", "kind": "verification", "validity_inputs": {"tree": TREE}},
            {"evidence_id": "review_closed", "kind": "review_closed", "validity_inputs": {"tree": TREE}},
        ],
        "pending_obligations": [],
    }), encoding="utf-8")
    return path


def _run(script: Path, state: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([        "pwsh.exe", "-NoProfile", "-File", str(script),
        "-ChangeId", "621-lifecycle-decision-auto-recovery",
        "-SourceSha", SHA,
        "-SourceTree", TREE,
        "-StateRoot", str(state),
        *extra,
    ], capture_output=True, text=True, timeout=30, check=False)


def test_promotion_ready_blocks_redundant_local_canonical_verify(tmp_path: Path) -> None:
    state = tmp_path / "once-through"
    promotion = _promotion(state)
    script = Path(__file__).parents[1] / "scripts" / "verify-lifecycle-guard.ps1"
    result = _run(script, state)
    assert result.returncode == 23
    payload = json.loads(result.stdout.strip())
    assert payload["code"] == "REDUNDANT_VERIFICATION"
    assert payload["disposition"] == "redundant"
    assert payload["lifecycle_blocked"] is False
    assert payload["next_required_action"] == "converge_change_to_done"
    assert payload["canonical_owner"] == "github_actions_exact_pr_head"
    assert Path(payload["promotion_receipt"]) == promotion
    events = list((state / "lifecycle-telemetry").glob("*.json"))
    assert len(events) == 1
    assert json.loads(events[0].read_text(encoding="utf-8"))["event"] == "redundant_operation_prevented"


def test_diagnostic_override_is_allowed_and_audited(tmp_path: Path) -> None:
    state = tmp_path / "once-through"
    _promotion(state)
    script = Path(__file__).parents[1] / "scripts" / "verify-lifecycle-guard.ps1"
    result = _run(script, state, "-DiagnosticOverride")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())
    assert payload["disposition"] == "diagnostic_only"
    assert payload["diagnostic_override"] is True
    events = list((state / "lifecycle-telemetry").glob("*.json"))
    assert len(events) == 1
    assert json.loads(events[0].read_text(encoding="utf-8"))["event"] == "diagnostic_override_used"


def test_changed_source_does_not_claim_promotion_ready(tmp_path: Path) -> None:
    state = tmp_path / "once-through"
    _promotion(state)
    script = Path(__file__).parents[1] / "scripts" / "verify-lifecycle-guard.ps1"
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(script),
        "-ChangeId", "621-lifecycle-decision-auto-recovery",
        "-SourceSha", "c" * 40,
        "-SourceTree", TREE,
        "-StateRoot", str(state),
    ], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip())["disposition"] == "allowed"


def test_missing_tree_binding_does_not_suppress_verification(tmp_path: Path) -> None:
    state = tmp_path / "once-through"
    path = _promotion(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evidence"][1]["validity_inputs"] = {}
    path.write_text(json.dumps(payload), encoding="utf-8")
    script = Path(__file__).parents[1] / "scripts" / "verify-lifecycle-guard.ps1"
    result = _run(script, state)
    assert result.returncode == 0, result.stderr
    guarded = json.loads(result.stdout.strip())
    assert guarded["disposition"] == "allowed"
    assert guarded["reason"] == "PROMOTION_EVIDENCE_STALE"


def test_missing_required_tree_evidence_does_not_suppress_verification(tmp_path: Path) -> None:
    state = tmp_path / "once-through"
    path = _promotion(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evidence"] = payload["evidence"][:1]
    path.write_text(json.dumps(payload), encoding="utf-8")
    script = Path(__file__).parents[1] / "scripts" / "verify-lifecycle-guard.ps1"
    result = _run(script, state)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip())["reason"] == "PROMOTION_EVIDENCE_STALE"
