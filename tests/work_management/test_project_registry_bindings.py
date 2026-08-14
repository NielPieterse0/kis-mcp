from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.projects import load_project_registry_settings
from kis_mcp.work_management.settings import load_work_management_settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = (
    REPOSITORY_ROOT / "settings" / "work-management" / "github-projects.settings.json"
)
REGISTRY_PATH = REPOSITORY_ROOT / "settings" / "projects.settings.json"


def _registry():
    return load_project_registry_settings(REGISTRY_PATH, boundary="C:\\Projects")


def test_registry_bridge_preserves_behavior_and_existing_binding_ids() -> None:
    baseline = load_work_management_settings(SETTINGS_PATH)
    bridged = load_work_management_settings(
        SETTINGS_PATH,
        project_registry=_registry(),
    )

    assert bridged.features == baseline.features
    assert bridged.automation == baseline.automation
    assert bridged.gates == baseline.gates
    assert bridged.evidence == baseline.evidence
    assert bridged.enabled == baseline.enabled
    assert bridged.portfolio_id == baseline.portfolio_id

    project = bridged.project("kis-mcp")
    binding = bridged.binding(project.backend_binding)
    assert project.backend_binding == "github-default"
    assert project.local_root == "C:\\Projects\\kis-mcp"
    assert project.repository == "nielpieterse0/kis-mcp"
    assert binding.binding_id == "github-default"
    assert binding.provider == "github-mcp"
    assert binding.owner == "NielPieterse0"
    assert binding.owner_type.value == "user"
    assert binding.project_number == 1


def test_registry_bridge_enrolls_every_registered_project_on_shared_backend() -> None:
    registry = _registry()
    bridged = load_work_management_settings(
        SETTINGS_PATH,
        project_registry=registry,
    )

    assert {project.project_id for project in bridged.managed_projects} == {
        project.project_id for project in registry.projects
    }
    for registered in registry.projects:
        managed = bridged.project(registered.project_id)
        expected_repository = (
            registered.github.repository if registered.github is not None else None
        )
        assert managed.local_root == registered.local_root
        assert managed.display_name == registered.display_name
        assert managed.repository == expected_repository
        assert managed.backend_binding == "github-default"


def test_registry_bridge_rejects_implicit_enrollment_when_backend_is_ambiguous(
    tmp_path: Path,
) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document["backend_bindings"].append(
        {
            "binding_id": "secondary",
            "provider": "github-mcp",
            "owner": "NielPieterse0",
            "owner_type": "user",
            "project_number": 2,
        }
    )
    path = tmp_path / "work-management.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="ambiguous for automatic project enrollment"):
        load_work_management_settings(path, project_registry=_registry())


def test_registry_bridge_overlays_backend_coordinates_without_changing_modes(
    tmp_path: Path,
) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    binding = document["backend_bindings"][0]
    binding["owner"] = "stale-owner"
    binding["owner_type"] = "org"
    binding["project_number"] = 999
    path = tmp_path / "work-management.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    bridged = load_work_management_settings(path, project_registry=_registry())

    resolved = bridged.binding("github-default")
    assert resolved.owner == "NielPieterse0"
    assert resolved.owner_type.value == "user"
    assert resolved.project_number == 1
    assert bridged.feature_mode("programme_status").value == "enabled"
    assert bridged.gate_mode("verification_evidence").value == "required"
    assert bridged.evidence.max_total_bytes == 4_194_304


def test_registry_bridge_rejects_ambiguous_project_coordinates(tmp_path: Path) -> None:
    registry_document = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    kis = next(
        item
        for item in registry_document["projects"]
        if item["project_id"] == "kis-mcp"
    )
    kis["github"]["projects"] = [
        {
            "binding_id": "delivery",
            "owner": "NielPieterse0",
            "owner_type": "user",
            "project_number": 1,
        },
        {
            "binding_id": "planning",
            "owner": "NielPieterse0",
            "owner_type": "user",
            "project_number": 2,
        },
    ]
    registry_path = tmp_path / "projects.settings.json"
    registry_path.write_text(json.dumps(registry_document), encoding="utf-8")
    registry = load_project_registry_settings(registry_path, boundary="C:\\Projects")

    with pytest.raises(ValueError, match="ambiguous work-management binding"):
        load_work_management_settings(SETTINGS_PATH, project_registry=registry)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("local_root", "C:\\Projects\\different"),
        ("repository", "NielPieterse0/different"),
    ],
)
def test_registry_bridge_fails_closed_on_managed_project_identity_conflict(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document["managed_projects"][0][field] = value
    path = tmp_path / "work-management.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="conflicts with project registry"):
        load_work_management_settings(path, project_registry=_registry())
