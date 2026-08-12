from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.govern.settings import GovernanceSettings

ROOT = Path(__file__).resolve().parents[2]


def test_checked_in_governance_settings_are_strict_and_advisory() -> None:
    settings = GovernanceSettings.load(ROOT / "settings" / "governance.settings.json")
    schema = json.loads((ROOT / "contracts" / "governance" / "settings.schema.json").read_text(encoding="utf-8"))

    assert settings.enabled is True
    assert settings.max_findings == 100
    assert "current-implementation-drift" in settings.enabled_rules
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]["enabled_rules"]["items"]["enum"]) == set(settings.enabled_rules)


def test_settings_reject_unknown_rule(tmp_path: Path) -> None:
    data = json.loads((ROOT / "settings" / "governance.settings.json").read_text(encoding="utf-8"))
    data["enabled_rules"].append("block-work")
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported"):
        GovernanceSettings.load(path)
