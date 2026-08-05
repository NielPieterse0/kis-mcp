from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.control_center.settings import (
    ControlCenterSettingsError,
    load_control_center_settings,
)


def _document(tmp_path: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "project_path": str(tmp_path / "project"),
        "runtime_settings_path": str(tmp_path / "runtime.json"),
        "policy_path": str(tmp_path / "policy.json"),
        "provider_settings_path": str(tmp_path / "providers.json"),
        "approval_register_path": str(tmp_path / "approvals.md"),
        "quarantine_root": str(tmp_path / "quarantine"),
        "verification_command": [
            "pwsh",
            "-NoProfile",
            "-File",
            "scripts/verify.ps1",
        ],
        "discover_enabled": True,
        "limits": {
            "max_provider_entries": 20,
            "max_approval_entries": 20,
            "max_recent_calls": 50,
            "max_policy_decisions": 50,
            "max_active_processes": 50,
            "max_active_searches": 50,
            "max_discover_findings": 20,
            "max_quarantine_records": 20,
            "git_timeout_seconds": 3,
            "max_json_bytes": 1000000,
        },
    }


def test_load_settings_accepts_strict_document(tmp_path: Path) -> None:
    path = tmp_path / "control-center.settings.json"
    path.write_text(json.dumps(_document(tmp_path)), encoding="utf-8")

    settings = load_control_center_settings(path)

    assert settings.schema_version == 1
    assert settings.project_path == tmp_path / "project"
    assert settings.runtime_settings_path == tmp_path / "runtime.json"
    assert settings.policy_path == tmp_path / "policy.json"
    assert settings.provider_settings_path == tmp_path / "providers.json"
    assert settings.approval_register_path == tmp_path / "approvals.md"
    assert settings.quarantine_root == tmp_path / "quarantine"
    assert settings.verification_command[-1] == "scripts/verify.ps1"
    assert settings.discover_enabled is True
    assert settings.max_provider_entries == 20
    assert settings.max_approval_entries == 20
    assert settings.max_recent_calls == 50
    assert settings.max_policy_decisions == 50
    assert settings.max_active_processes == 50
    assert settings.max_active_searches == 50
    assert settings.max_discover_findings == 20
    assert settings.max_quarantine_records == 20
    assert settings.git_timeout_seconds == 3
    assert settings.max_json_bytes == 1000000


def test_load_settings_rejects_unknown_field(tmp_path: Path) -> None:
    document = _document(tmp_path)
    document["unexpected"] = True
    path = tmp_path / "control-center.settings.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ControlCenterSettingsError, match="unknown field"):
        load_control_center_settings(path)


def test_load_settings_rejects_invalid_discover_flag(tmp_path: Path) -> None:
    document = _document(tmp_path)
    document["discover_enabled"] = "yes"
    path = tmp_path / "control-center.settings.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ControlCenterSettingsError, match="discover_enabled"):
        load_control_center_settings(path)


def test_checked_in_settings_match_schema_contract() -> None:
    repository = Path(__file__).resolve().parents[2]
    settings = json.loads(
        (repository / "settings" / "control-center.settings.json").read_text(
            encoding="utf-8"
        )
    )
    schema = json.loads(
        (
            repository
            / "contracts"
            / "control-center"
            / "settings.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert schema["additionalProperties"] is False
    assert set(settings) == set(schema["required"])
    assert settings["schema_version"] == schema["properties"]["schema_version"][
        "const"
    ]
    assert set(settings["limits"]) == set(
        schema["properties"]["limits"]["required"]
    )

    loaded = load_control_center_settings(
        repository / "settings" / "control-center.settings.json"
    )
    assert loaded.project_path == Path(settings["project_path"])
    assert loaded.project_path == Path(r"C:\Projects\kis-mcp")
    assert loaded.approval_register_path == Path(
        r"C:\Projects\kis-mcp\docs\HARD-BLOCK-APPROVAL-REGISTER.md"
    )
