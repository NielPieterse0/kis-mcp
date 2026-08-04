from __future__ import annotations

import asyncio
import json
from typing import Any

from fastmcp import Client

from .server import build_github_provider_server
from .settings import GitHubProviderSettings, load_github_provider_settings


_REQUIRED_SURFACE = {
    "kis_github_health",
    "get_me",
    "get_file_contents",
    "create_or_update_file",
}


def _result_mapping(result: Any) -> dict[str, Any]:
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return dict(data)

    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        nested = structured.get("result")
        if isinstance(nested, dict):
            return dict(nested)
        return dict(structured)

    texts = [
        text
        for block in getattr(result, "content", [])
        if isinstance((text := getattr(block, "text", None)), str)
    ]
    if texts:
        try:
            parsed = json.loads("\n".join(texts))
        except json.JSONDecodeError as exc:
            raise RuntimeError("GitHub MCP smoke result was not structured JSON") from exc
        if isinstance(parsed, dict):
            return parsed
    return {}


def _require_success(result: Any, label: str) -> None:
    if getattr(result, "is_error", False):
        raise RuntimeError(f"GitHub MCP live smoke failed during {label}")


async def _run_live_smoke(
    settings: GitHubProviderSettings,
) -> dict[str, bool | str]:
    server = build_github_provider_server(settings)
    async with Client(server, timeout=60, init_timeout=60) as client:
        tools = await client.list_tools()
        names = {str(tool.name) for tool in tools}
        missing = sorted(_REQUIRED_SURFACE.difference(names))
        if missing:
            raise RuntimeError(
                "GitHub MCP pinned read/write surface is incomplete: "
                + ", ".join(missing)
            )

        health_result = await client.call_tool("kis_github_health", {})
        _require_success(health_result, "health")
        health = _result_mapping(health_result)
        if health.get("ready") is not True or health.get("token_present") is not True:
            raise RuntimeError("GitHub MCP health did not report live readiness")

        identity_result = await client.call_tool("get_me", {})
        _require_success(identity_result, "authentication")

        repository = settings.approved_repositories[0]
        owner, repo = repository.split("/", 1)
        read_result = await client.call_tool(
            "get_file_contents",
            {"owner": owner, "repo": repo, "path": "README.md"},
        )
        _require_success(read_result, "approved private-repository read")

    return {
        "ready": True,
        "surface": True,
        "authentication": True,
        "private_repository_read": True,
        "approved_repository": repository,
    }


def run_live_smoke(
    settings: GitHubProviderSettings | None = None,
) -> dict[str, bool | str]:
    return asyncio.run(_run_live_smoke(settings or load_github_provider_settings()))


def main() -> None:
    print(json.dumps(run_live_smoke(), sort_keys=True))


if __name__ == "__main__":
    main()
