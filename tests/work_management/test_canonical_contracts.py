from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from kis_mcp.work_management.canonical_contracts import (
    load_canonical_work_contracts,
    validate_runtime_vocabulary,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_PATH = REPOSITORY_ROOT / "settings" / "work-management" / "contracts"


def test_canonical_contracts_load_complete_work_semantics() -> None:
    contracts = load_canonical_work_contracts(CONTRACTS_PATH)

    assert contracts.work_item.schema_version == 1
    assert contracts.lifecycle.schema_version == 1
    assert contracts.selection.schema_version == 1
    assert len(contracts.work_item.managed_fields) == 28
    assert contracts.work_item.managed_fields[-3:] == (
        "Live Verification",
        "Commissioning Key",
        "Live Verification Evidence",
    )

def test_canonical_vocabularies_preserve_current_tokens_and_meaning() -> None:
    contracts = load_canonical_work_contracts(CONTRACTS_PATH)

    assert contracts.work_item.vocabulary_tokens("status") == (
        "inbox", "triage", "proposed", "approved", "ready", "active",
        "blocked", "on_hold", "deferred", "rejected", "superseded", "done",
    )
    assert contracts.work_item.vocabulary_tokens("priority") == (
        "critical", "high", "medium", "low",
    )
    assert contracts.work_item.vocabulary_tokens("effort") == (
        "tiny", "small", "medium", "large",
    )
    confidence = contracts.work_item.vocabulary("confidence")
    meanings = {item.token: item.definition for item in confidence.values}
    assert set(meanings) == {"high", "medium", "low"}
    assert len(set(meanings.values())) == 3
    assert all(meanings.values())


def test_selection_contract_preserves_current_policy_without_withdrawn_tiers() -> None:
    contracts = load_canonical_work_contracts(CONTRACTS_PATH)
    selection = contracts.selection

    assert selection.eligible_states == ("ready",)
    assert selection.priority_order == ("critical", "high", "medium", "low")
    assert selection.effort_order == ("tiny", "small", "medium", "large")
    assert selection.ranking == ("priority", "effort", "created_order", "record_id")
    serialized = json.dumps(selection.to_json_dict(), sort_keys=True).casefold()
    assert "work_class" not in serialized
    assert "selection_tier" not in serialized
    assert "material_finding" not in serialized

def test_contract_fingerprints_are_stable_sha256_values() -> None:
    first = load_canonical_work_contracts(CONTRACTS_PATH)
    second = load_canonical_work_contracts(CONTRACTS_PATH)

    assert first.fingerprints == second.fingerprints
    assert set(first.fingerprints) == {
        "work_item_semantics", "work_lifecycle_operations", "work_selection"
    }
    assert all(len(value) == 64 for value in first.fingerprints.values())


def test_contract_loader_rejects_unknown_top_level_keys(tmp_path: Path) -> None:
    candidate = tmp_path / "contracts"
    shutil.copytree(CONTRACTS_PATH, candidate)
    path = candidate / "work-selection.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["unexpected"] = True
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="work selection keys"):
        load_canonical_work_contracts(candidate)


def test_contract_loader_rejects_unknown_field_references(tmp_path: Path) -> None:
    candidate = tmp_path / "contracts"
    shutil.copytree(CONTRACTS_PATH, candidate)
    path = candidate / "work-selection.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["fields"]["priority"] = "Unknown Priority"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown canonical field"):
        load_canonical_work_contracts(candidate)

def test_runtime_enum_vocabulary_is_an_exact_canonical_projection() -> None:
    contracts = load_canonical_work_contracts(CONTRACTS_PATH)
    validate_runtime_vocabulary(contracts)


def test_live_verification_is_distinct_from_source_verification() -> None:
    contracts = load_canonical_work_contracts(CONTRACTS_PATH)

    verification = contracts.work_item.field("Verification")
    live = contracts.work_item.field("Live Verification")
    assert verification.vocabulary == "verification"
    assert live.vocabulary == "live_verification"
    assert contracts.work_item.vocabulary_tokens("verification") == (
        "not_run", "pending", "passed", "failed", "blocked"
    )
    assert contracts.work_item.vocabulary_tokens("live_verification") == (
        "not_assessed", "not_required", "pending", "passed", "failed", "blocked"
    )


def test_selection_profiles_preserve_adapter_reason_order() -> None:
    selection = load_canonical_work_contracts(CONTRACTS_PATH).selection

    assert selection.profile("provider_project").rules == (
        "source_issue", "source_open", "eligible_state", "valid_priority",
        "valid_effort", "required_fields", "unclaimed", "dependency_evidence",
        "dependencies_clear",
    )
    assert selection.profile("normalized_domain").rules == (
        "project_match", "eligible_state", "unclaimed", "approval_complete",
        "dependencies_clear",
    )
    assert selection.profile("normalized_domain").reason("eligible_state") == "state_not_executable"
    assert selection.profile("provider_project").reason("eligible_state") == "state_not_ready"
