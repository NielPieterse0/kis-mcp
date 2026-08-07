from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from typing import Any

from fastmcp import Client

from kis_mcp.repositories import RepositorySettings, load_repository_settings

from .server import build_github_provider_server
from .settings import GitHubProviderSettings, load_github_provider_settings


_REQUIRED_TOOLS = ("get_me", "get_file_contents", "create_or_update_file")


def _tool_name(prefix: str, name: str) -> str:
    return f"{prefix}{name}"


def _require_success(result: Any, label: str) -> None:
    if getattr(result, "is_error", False):
        raise RuntimeError(f"GitHub MCP commissioning failed during {label}")


def _result_evidence(result: Any) -> str:
    evidence: list[str] = []
    data = getattr(result, "data", None)
    if data is not None:
        try:
            evidence.append(json.dumps(data, sort_keys=True, default=str))
        except (TypeError, ValueError):
            evidence.append(str(data))
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        try:
            evidence.append(json.dumps(structured, sort_keys=True, default=str))
        except (TypeError, ValueError):
            evidence.append(str(structured))
    for block in getattr(result, "content", ()):
        text = getattr(block, "text", None)
        if isinstance(text, str):
            evidence.append(text)
    return "\n".join(evidence)


def _is_scope_rejection(value: Any) -> bool:
    return "GITHUB_REPOSITORY_SCOPE" in str(value)


def _rejected_repository(repository_settings: RepositorySettings) -> str:
    approved = repository_settings.github_repository
    for candidate in ("github/github-mcp-server", "octocat/hello-world"):
        if candidate != approved:
            return candidate
    raise RuntimeError("GitHub MCP commissioning could not select another repository")


async def commission_github_client(
    client: Any,
    repository_settings: RepositorySettings,
    *,
    tool_prefix: str = "",
) -> dict[str, bool | str]:
    tools = await client.list_tools()
    names = {str(tool.name) for tool in tools}
    required = {_tool_name(tool_prefix, name) for name in _REQUIRED_TOOLS}
    missing = sorted(required.difference(names))
    if missing:
        raise RuntimeError(
            "GitHub MCP pinned read/write surface is incomplete: " + ", ".join(missing)
        )

    identity = await client.call_tool(_tool_name(tool_prefix, "get_me"), {})
    _require_success(identity, "OAuth authentication")

    approved_repository = repository_settings.github_repository
    owner, repository = approved_repository.split("/", 1)
    private_read = await client.call_tool(
        _tool_name(tool_prefix, "get_file_contents"),
        {"owner": owner, "repo": repository, "path": "README.md"},
    )
    _require_success(private_read, "selected private-repository read")

    rejected_repository = _rejected_repository(repository_settings)
    rejected_owner, rejected_repo = rejected_repository.split("/", 1)
    try:
        result = await client.call_tool(
            _tool_name(tool_prefix, "get_file_contents"),
            {
                "owner": rejected_owner,
                "repo": rejected_repo,
                "path": "README.md",
            },
        )
    except Exception as exc:
        if not _is_scope_rejection(exc):
            raise
    else:
        scope_evidence = _result_evidence(result)
        if not getattr(result, "is_error", False) or not _is_scope_rejection(
            scope_evidence
        ):
            raise RuntimeError(
                "GitHub MCP repository routing did not produce explicit "
                "GITHUB_REPOSITORY_SCOPE evidence"
            )

    return {
        "surface": True,
        "authentication": True,
        "private_repository_read": True,
        "repository_scope": True,
        "approved_repository": approved_repository,
        "rejected_repository": rejected_repository,
    }


async def _run_standalone_commissioning(
    settings: GitHubProviderSettings,
    repository_settings: RepositorySettings,
) -> dict[str, bool | str]:
    server = build_github_provider_server(
        settings,
        repository_settings_source=lambda: repository_settings,
    )
    async with Client(server, timeout=120, init_timeout=120) as client:
        return await commission_github_client(client, repository_settings)


def run_standalone_commissioning(
    settings: GitHubProviderSettings | None = None,
    repository_settings: RepositorySettings | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, bool | str]:
    runtime = settings or load_github_provider_settings()
    selected_repository = repository_settings or load_repository_settings()
    source = os.environ if environ is None else environ
    if str(source.get(runtime.pat_env, "")).strip():
        raise RuntimeError(
            f"GITHUB_OAUTH_PAT_CONFLICT: clear {runtime.pat_env} before interactive OAuth commissioning"
        )
    return asyncio.run(_run_standalone_commissioning(runtime, selected_repository))


def main() -> None:
    print(json.dumps(run_standalone_commissioning(), sort_keys=True))


if __name__ == "__main__":
    main()
