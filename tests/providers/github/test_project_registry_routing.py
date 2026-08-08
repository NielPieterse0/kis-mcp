from __future__ import annotations

from pathlib import Path

import pytest

from kis_mcp.projects import load_project_registry_settings
from kis_mcp.providers.github.routing import GitHubRepositoryRouting
from kis_mcp.providers.github.scope import GitHubRepositoryScopeError
from kis_mcp.repositories.settings import SelectedRepositorySettings


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPOSITORY_ROOT / "settings" / "projects.settings.json"


def _routing() -> GitHubRepositoryRouting:
    registry = load_project_registry_settings(REGISTRY_PATH, boundary="C:\\Projects")
    selected = SelectedRepositorySettings(
        registry=registry,
        boundary=Path("C:\\Projects"),
        validate_remote=False,
    )
    return GitHubRepositoryRouting(selected.current)


def test_registered_repository_union_is_authorized_without_active_project_switch() -> None:
    routing = _routing()

    routing.authorize("get_file_contents", {"owner": "NielPieterse0", "repo": "kis-mcp"})
    routing.authorize("get_file_contents", {"owner": "NielPieterse0", "repo": "gpt-os"})

    routing.authorize(
        "projects_get",
        {
            "method": "get_project",
            "owner": "NielPieterse0",
            "owner_type": "user",
            "project_number": 1,
        },
    )


def test_unregistered_repository_and_project_are_rejected() -> None:
    routing = _routing()

    with pytest.raises(GitHubRepositoryScopeError, match="not approved"):
        routing.authorize("get_file_contents", {"owner": "NielPieterse0", "repo": "unknown"})

    with pytest.raises(GitHubRepositoryScopeError, match="not explicitly approved"):
        routing.authorize(
            "projects_get",
            {
                "method": "get_project",
                "owner": "NielPieterse0",
                "owner_type": "user",
                "project_number": 999,
            },
        )
