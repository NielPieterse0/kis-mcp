from __future__ import annotations

import pytest

from kis_mcp.providers.github.scope import (
    GitHubRepositoryScope,
    GitHubRepositoryScopeError,
    normalize_repository,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("NielPieterse0/kis-mcp", "nielpieterse0/kis-mcp"),
        ("NielPieterse0/kis-mcp.git", "nielpieterse0/kis-mcp"),
        ("https://github.com/NielPieterse0/kis-mcp", "nielpieterse0/kis-mcp"),
        ("https://api.github.com/repos/NielPieterse0/kis-mcp", "nielpieterse0/kis-mcp"),
        ("git@github.com:NielPieterse0/kis-mcp.git", "nielpieterse0/kis-mcp"),
    ],
)
def test_normalizes_supported_repository_identities(value: str, expected: str) -> None:
    assert normalize_repository(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "repo-only",
        "owner/repo/extra",
        "https://token@github.com/owner/repo",
        "https://gitlab.com/owner/repo",
        "git@example.com:owner/repo.git",
        "",
    ],
)
def test_rejects_ambiguous_or_credential_bearing_repository_identity(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_repository(value)


def test_allows_approved_owner_repo_and_repository_fields() -> None:
    scope = GitHubRepositoryScope(
        ["NielPieterse0/kis-mcp"],
        ["get_me"],
        [("NielPieterse0", "user", 12)],
    )

    scope.authorize("get_file_contents", {"owner": "NielPieterse0", "repo": "kis-mcp"})
    scope.authorize(
        "get_file_contents",
        {"owner": "NielPieterse0", "repository_name": "kis-mcp"},
    )
    scope.authorize("pull_request_read", {"repository": "NielPieterse0/kis-mcp"})
    scope.authorize("other", {"repo": "NielPieterse0/kis-mcp"})
    scope.authorize("other", {"repo_full_name": "NielPieterse0/kis-mcp"})
    scope.authorize(
        "other",
        {"repository_url": "https://github.com/NielPieterse0/kis-mcp"},
    )


def test_malformed_repository_target_returns_stable_scope_error() -> None:
    scope = GitHubRepositoryScope(
        ["NielPieterse0/kis-mcp"],
        ["get_me"],
        [("NielPieterse0", "user", 12)],
    )

    with pytest.raises(GitHubRepositoryScopeError, match="invalid repository target"):
        scope.authorize("pull_request_read", {"repository": "not-a-repository"})


def test_rejects_any_unapproved_or_conflicting_repository_target() -> None:
    scope = GitHubRepositoryScope(
        ["NielPieterse0/kis-mcp"],
        ["get_me"],
        [("NielPieterse0", "user", 12)],
    )

    with pytest.raises(GitHubRepositoryScopeError, match="other/repo"):
        scope.authorize("get_file_contents", {"owner": "other", "repo": "repo"})

    with pytest.raises(GitHubRepositoryScopeError, match="other/repo"):
        scope.authorize(
            "copy_file",
            {
                "source_repository": "NielPieterse0/kis-mcp",
                "target_repository": "other/repo",
            },
        )


def test_search_requires_explicit_approved_repo_qualifiers() -> None:
    scope = GitHubRepositoryScope(
        ["NielPieterse0/kis-mcp"],
        ["get_me"],
        [("NielPieterse0", "user", 12)],
    )

    scope.authorize(
        "search_code",
        {"query": "provider registry repo:NielPieterse0/kis-mcp"},
    )

    with pytest.raises(GitHubRepositoryScopeError, match="repo:owner/name"):
        scope.authorize("search_code", {"query": "provider registry"})

    with pytest.raises(GitHubRepositoryScopeError, match="other/repo"):
        scope.authorize("search_code", {"query": "provider repo:other/repo"})


def test_only_configured_identity_tools_may_be_unscoped() -> None:
    scope = GitHubRepositoryScope(
        ["NielPieterse0/kis-mcp"],
        ["get_me"],
        [("NielPieterse0", "user", 12)],
    )

    scope.authorize("get_me", {})

    with pytest.raises(GitHubRepositoryScopeError, match="explicit approved repository"):
        scope.authorize("list_notifications", {})


def test_allows_only_verified_project_read_methods_for_approved_owner() -> None:
    scope = GitHubRepositoryScope(
        ["NielPieterse0/kis-mcp"],
        ["get_me"],
        [("NielPieterse0", "user", 12)],
    )

    scope.authorize(
        "projects_get",
        {
            "method": "get_project",
            "owner": "NielPieterse0",
            "owner_type": "user",
            "project_number": 12,
        },
    )
    scope.authorize(
        "projects_list",
        {
            "method": "list_project_fields",
            "owner": "nielpieterse0",
            "owner_type": "user",
            "project_number": 12,
            "per_page": 50,
        },
    )
    scope.authorize(
        "projects_list",
        {
            "method": "list_project_items",
            "owner": "NielPieterse0",
            "owner_type": "user",
            "project_number": 12,
            "field_names": ["Status"],
        },
    )


def test_rejects_project_reads_for_unapproved_owner_or_method() -> None:
    scope = GitHubRepositoryScope(
        ["NielPieterse0/kis-mcp"],
        ["get_me"],
        [("NielPieterse0", "user", 12)],
    )

    with pytest.raises(GitHubRepositoryScopeError, match="not explicitly approved"):
        scope.authorize(
            "projects_get",
            {
                "method": "get_project",
                "owner": "other",
                "owner_type": "user",
                "project_number": 12,
            },
        )

    with pytest.raises(GitHubRepositoryScopeError, match="Project method is not approved"):
        scope.authorize(
            "projects_list",
            {
                "method": "list_projects",
                "owner": "NielPieterse0",
                "owner_type": "user",
            },
        )


def test_rejects_project_mutation_and_malformed_project_identity() -> None:
    scope = GitHubRepositoryScope(
        ["NielPieterse0/kis-mcp"],
        ["get_me"],
        [("NielPieterse0", "user", 12)],
    )

    with pytest.raises(GitHubRepositoryScopeError, match="explicit approved repository"):
        scope.authorize(
            "projects_write",
            {
                "method": "create_project",
                "owner": "NielPieterse0",
                "owner_type": "user",
                "title": "Not allowed",
            },
        )

    with pytest.raises(GitHubRepositoryScopeError, match="project_number"):
        scope.authorize(
            "projects_get",
            {
                "method": "get_project",
                "owner": "NielPieterse0",
                "owner_type": "user",
                "project_number": 0,
            },
        )

    with pytest.raises(GitHubRepositoryScopeError, match="owner_type"):
        scope.authorize(
            "projects_list",
            {
                "method": "list_project_items",
                "owner": "NielPieterse0",
                "owner_type": "team",
                "project_number": 12,
            },
        )
