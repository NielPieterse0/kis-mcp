from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from fastmcp import Client

from kis_mcp.projects import ProjectRegistry, load_project_registry_settings

from .config import SupabaseProviderConfig, load_supabase_provider_config
from .runtime import legacy_pat_conflict
from .server import build_server


_REQUIRED_READ_TOOLS = ("get_project_url", "list_tables")
_REPRESENTATIVE_MUTATING_TOOL = "apply_migration"


def _tool_name(prefix: str, name: str) -> str:
    return f"{prefix}{name}"


def _result_payload(result: Any) -> dict[str, Any]:
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
        for block in getattr(result, "content", ())
        if isinstance((text := getattr(block, "text", None)), str)
    ]
    if not texts:
        return {}
    try:
        parsed = json.loads("\n".join(texts))
    except json.JSONDecodeError:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _require_tool_surface(
    names: set[str],
    config: SupabaseProviderConfig,
    tool_prefix: str,
) -> None:
    required_reads = {
        _tool_name(tool_prefix, name) for name in _REQUIRED_READ_TOOLS
    }
    missing_reads = sorted(required_reads - names)
    if missing_reads:
        raise RuntimeError(
            "Supabase MCP required read tools are missing: "
            + ", ".join(missing_reads)
        )

    mutating_tool = _tool_name(tool_prefix, _REPRESENTATIVE_MUTATING_TOOL)
    if config.read_only:
        if mutating_tool in names:
            raise RuntimeError(
                "Supabase MCP read-only surface exposes a mutating tool: "
                f"{mutating_tool}"
            )
    elif mutating_tool not in names:
        raise RuntimeError(
            "Supabase MCP required non-invoked mutation surface is missing: "
            f"{mutating_tool}"
        )


def _require_project_url(result: Any, project_ref: str) -> None:
    if getattr(result, "is_error", False):
        raise RuntimeError("Supabase MCP commissioning failed during registered project read")

    payload = _result_payload(result)
    value = payload.get("url")
    if not isinstance(value, str):
        raise RuntimeError("Supabase MCP registered project read returned no project URL")

    parsed = urlparse(value)
    expected_hostname = f"{project_ref}.supabase.co".lower()
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != expected_hostname:
        raise RuntimeError(
            "Supabase MCP registered project read did not match the configured project"
        )


def _registered_project_ref(
    registry: ProjectRegistry,
    project_id: str | None,
) -> str:
    project = registry.project(project_id or registry.default_project_id)
    if project.supabase is None:
        raise RuntimeError(
            f"Registered KIS project has no Supabase binding: {project.project_id}"
        )
    return project.supabase.project_ref


async def commission_supabase_client(
    client: Any,
    config: SupabaseProviderConfig,
    project_ref: str,
    *,
    tool_prefix: str = "",
) -> dict[str, bool]:
    tools = await client.list_tools()
    names = {str(tool.name) for tool in tools}
    _require_tool_surface(names, config, tool_prefix)

    required_read = _tool_name(tool_prefix, "get_project_url")
    result = await client.call_tool(required_read, {"project_id": project_ref})
    _require_project_url(result, project_ref)
    return {
        "account_surface": True,
        "authentication": True,
        "registered_project_read": True,
    }


async def _run_standalone_commissioning(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
    project_ref: str,
    registry: ProjectRegistry,
) -> dict[str, bool]:
    server = build_server(config, environment, project_registry=registry)
    async with Client(server, timeout=120, init_timeout=120) as client:
        return await commission_supabase_client(client, config, project_ref)


def run_standalone_commissioning(
    config: SupabaseProviderConfig | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    project_id: str | None = None,
    registry: ProjectRegistry | None = None,
) -> dict[str, bool]:
    runtime = config or load_supabase_provider_config()
    source = os.environ if environ is None else environ
    if legacy_pat_conflict(runtime, source):
        raise RuntimeError(
            f"SUPABASE_LEGACY_PAT_CONFLICT: clear {runtime.legacy_pat_env} "
            "before browser OAuth commissioning"
        )
    projects = registry or load_project_registry_settings()
    project_ref = _registered_project_ref(projects, project_id)
    return asyncio.run(
        _run_standalone_commissioning(runtime, source, project_ref, projects)
    )


def main() -> None:
    print(json.dumps(run_standalone_commissioning(), sort_keys=True))


if __name__ == "__main__":
    main()
