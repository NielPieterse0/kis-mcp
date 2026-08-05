from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable, Mapping
from typing import Any

from fastmcp import Client

from .commission import commission_supabase_client
from .config import SupabaseProviderConfig, load_supabase_provider_config
from .runtime import legacy_pat_conflict, require_project_scope

ServerFactory = Callable[[], Any]


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
        for block in getattr(result, "content", ())
        if isinstance((text := getattr(block, "text", None)), str)
    ]
    if texts:
        try:
            parsed = json.loads("\n".join(texts))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Supabase MCP smoke status was not structured JSON") from exc
        if isinstance(parsed, dict):
            return parsed
    return {}


def _supabase_mounted(status: dict[str, Any]) -> bool:
    providers = status.get("external_providers")
    if not isinstance(providers, list):
        return False
    return any(
        isinstance(provider, dict)
        and provider.get("provider_id") == "supabase"
        and provider.get("mounted") is True
        and provider.get("state") == "mounted"
        for provider in providers
    )


async def _run_live_smoke(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
    server: Any,
) -> dict[str, bool]:
    async with Client(server, timeout=120, init_timeout=120) as client:
        status_result = await client.call_tool("kis_provider_status", {})
        if getattr(status_result, "is_error", False):
            raise RuntimeError("Supabase MCP shared runtime provider status failed")
        status = _result_mapping(status_result)
        if not _supabase_mounted(status):
            raise RuntimeError("Supabase MCP provider is not mounted in the shared runtime")

        report = await commission_supabase_client(
            client,
            config,
            environment,
            tool_prefix="supabase_",
        )

    return {"ready": True, "mounted": True, **report}


def run_live_smoke(
    server_factory: ServerFactory,
    config: SupabaseProviderConfig | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    runtime = config or load_supabase_provider_config()
    source = os.environ if environ is None else environ
    require_project_scope(runtime, source)
    if legacy_pat_conflict(runtime, source):
        raise RuntimeError(
            f"SUPABASE_LEGACY_PAT_CONFLICT: clear {runtime.legacy_pat_env} "
            "before shared-runtime OAuth verification"
        )
    server = server_factory()
    return asyncio.run(_run_live_smoke(runtime, source, server))


__all__ = ["ServerFactory", "run_live_smoke"]
