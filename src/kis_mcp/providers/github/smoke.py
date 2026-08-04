from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from typing import Any

from fastmcp import Client

from kis_mcp.server import build_server

from .commission import commission_github_client
from .settings import GitHubProviderSettings, load_github_provider_settings


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


def _github_mounted(status: dict[str, Any]) -> bool:
    providers = status.get("external_providers")
    if not isinstance(providers, list):
        return False
    return any(
        isinstance(provider, dict)
        and provider.get("provider_id") == "github-mcp"
        and provider.get("mounted") is True
        and provider.get("state") == "mounted"
        for provider in providers
    )


async def _run_live_smoke(
    settings: GitHubProviderSettings,
) -> dict[str, bool | str]:
    server = build_server()
    async with Client(server, timeout=120, init_timeout=120) as client:
        status_result = await client.call_tool("kis_provider_status", {})
        if getattr(status_result, "is_error", False):
            raise RuntimeError("GitHub MCP shared runtime provider status failed")
        status = _result_mapping(status_result)
        if not _github_mounted(status):
            raise RuntimeError("GitHub MCP provider is not mounted in the shared runtime")

        report = await commission_github_client(
            client,
            settings,
            tool_prefix="github_",
        )

    return {"ready": True, "mounted": True, **report}


def run_live_smoke(
    settings: GitHubProviderSettings | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, bool | str]:
    runtime = settings or load_github_provider_settings()
    source = os.environ if environ is None else environ
    if str(source.get(runtime.pat_env, "")).strip():
        raise RuntimeError(
            f"GITHUB_OAUTH_PAT_CONFLICT: clear {runtime.pat_env} before interactive OAuth commissioning"
        )
    return asyncio.run(_run_live_smoke(runtime))


def main() -> None:
    print(json.dumps(run_live_smoke(), sort_keys=True))


if __name__ == "__main__":
    main()
