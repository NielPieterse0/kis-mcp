from __future__ import annotations

from pathlib import Path

from kis_mcp.projects import load_project_registry_settings
from kis_mcp.work_management.settings import FeatureMode, load_work_management_settings


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "settings" / "projects.settings.json"
WORK_SETTINGS = ROOT / "settings" / "work-management" / "github-projects.settings.json"


def test_shared_github_project_is_commissioned_for_managed_repositories() -> None:
    registry = load_project_registry_settings(REGISTRY, boundary="C:\\Projects")
    settings = load_work_management_settings(WORK_SETTINGS, project_registry=registry)
    expected_repositories = {
        "chatgpt-skill": "nielpieterse0/chatgpt-skill",
        "college": "nielpieterse0/college",
        "commodity": "nielpieterse0/commodity",
        "kis-mcp": "nielpieterse0/kis-mcp",
        "kis-mcp-doc": "nielpieterse0/kis-mcp-doc",
    }

    for project_id, repository in expected_repositories.items():
        registered = registry.project(project_id)
        assert registered.github is not None
        assert registered.github.repository == repository
        managed = settings.project(project_id)
        assert managed.backend_binding == "github-default"
        assert managed.repository.casefold() == repository

    project = registry.project("kis-mcp").github.projects[0]
    assert (project.binding_id, project.owner, project.owner_type, project.project_number) == (
        "work-management", "NielPieterse0", "user", 1
    )
    assert all(
        not registry.project(project_id).github.projects
        for project_id in ("chatgpt-skill", "college", "commodity", "kis-mcp-doc")
    )
    doc_registered = registry.project("kis-mcp-doc")
    doc_managed = settings.project("kis-mcp-doc")
    assert doc_managed.local_root == doc_registered.local_root
    assert doc_managed.repository == doc_registered.github.repository
    assert doc_managed.backend_binding == "github-default"

    binding = settings.binding("github-default")
    assert binding.provider == "github-mcp"
    assert (binding.owner, binding.owner_type.value, binding.project_number) == (
        "NielPieterse0", "user", 1
    )

    assert settings.feature_mode("intake") is FeatureMode.READ_ONLY
    assert settings.feature_mode("review_import") is FeatureMode.READ_ONLY
    assert settings.feature_mode("reconciliation") is FeatureMode.ENABLED
    assert settings.feature_mode("programme_status") is FeatureMode.ENABLED
    assert not hasattr(settings, "automation")
