from __future__ import annotations

from pathlib import Path

from kis_mcp.projects import load_project_registry_settings
from kis_mcp.work_management.settings import FeatureMode, load_work_management_settings


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "settings" / "projects.settings.json"
WORK_SETTINGS = ROOT / "settings" / "work-management" / "github-projects.settings.json"


def test_kis_mcp_github_project_is_commissioned_for_supervised_reconciliation() -> None:
    registry = load_project_registry_settings(REGISTRY, boundary="C:\\Projects")
    settings = load_work_management_settings(WORK_SETTINGS)

    registered = registry.project("kis-mcp")
    assert registered.github is not None
    assert registered.github.repository == "nielpieterse0/kis-mcp"
    assert len(registered.github.projects) == 1
    project = registered.github.projects[0]
    assert (project.binding_id, project.owner, project.owner_type, project.project_number) == (
        "work-management",
        "NielPieterse0",
        "user",
        1,
    )

    managed = settings.project("kis-mcp")
    binding = settings.binding(managed.backend_binding)
    assert managed.backend_binding == "github-default"
    assert binding.provider == "github-mcp"
    assert (binding.owner, binding.owner_type.value, binding.project_number) == (
        "NielPieterse0",
        "user",
        1,
    )

    assert settings.feature_mode("intake") is FeatureMode.READ_ONLY
    assert settings.feature_mode("review_import") is FeatureMode.READ_ONLY
    assert settings.feature_mode("reconciliation") is FeatureMode.ENABLED
    assert settings.feature_mode("programme_status") is FeatureMode.ENABLED
    assert dict(settings.automation) == {
        "auto_add": False,
        "close_sync": False,
        "merge_sync": False,
        "review_extraction": False,
        "safe_repair": False,
        "scheduled_reconciliation": False,
    }
