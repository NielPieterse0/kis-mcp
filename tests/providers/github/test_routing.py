from __future__ import annotations

from pathlib import Path

import pytest

from kis_mcp.providers.github.routing import GitHubRepositoryRouting
from kis_mcp.providers.github.scope import GitHubRepositoryScopeError
from kis_mcp.repositories import GitHubProjectBinding, RepositorySettings


def _settings(repository: str, project_number: int) -> RepositorySettings:
    return RepositorySettings(
        repository_root=Path(r"C:\Projects") / repository.split("/")[-1],
        repository_id=repository.split("/")[-1],
        github_repository=repository,
        gh_projects=(
            GitHubProjectBinding(
                binding_id="work-management",
                owner=repository.split("/")[0],
                owner_type="user",
                project_number=project_number,
            ),
        ),
    )


def test_routing_uses_the_current_selected_repository_on_every_call() -> None:
    selected = [_settings("owner/first", 1)]
    routing = GitHubRepositoryRouting(lambda: selected[0])

    routing.authorize("get_file_contents", {"owner": "owner", "repo": "first"})
    with pytest.raises(GitHubRepositoryScopeError):
        routing.authorize("get_file_contents", {"owner": "owner", "repo": "second"})

    selected[0] = _settings("owner/second", 2)

    routing.authorize("get_file_contents", {"owner": "owner", "repo": "second"})
    with pytest.raises(GitHubRepositoryScopeError):
        routing.authorize("get_file_contents", {"owner": "owner", "repo": "first"})


def test_projects_are_loaded_only_from_the_selected_repository() -> None:
    selected = [_settings("owner/first", 1)]
    routing = GitHubRepositoryRouting(lambda: selected[0])

    routing.authorize(
        "projects_get",
        {
            "method": "get_project",
            "owner": "owner",
            "owner_type": "user",
            "project_number": 1,
        },
    )

    selected[0] = _settings("owner/second", 2)

    with pytest.raises(GitHubRepositoryScopeError):
        routing.authorize(
            "projects_get",
            {
                "method": "get_project",
                "owner": "owner",
                "owner_type": "user",
                "project_number": 1,
            },
        )
    routing.authorize(
        "projects_get",
        {
            "method": "get_project",
            "owner": "owner",
            "owner_type": "user",
            "project_number": 2,
        },
    )


def test_health_and_authentication_bootstrap_are_unscoped() -> None:
    routing = GitHubRepositoryRouting(lambda: _settings("owner/repo", 1))

    routing.authorize("get_me", {})
    routing.authorize("kis_github_health", {})
