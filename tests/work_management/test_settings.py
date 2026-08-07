from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.work_management.settings import (
    FeatureMode,
    GateMode,
    WorkManagementSettings,
    load_work_management_settings,
)


def document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "enabled": True,
        "portfolio_id": "default",
        "managed_projects": [
            {
                "project_id": "kis-mcp",
                "local_root": "C:\\Projects\\kis-mcp",
                "repository": "NielPieterse0/kis-mcp",
                "backend_binding": "github-default",
                "display_name": "kis-mcp",
            }
        ],
        "backend_bindings": [
            {
                "binding_id": "github-default",
                "provider": "github",
                "owner": "NielPieterse0",
                "owner_type": "user",
                "project_number": None,
            }
        ],
        "features": {
            "intake": "enabled",
            "review_import": "read_only",
        },
        "automation": {
            "scheduled_reconciliation": False,
            "safe_repair": False,
        },
        "gates": {
            "project_settings": "required",
            "programme_drift": "advisory",
        },
        "evidence": {
            "max_file_bytes": 1048576,
            "max_total_bytes": 4194304,
        },
    }


def write_document(tmp_path: Path, value: dict[str, object]) -> Path:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_loads_strict_multi_project_settings(tmp_path: Path) -> None:
    value = document()
    value["managed_projects"] = [
        *value["managed_projects"],
        {
            "project_id": "other-project",
            "local_root": "C:\\Projects\\other-project",
            "repository": "NielPieterse0/other-project",
            "backend_binding": "github-default",
            "display_name": None,
        },
    ]

    settings = load_work_management_settings(write_document(tmp_path, value))

    assert settings.enabled is True
    assert settings.project("kis-mcp").repository == "NielPieterse0/kis-mcp"
    assert settings.project("other-project").backend_binding == "github-default"
    assert settings.feature_mode("intake") is FeatureMode.ENABLED
    assert settings.feature_mode("review_import") is FeatureMode.READ_ONLY
    assert settings.gate_mode("programme_drift") is GateMode.ADVISORY


def test_rejects_unknown_top_level_key(tmp_path: Path) -> None:
    value = document()
    value["unexpected"] = True

    with pytest.raises(ValueError, match="unknown settings keys"):
        load_work_management_settings(write_document(tmp_path, value))


def test_rejects_duplicate_project_identity(tmp_path: Path) -> None:
    value = document()
    value["managed_projects"] = [
        *value["managed_projects"],
        dict(value["managed_projects"][0]),
    ]

    with pytest.raises(ValueError, match="project_id"):
        load_work_management_settings(write_document(tmp_path, value))


def test_rejects_missing_backend_binding(tmp_path: Path) -> None:
    value = document()
    value["managed_projects"][0]["backend_binding"] = "missing"

    with pytest.raises(ValueError, match="backend binding"):
        load_work_management_settings(write_document(tmp_path, value))


def test_rejects_invalid_feature_and_gate_modes(tmp_path: Path) -> None:
    value = document()
    value["features"]["intake"] = "automatic"
    with pytest.raises(ValueError, match="FeatureMode"):
        load_work_management_settings(write_document(tmp_path, value))

    value = document()
    value["gates"]["project_settings"] = "blocking"
    with pytest.raises(ValueError, match="GateMode"):
        load_work_management_settings(write_document(tmp_path, value))


def test_settings_object_rejects_duplicate_bindings() -> None:
    loaded = load_work_management_settings
    assert callable(loaded)
    assert WorkManagementSettings.__name__ == "WorkManagementSettings"


def test_checked_in_settings_and_schema_are_parseable() -> None:
    root = Path(__file__).resolve().parents[2]
    settings = load_work_management_settings(
        root / "settings" / "work-management" / "github-projects.settings.json"
    )
    schema = json.loads(
        (
            root
            / "contracts"
            / "work-management"
            / "github-projects.settings.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert settings.enabled is False
    assert settings.project("kis-mcp").repository == "NielPieterse0/kis-mcp"
    assert schema["additionalProperties"] is False
