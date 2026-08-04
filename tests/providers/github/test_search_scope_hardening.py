from __future__ import annotations

import pytest

from kis_mcp.providers.github.scope import GitHubRepositoryScope, GitHubRepositoryScopeError


SCOPE = GitHubRepositoryScope(["NielPieterse0/kis-mcp"], ["get_me"])


@pytest.mark.parametrize(
    "query",
    [
        "repo:NielPieterse0/kis-mcp provider path:src",
        "(repo:NielPieterse0/kis-mcp) provider",
        "repo:NielPieterse0/kis-mcp language:python filename:scope.py symbol:authorize",
        "repo:NielPieterse0/kis-mcp NOT path:tests",
        "repo:NielPieterse0/kis-mcp NOT (path:tests OR filename:test_scope.py)",
        "repo:NielPieterse0/kis-mcp (path:src OR path:tests)",
        'repo:NielPieterse0/kis-mcp "repo:other/repository" provider',
    ],
)
def test_allows_filters_grouping_and_safe_exclusions(query: str) -> None:
    SCOPE.authorize("search_code", {"query": query})


@pytest.mark.parametrize(
    "query",
    [
        "repo:NielPieterse0/kis-mcp OR path:tests",
        "(repo:NielPieterse0/kis-mcp OR path:tests) provider",
        "NOT repo:NielPieterse0/kis-mcp path:tests",
        "repo:NielPieterse0/kis-mcp repo:NielPieterse0/kis-mcp",
        "repo:NielPieterse0/kis-mcp org:NielPieterse0",
        "repo:NielPieterse0/kis-mcp user:NielPieterse0",
        "repo:NielPieterse0/kis-mcp owner:NielPieterse0",
        "repo:NielPieterse0/kis-mcp AND",
        "repo:NielPieterse0/kis-mcp (path:src",
    ],
)
def test_rejects_only_unsupported_or_scope_bypassing_grammar(query: str) -> None:
    with pytest.raises(GitHubRepositoryScopeError) as captured:
        SCOPE.authorize("search_code", {"query": query})

    assert captured.value.reason == "unsupported_search_grammar"
    assert "GITHUB_UNSUPPORTED_SEARCH_GRAMMAR" in str(captured.value)


@pytest.mark.parametrize(
    "query",
    [
        "provider registry",
        '"repo:NielPieterse0/kis-mcp" provider',
        "repo:NielPieterse0/other provider",
        "repo:not-a-repository provider",
    ],
)
def test_repository_scope_violations_are_reported_separately(query: str) -> None:
    with pytest.raises(GitHubRepositoryScopeError) as captured:
        SCOPE.authorize("search_code", {"query": query})

    assert captured.value.reason == "repository_scope_violation"
    assert "GITHUB_REPOSITORY_SCOPE_VIOLATION" in str(captured.value)
