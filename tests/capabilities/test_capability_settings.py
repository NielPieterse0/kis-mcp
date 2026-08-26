from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.capabilities.settings import (
    CapabilitySettingsError,
    load_capability_settings,
)


def test_default_capability_settings_are_complete() -> None:
    settings = load_capability_settings()

    assert settings.schema_version == 1
    assert sum(settings.suitability_weights.values()) == 100
    assert sum(settings.quality_weights.values()) == 100
    assert len(settings.direct_operations) <= settings.direct_profile_max
    assert len(settings.skill_metadata) == 30
    assert {
        "agentproof",
        "code-verification",
        "code-work",
        "commit-workspace-changes",
        "gh-address-comments",
        "gh-fix-ci",
        "gh-review-comment-triage",
        "github",
        "manage-code-ontology",
        "merge-conflict-resolution",
        "mcp-development",
        "mcpb-local-packaging",
        "openai-mcp-app-ui",
        "openai-mcp-server",
        "take-pr-to-completion",
        "yeet",
    } <= set(settings.skill_metadata)
    assert not {"build-mcp-app", "build-mcpb", "build-mcp-server"} & set(settings.skill_metadata)
    assert all(item.category != "uncategorized" for item in settings.skill_metadata.values())
    assert all(item.capabilities for item in settings.skill_metadata.values())
    assert "search_capabilities" in settings.discovery_operations
    assert "describe_capability" in settings.discovery_operations
    assert "recommend_workflow" in settings.discovery_operations
    assert settings.result_budget.max_chars == 100_000
    assert settings.result_budget.preview_items == 10
    assert settings.result_budget.preview_string_chars == 4_000
    assert settings.result_budget.preview_depth == 4
    assert settings.result_budget.resource_ttl_seconds == 86_400
    assert settings.result_budget.resource_max_entries == 128
    assert settings.result_budget.resource_max_bytes == 5_000_000


def test_settings_reject_unknown_top_level_fields(tmp_path: Path) -> None:
    source = Path("settings/capabilities.settings.json")
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CapabilitySettingsError, match="unknown fields"):
        load_capability_settings(path)



def test_capability_settings_schema_matches_strict_nested_contract() -> None:
    schema = json.loads(
        Path("contracts/capabilities/settings.schema.json").read_text(encoding="utf-8")
    )
    payload = json.loads(
        Path("settings/capabilities.settings.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(payload)) == []

    invalid_direct = json.loads(json.dumps(payload))
    invalid_direct["direct_profile"]["unexpected"] = True
    assert list(validator.iter_errors(invalid_direct))

    invalid_skill = json.loads(json.dumps(payload))
    invalid_skill["skill_metadata"]["modularity-assessment"]["capabilities"] = []
    assert list(validator.iter_errors(invalid_skill))

    invalid_weight = json.loads(json.dumps(payload))
    invalid_weight["suitability_weights"].pop("intent_match")
    assert list(validator.iter_errors(invalid_weight))


def test_legacy_four_field_result_budget_uses_resource_defaults(tmp_path: Path) -> None:
    payload = json.loads(
        Path("settings/capabilities.settings.json").read_text(encoding="utf-8")
    )
    for key in (
        "resource_ttl_seconds",
        "resource_max_entries",
        "resource_max_bytes",
    ):
        payload["result_budget"].pop(key)
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    settings = load_capability_settings(path)

    assert settings.result_budget.resource_ttl_seconds == 86_400
    assert settings.result_budget.resource_max_entries == 128
    assert settings.result_budget.resource_max_bytes == 5_000_000


def test_settings_reject_invalid_result_resource_bounds(tmp_path: Path) -> None:
    payload = json.loads(
        Path("settings/capabilities.settings.json").read_text(encoding="utf-8")
    )
    payload["result_budget"]["resource_ttl_seconds"] = 0
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CapabilitySettingsError, match="resource_ttl_seconds"):
        load_capability_settings(path)


def test_settings_reject_incomplete_skill_metadata(tmp_path: Path) -> None:
    payload = json.loads(
        Path("settings/capabilities.settings.json").read_text(encoding="utf-8")
    )
    payload["skill_metadata"]["modularity-assessment"]["activation_terms"] = []
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CapabilitySettingsError, match="activation_terms must not be empty"):
        load_capability_settings(path)
