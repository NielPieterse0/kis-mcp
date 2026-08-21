from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.work_management import (
    DeliveryStage,
    Effort,
    FieldAuthority,
    LifecycleState,
    Priority,
    load_command_plane_settings,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = (
    REPOSITORY_ROOT / "settings" / "work-management" / "command-plane.settings.json"
)
PROJECT_SCHEMA_PATH = (
    REPOSITORY_ROOT / "settings" / "work-management" / "github-project-schema.json"
)


def test_command_plane_settings_define_directional_authority_and_queue() -> None:
    settings = load_command_plane_settings(SETTINGS_PATH)
    assert settings.authority("Priority").authority == "work_management"
    assert settings.authority("Priority").direction == "command"
    assert settings.authority("Complexity").authority == "repository_change"
    assert settings.authority("Verification").authority == "actions"
    assert settings.queue.eligible_states == (LifecycleState.READY,)
    assert settings.queue.priority_order == ("critical", "high", "medium", "low")
    assert settings.queue.effort_order == ("tiny", "small", "medium", "large")
    assert settings.claim.auto_expiry is False
    assert settings.intake_state("Todo") is LifecycleState.INBOX
    assert settings.intake_state("ready") is None
    assert settings.required_fields_for_transition(LifecycleState.ON_HOLD) == (
        "Review Trigger",
    )


def test_command_plane_authority_covers_project_and_native_queue_fields() -> None:
    settings = load_command_plane_settings(SETTINGS_PATH)
    project_schema = json.loads(PROJECT_SCHEMA_PATH.read_text(encoding="utf-8"))
    required = {field["name"] for field in project_schema["fields"]}
    required.update({settings.queue.created_field, settings.queue.blocked_by_field})

    declared = {name for name, _authority in settings.field_authority}
    assert required <= declared


def test_project_schema_provisions_dependency_evidence_field() -> None:
    settings = load_command_plane_settings(SETTINGS_PATH)
    project_schema = json.loads(PROJECT_SCHEMA_PATH.read_text(encoding="utf-8"))
    fields = {field["name"]: field for field in project_schema["fields"]}

    assert fields[settings.queue.blocked_by_field] == {
        "name": "Blocked By",
        "type": "text",
        "options": [],
    }


def test_command_plane_settings_match_checked_in_schema() -> None:
    schema_path = (
        REPOSITORY_ROOT
        / "contracts"
        / "work-management"
        / "command-plane.settings.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []


def test_command_plane_settings_allow_missing_intake_aliases_for_compatibility(tmp_path: Path) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    del document["intake_aliases"]
    candidate = tmp_path / "command-plane.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")

    settings = load_command_plane_settings(candidate)
    assert settings.intake_aliases == ()
    assert settings.intake_state("Todo") is None


def test_command_plane_settings_reject_alias_shadowing_declared_state(tmp_path: Path) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document["intake_aliases"]["ready"] = "inbox"
    candidate = tmp_path / "command-plane.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="must not shadow declared work states"):
        load_command_plane_settings(candidate)


def test_command_plane_settings_fail_closed_for_unknown_intake_alias() -> None:
    settings = load_command_plane_settings(SETTINGS_PATH)
    assert settings.intake_state("Tood") is None


def test_command_plane_settings_rejects_unapproved_alias_extension(tmp_path: Path) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document["intake_aliases"]["backlog"] = "inbox"
    candidate = tmp_path / "command-plane.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="intake_aliases drifts from canonical Work contract"):
        load_command_plane_settings(candidate)


def test_command_plane_settings_reject_unknown_ranking_key(tmp_path: Path) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document["queue"]["ranking"] = ["magic"]
    candidate = tmp_path / "command-plane.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="ranking"):
        load_command_plane_settings(candidate)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("readiness", "requires_dependencies_understood"),
        ("completion", "require_no_active_claim_after_close"),
    ],
)
def test_command_plane_settings_reject_non_boolean_flags(
    tmp_path: Path, section: str, field: str
) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document[section][field] = "false"
    candidate = tmp_path / "command-plane.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="boolean"):
        load_command_plane_settings(candidate)


def test_runtime_vocabulary_matches_settings_authority() -> None:
    settings = load_command_plane_settings(SETTINGS_PATH)

    assert tuple(item.value for item in Priority) == settings.queue.priority_order
    assert tuple(item.value for item in Effort) == settings.queue.effort_order
    assert tuple(item.value for item in DeliveryStage) == settings.delivery_stages
    assert set(settings.work_states) == {
        LifecycleState.INBOX,
        LifecycleState.TRIAGE,
        LifecycleState.PROPOSED,
        LifecycleState.APPROVED,
        LifecycleState.READY,
        LifecycleState.ACTIVE,
        LifecycleState.BLOCKED,
        LifecycleState.ON_HOLD,
        LifecycleState.DEFERRED,
        LifecycleState.REJECTED,
        LifecycleState.SUPERSEDED,
        LifecycleState.DONE,
    }


def test_command_plane_projection_rejects_priority_order_drift(tmp_path: Path) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document["queue"]["priority_order"] = ["high", "critical", "medium", "low"]
    candidate = tmp_path / "command-plane.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="queue.priority_order drifts from canonical Work contract"):
        load_command_plane_settings(candidate)


def test_command_plane_projection_rejects_transition_drift(tmp_path: Path) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document["transitions"]["ready"] = ["on_hold"]
    candidate = tmp_path / "command-plane.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="transitions drifts from canonical Work contract"):
        load_command_plane_settings(candidate)


def test_command_plane_projection_requires_canonical_field_authority(tmp_path: Path) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document["field_authority"]["Priority"]["authority"] = "derived"
    candidate = tmp_path / "command-plane.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="field_authority drifts from canonical Work contract"):
        load_command_plane_settings(candidate)


def test_command_plane_projects_live_verification_authority() -> None:
    settings = load_command_plane_settings(SETTINGS_PATH)

    assert settings.authority("Live Verification") == FieldAuthority("derived", "evidence")
    assert settings.authority("Commissioning Key") == FieldAuthority("derived", "evidence")
    assert settings.authority("Live Verification Evidence") == FieldAuthority("derived", "evidence")
