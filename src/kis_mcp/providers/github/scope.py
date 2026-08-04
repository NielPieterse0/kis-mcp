from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext


_REPOSITORY_PART = re.compile(r"^[A-Za-z0-9_.-]+$")
_REPO_QUALIFIER = re.compile(r"(?:^|\s)repo:([^\s]+)", re.IGNORECASE)
_REPOSITORY_FIELDS = {
    "repository",
    "repository_name",
    "repository_url",
    "repo_full_name",
    "source_repository",
    "target_repository",
    "base_repository",
    "head_repository",
}


class GitHubRepositoryScopeError(RuntimeError):
    pass


def _validate_parts(owner: str, repository: str) -> str:
    owner = owner.strip()
    repository = repository.strip()
    if repository.casefold().endswith(".git"):
        repository = repository[:-4]
    if (
        not owner
        or not repository
        or owner in {".", ".."}
        or repository in {".", ".."}
        or _REPOSITORY_PART.fullmatch(owner) is None
        or _REPOSITORY_PART.fullmatch(repository) is None
    ):
        raise ValueError("Repository identity must use owner/repo")
    return f"{owner.casefold()}/{repository.casefold()}"


def normalize_repository(value: str) -> str:
    """Normalize supported GitHub repository identities to lowercase owner/repo."""

    raw = str(value).strip()
    if not raw:
        raise ValueError("Repository identity must use owner/repo")

    ssh = re.fullmatch(r"git@github\.com:([^/]+)/([^/]+)", raw, re.IGNORECASE)
    if ssh:
        return _validate_parts(ssh.group(1), ssh.group(2))

    if "://" in raw:
        parsed = urlsplit(raw)
        if parsed.username or parsed.password:
            raise ValueError("Credential-bearing repository URLs are not accepted")
        host = (parsed.hostname or "").casefold()
        parts = [part for part in parsed.path.split("/") if part]
        if host == "github.com" and len(parts) == 2:
            return _validate_parts(parts[0], parts[1])
        if host == "api.github.com" and len(parts) == 3 and parts[0].casefold() == "repos":
            return _validate_parts(parts[1], parts[2])
        raise ValueError("Repository URL must identify github.com owner/repo")

    parts = raw.split("/")
    if len(parts) != 2:
        raise ValueError("Repository identity must use owner/repo")
    return _validate_parts(parts[0], parts[1])


class GitHubRepositoryScope:
    """Authorize connector calls against explicit approved repository identities."""

    def __init__(
        self,
        approved_repositories: Sequence[str],
        unscoped_tools: Sequence[str],
    ) -> None:
        self.approved_repositories = frozenset(
            normalize_repository(value) for value in approved_repositories
        )
        if not self.approved_repositories:
            raise ValueError("At least one approved repository is required")
        self.unscoped_tools = frozenset(value.casefold() for value in unscoped_tools)

    def authorize(self, tool_name: str, arguments: Mapping[str, Any]) -> None:
        try:
            targets = self._extract_targets(arguments)
            query_targets = self._extract_query_targets(arguments)
        except ValueError as exc:
            raise GitHubRepositoryScopeError(
                "GITHUB_REPOSITORY_SCOPE: The call contains an invalid repository "
                f"target: {exc}"
            ) from exc
        targets.update(query_targets)

        if "search" in tool_name.casefold() and not targets:
            raise GitHubRepositoryScopeError(
                "GITHUB_REPOSITORY_SCOPE: Repository searches require an explicit "
                "repo:owner/name qualifier for an approved repository."
            )

        unapproved = sorted(targets.difference(self.approved_repositories))
        if unapproved:
            raise GitHubRepositoryScopeError(
                "GITHUB_REPOSITORY_SCOPE: Repository target is not approved: "
                + ", ".join(unapproved)
            )

        if targets:
            return
        if tool_name.casefold() in self.unscoped_tools:
            return
        raise GitHubRepositoryScopeError(
            "GITHUB_REPOSITORY_SCOPE: This tool call must include an explicit approved "
            "repository target."
        )

    def _extract_targets(self, value: Any) -> set[str]:
        targets: set[str] = set()
        if isinstance(value, Mapping):
            owner = value.get("owner")
            repo = value.get("repo")
            repository_name = value.get("repository_name")
            if isinstance(owner, str):
                if isinstance(repo, str):
                    targets.add(normalize_repository(f"{owner}/{repo}"))
                elif isinstance(repository_name, str):
                    targets.add(normalize_repository(f"{owner}/{repository_name}"))

            for key, item in value.items():
                key_name = str(key).casefold()
                if key_name in {"repo", "repository_name"} and isinstance(owner, str):
                    continue
                if key_name == "repo" and isinstance(item, str) and "/" in item:
                    targets.add(normalize_repository(item))
                elif key_name in _REPOSITORY_FIELDS and isinstance(item, str):
                    targets.add(normalize_repository(item))
                elif isinstance(item, (Mapping, list, tuple)):
                    targets.update(self._extract_targets(item))
        elif isinstance(value, (list, tuple)):
            for item in value:
                targets.update(self._extract_targets(item))
        return targets

    def _extract_query_targets(self, value: Any) -> set[str]:
        targets: set[str] = set()
        if isinstance(value, Mapping):
            for key, item in value.items():
                if str(key).casefold() == "query" and isinstance(item, str):
                    for match in _REPO_QUALIFIER.finditer(item):
                        targets.add(normalize_repository(match.group(1)))
                elif isinstance(item, (Mapping, list, tuple)):
                    targets.update(self._extract_query_targets(item))
        elif isinstance(value, (list, tuple)):
            for item in value:
                targets.update(self._extract_query_targets(item))
        return targets


class GitHubRepositoryScopeMiddleware(Middleware):
    def __init__(self, scope: GitHubRepositoryScope) -> None:
        self.scope = scope

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        try:
            self.scope.authorize(
                str(context.message.name),
                dict(context.message.arguments or {}),
            )
        except GitHubRepositoryScopeError as exc:
            raise ToolError(str(exc)) from exc
        return await call_next(context)
