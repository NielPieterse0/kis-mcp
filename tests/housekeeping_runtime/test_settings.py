from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from kis_mcp.housekeeping_runtime.settings import (
    HousekeepingRuntimeSettingsError,
    load_housekeeping_runtime_settings,
)
from kis_mcp.work_management.settings import load_work_management_settings


def _document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "enabled": True,
        "host_instance": "kis-op",
        "state_namespace": "housekeeping",
        "receipt_retention": 120,
        "freshness_stale_after_seconds": 5400,
        "apply_max_age_seconds": 1800,
        "scheduled_mode": "preview",
        "targets": [
            {
                "runner": "work-management-reconciliation",
                "project_id": "kis-mcp",
                "repository": "NielPieterse0/kis-mcp",
                "repository_root": "C:\\Projects\\kis-mcp",
                "interval_seconds": 1800,
                "initial_delay_seconds": 15,
                "item_limit": 1000,
                "max_findings": 200,
                "max_mutations": 20,
                "max_external_reads": 100,
            },
            {
                "runner": "backlog-readiness",
                "project_id": "kis-mcp",
                "repository": "NielPieterse0/kis-mcp",
                "repository_root": "C:\\Projects\\kis-mcp",
                "interval_seconds": 1800,
                "initial_delay_seconds": 45,
                "item_limit": 1000,
                "max_findings": 200,
                "max_mutations": 20,
                "max_external_reads": 100,
            },
        ],
    }


def _write(tmp_path: Path, document: dict[str, object]) -> Path:
    path = tmp_path / "housekeeping.settings.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_valid_settings_load_and_normalize_targets(tmp_path: Path) -> None:
    settings = load_housekeeping_runtime_settings(_write(tmp_path, _document()))

    assert settings.enabled is True
    assert settings.host_instance == "kis-op"
    assert settings.scheduled_mode == "preview"
    assert [item.runner.value for item in settings.targets] == [
        "backlog_readiness",
        "work_management_reconciliation",
    ]
    assert settings.target("work-management-reconciliation").interval_seconds == 1800


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("host_instance", "kis-dev", "host_instance must be kis-op"),
        ("scheduled_mode", "apply", "scheduled_mode must be preview"),
        ("receipt_retention", 0, "receipt_retention"),
        ("freshness_stale_after_seconds", 30, "freshness_stale_after_seconds"),
        ("apply_max_age_seconds", 0, "apply_max_age_seconds"),
    ],
)
def test_invalid_root_policy_is_rejected(
    tmp_path: Path, key: str, value: object, message: str
) -> None:
    document = _document()
    document[key] = value
    with pytest.raises(HousekeepingRuntimeSettingsError, match=message):
        load_housekeeping_runtime_settings(_write(tmp_path, document))


def test_duplicate_runner_target_is_rejected(tmp_path: Path) -> None:
    document = _document()
    targets = document["targets"]
    assert isinstance(targets, list)
    targets.append(deepcopy(targets[0]))

    with pytest.raises(HousekeepingRuntimeSettingsError, match="duplicate runner"):
        load_housekeeping_runtime_settings(_write(tmp_path, document))


def test_interval_and_repository_boundary_are_bounded(tmp_path: Path) -> None:
    document = _document()
    targets = document["targets"]
    assert isinstance(targets, list)
    first = targets[0]
    assert isinstance(first, dict)
    first["interval_seconds"] = 30
    with pytest.raises(HousekeepingRuntimeSettingsError, match="interval_seconds"):
        load_housekeeping_runtime_settings(_write(tmp_path, document))

    document = _document()
    targets = document["targets"]
    assert isinstance(targets, list)
    first = targets[0]
    assert isinstance(first, dict)
    first["repository_root"] = "D:\\outside"
    with pytest.raises(HousekeepingRuntimeSettingsError, match="repository_root"):
        load_housekeeping_runtime_settings(_write(tmp_path, document))


def test_checked_in_scheduler_is_independent_of_legacy_work_management_automation() -> None:
    housekeeping = load_housekeeping_runtime_settings()
    work_management = load_work_management_settings()

    assert housekeeping.enabled is True
    assert work_management.automation_enabled("scheduled_reconciliation") is False
    assert {target.runner.value for target in housekeeping.targets} == {
        "work_management_reconciliation",
        "backlog_readiness",
    }


def test_housekeeping_settings_participate_in_runtime_generation() -> None:
    from kis_mcp.gateway import foundation

    generation = dict(foundation._runtime_config_generation())
    assert "settings/housekeeping.settings.json" in generation
    assert generation["settings/housekeeping.settings.json"] != "missing"


def test_apply_age_and_health_freshness_are_independent(tmp_path: Path) -> None:
    document = _document()
    document["freshness_stale_after_seconds"] = 300
    document["apply_max_age_seconds"] = 600

    settings = load_housekeeping_runtime_settings(_write(tmp_path, document))
    assert settings.freshness_stale_after_seconds == 300
    assert settings.apply_max_age_seconds == 600
