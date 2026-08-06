from __future__ import annotations

import json
from pathlib import Path

import pytest

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
    assert len(settings.skill_metadata) == 17
    assert all(item.category != "uncategorized" for item in settings.skill_metadata.values())
    assert all(item.capabilities for item in settings.skill_metadata.values())
    assert "search_capabilities" in settings.discovery_operations
    assert "describe_capability" in settings.discovery_operations
    assert "recommend_workflow" in settings.discovery_operations


def test_settings_reject_unknown_top_level_fields(tmp_path: Path) -> None:
    source = Path("settings/capabilities.settings.json")
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CapabilitySettingsError, match="unknown fields"):
        load_capability_settings(path)
