from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext


_REPOSITORY_PART = re.compile(r"^[A-Za-z0-9_.-]+$")
_QUALIFIER = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(.*)$")
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
_SCOPE_QUALIFIERS = frozenset({"repo", "org", "user", "owner"})
_PROJECT_READ_METHODS = {
    "projects_get": frozenset({"get_project"}),
    "projects_list": frozenset({"list_project_fields", "list_project_items"}),
}
_PROJECT_OWNER_TYPES = frozenset({"user", "org"})


class GitHubRepositoryScopeError(RuntimeError):
    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        code = (
            "GITHUB_UNSUPPORTED_SEARCH_GRAMMAR"
            if reason == "unsupported_search_grammar"
            else "GITHUB_REPOSITORY_SCOPE_VIOLATION"
        )
        super().__init__(f"{code}: {reason}: {message}")


@dataclass(frozen=True, slots=True)
class _SearchToken:
    kind: str
    value: str
    quoted: bool = False


@dataclass(frozen=True, slots=True)
class _SearchNode:
    kind: str
    value: str | None = None
    quoted: bool = False
    children: tuple[_SearchNode, ...] = ()


class _SearchParser:
    def __init__(self, query: str) -> None:
        self.tokens = _tokenize_search(query)
        self.index = 0

    def parse(self) -> _SearchNode:
        if not self.tokens:
            raise ValueError("Search query is empty")
        node = self._parse_or()
        if self.index != len(self.tokens):
            raise ValueError("Unexpected search token")
        return node

    def _parse_or(self) -> _SearchNode:
        nodes = [self._parse_and()]
        while self._accept("OR"):
            nodes.append(self._parse_and())
        return nodes[0] if len(nodes) == 1 else _SearchNode("or", children=tuple(nodes))

    def _parse_and(self) -> _SearchNode:
        nodes: list[_SearchNode] = []
        while self.index < len(self.tokens):
            token = self.tokens[self.index]
            if token.kind in {"RPAREN", "OR"}:
                break
            if token.kind == "AND":
                self.index += 1
                if not nodes:
                    raise ValueError("AND requires a preceding expression")
                if self.index >= len(self.tokens) or self.tokens[self.index].kind in {
                    "AND",
                    "OR",
                    "RPAREN",
                }:
                    raise ValueError("AND requires a following expression")
                continue
            nodes.append(self._parse_unary())
        if not nodes:
            raise ValueError("Expected a search expression")
        return nodes[0] if len(nodes) == 1 else _SearchNode("and", children=tuple(nodes))

    def _parse_unary(self) -> _SearchNode:
        if self._accept("NOT"):
            return _SearchNode("not", children=(self._parse_unary(),))
        if self._accept("LPAREN"):
            node = self._parse_or()
            if not self._accept("RPAREN"):
                raise ValueError("Unclosed search group")
            return node
        if self.index >= len(self.tokens):
            raise ValueError("Expected a search term")
        token = self.tokens[self.index]
        if token.kind != "TERM":
            raise ValueError("Expected a search term")
        self.index += 1
        return _SearchNode("term", value=token.value, quoted=token.quoted)

    def _accept(self, kind: str) -> bool:
        if self.index < len(self.tokens) and self.tokens[self.index].kind == kind:
            self.index += 1
            return True
        return False


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
        approved_projects: Sequence[tuple[str, str, int]] = (),
    ) -> None:
        self.approved_repositories = frozenset(
            normalize_repository(value) for value in approved_repositories
        )
        if not self.approved_repositories:
            raise ValueError("At least one approved repository is required")
        normalized_projects: set[tuple[str, str, int]] = set()
        for owner, owner_type, project_number in approved_projects:
            normalized_owner = str(owner).strip().casefold()
            normalized_owner_type = str(owner_type).strip().casefold()
            if (
                _REPOSITORY_PART.fullmatch(normalized_owner) is None
                or normalized_owner in {".", ".."}
                or normalized_owner_type not in _PROJECT_OWNER_TYPES
                or isinstance(project_number, bool)
                or not isinstance(project_number, int)
                or project_number <= 0
            ):
                raise ValueError("approved_projects contains an invalid project identity")
            normalized_projects.add(
                (normalized_owner, normalized_owner_type, project_number)
            )
        self.approved_projects = frozenset(normalized_projects)
        self.unscoped_tools = frozenset(value.casefold() for value in unscoped_tools)

    def authorize(self, tool_name: str, arguments: Mapping[str, Any]) -> None:
        normalized_tool = tool_name.casefold()
        if normalized_tool in _PROJECT_READ_METHODS:
            self._authorize_project_read(normalized_tool, arguments)
            return
        if "search" in normalized_tool:
            self._authorize_search(arguments)
            return

        try:
            targets = self._extract_targets(arguments)
        except ValueError as exc:
            raise GitHubRepositoryScopeError(
                "repository_scope_violation",
                f"The call contains an invalid repository target: {exc}",
            ) from exc

        unapproved = sorted(targets.difference(self.approved_repositories))
        if unapproved:
            raise GitHubRepositoryScopeError(
                "repository_scope_violation",
                "Repository target is not approved: " + ", ".join(unapproved),
            )

        if targets:
            return
        if tool_name.casefold() in self.unscoped_tools:
            return
        raise GitHubRepositoryScopeError(
            "repository_scope_violation",
            "This tool call must include an explicit approved repository target.",
        )

    def _authorize_project_read(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
    ) -> None:
        method = arguments.get("method")
        if not isinstance(method, str) or method not in _PROJECT_READ_METHODS[tool_name]:
            raise GitHubRepositoryScopeError(
                "repository_scope_violation",
                "Project method is not approved for read-only access.",
            )

        owner = arguments.get("owner")
        if (
            not isinstance(owner, str)
            or not owner.strip()
            or owner.strip() in {".", ".."}
            or _REPOSITORY_PART.fullmatch(owner.strip()) is None
        ):
            raise GitHubRepositoryScopeError(
                "repository_scope_violation",
                "Project owner must be a valid GitHub owner.",
            )
        owner_type = arguments.get("owner_type")
        if not isinstance(owner_type, str) or owner_type.casefold() not in _PROJECT_OWNER_TYPES:
            raise GitHubRepositoryScopeError(
                "repository_scope_violation",
                "Project owner_type must be user or org.",
            )

        project_number = arguments.get("project_number")
        if (
            isinstance(project_number, bool)
            or not isinstance(project_number, int)
            or project_number <= 0
        ):
            raise GitHubRepositoryScopeError(
                "repository_scope_violation",
                "Project project_number must be a positive integer.",
            )
        project_key = (
            owner.strip().casefold(),
            owner_type.strip().casefold(),
            project_number,
        )
        if project_key not in self.approved_projects:
            raise GitHubRepositoryScopeError(
                "repository_scope_violation",
                "Project identity is not explicitly approved.",
            )

    def _authorize_search(self, arguments: Mapping[str, Any]) -> None:
        queries = _collect_queries(arguments)
        if len(queries) != 1:
            raise GitHubRepositoryScopeError(
                "unsupported_search_grammar",
                "A repository search must contain exactly one query string.",
            )
        try:
            root = _SearchParser(queries[0]).parse()
        except ValueError as exc:
            raise GitHubRepositoryScopeError(
                "unsupported_search_grammar",
                f"The search query cannot be authorized by the bounded parser: {exc}",
            ) from exc

        repository_terms: list[str] = []
        conflicting_scope: list[str] = []
        for node in _walk(root):
            if node.kind != "term" or node.quoted or not node.value:
                continue
            qualifier = _qualifier(node.value)
            if qualifier is None:
                continue
            name, value = qualifier
            if name == "repo":
                try:
                    repository_terms.append(normalize_repository(value))
                except ValueError as exc:
                    raise GitHubRepositoryScopeError(
                        "repository_scope_violation",
                        f"The search query contains an invalid repository target: {exc}",
                    ) from exc
            elif name in _SCOPE_QUALIFIERS:
                conflicting_scope.append(name)

        if not repository_terms:
            raise GitHubRepositoryScopeError(
                "repository_scope_violation",
                "Repository searches require an explicit repo:owner/name qualifier for an approved repository.",
            )
        unapproved = sorted(set(repository_terms).difference(self.approved_repositories))
        if unapproved:
            raise GitHubRepositoryScopeError(
                "repository_scope_violation",
                "Repository target is not approved: " + ", ".join(unapproved),
            )
        if len(repository_terms) != 1:
            raise GitHubRepositoryScopeError(
                "unsupported_search_grammar",
                "The search query must contain exactly one effective repository qualifier.",
            )
        if conflicting_scope:
            raise GitHubRepositoryScopeError(
                "unsupported_search_grammar",
                "The search query contains additional repository-scope qualifiers: "
                + ", ".join(sorted(set(conflicting_scope))),
            )
        if not _repository_scope_guaranteed(root):
            raise GitHubRepositoryScopeError(
                "unsupported_search_grammar",
                "The search query can negate or bypass the approved repository constraint.",
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


def _tokenize_search(query: str) -> tuple[_SearchToken, ...]:
    tokens: list[_SearchToken] = []
    index = 0
    while index < len(query):
        character = query[index]
        if character.isspace():
            index += 1
            continue
        if character == "(":
            tokens.append(_SearchToken("LPAREN", character))
            index += 1
            continue
        if character == ")":
            tokens.append(_SearchToken("RPAREN", character))
            index += 1
            continue
        if character in {"\"", "'"}:
            quote = character
            index += 1
            value: list[str] = []
            while index < len(query):
                character = query[index]
                if character == "\\" and index + 1 < len(query):
                    index += 1
                    value.append(query[index])
                    index += 1
                    continue
                if character == quote:
                    index += 1
                    break
                value.append(character)
                index += 1
            else:
                raise ValueError("Unclosed quoted search term")
            tokens.append(_SearchToken("TERM", "".join(value), quoted=True))
            continue

        start = index
        while index < len(query) and not query[index].isspace() and query[index] not in "()":
            index += 1
        value = query[start:index]
        upper = value.upper()
        kind = upper if upper in {"AND", "OR", "NOT"} else "TERM"
        tokens.append(_SearchToken(kind, value))
    return tuple(tokens)


def _walk(node: _SearchNode) -> tuple[_SearchNode, ...]:
    values = [node]
    for child in node.children:
        values.extend(_walk(child))
    return tuple(values)


def _qualifier(value: str) -> tuple[str, str] | None:
    match = _QUALIFIER.fullmatch(value)
    if match is None:
        return None
    return match.group(1).casefold(), match.group(2)


def _repository_scope_guaranteed(node: _SearchNode) -> bool:
    if node.kind == "term":
        if node.quoted or not node.value:
            return False
        qualifier = _qualifier(node.value)
        return qualifier is not None and qualifier[0] == "repo"
    if node.kind == "not":
        return False
    if node.kind == "and":
        return any(_repository_scope_guaranteed(child) for child in node.children)
    if node.kind == "or":
        return bool(node.children) and all(
            _repository_scope_guaranteed(child) for child in node.children
        )
    return False


def _collect_queries(value: Any) -> tuple[str, ...]:
    queries: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() == "query" and isinstance(item, str):
                queries.append(item)
            elif isinstance(item, (Mapping, list, tuple)):
                queries.extend(_collect_queries(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            queries.extend(_collect_queries(item))
    return tuple(queries)
