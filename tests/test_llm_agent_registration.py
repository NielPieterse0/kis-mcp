from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import FastMCP

from kis_mcp import server as server_module
from kis_mcp.providers.runtime_settings import ProviderMountSetting, ProviderRuntimeSettings


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_build_server_registers_additive_review_and_benchmark_tools(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "create_proxy",
        lambda *_args, **_kwargs: FastMCP("test-root"),
    )
    runtime_settings = ProviderRuntimeSettings(
        schema_version=1,
        providers=(
            ProviderMountSetting(
                provider_id="github-mcp", enabled=False, namespace="github"
            ),
            ProviderMountSetting(
                provider_id="supabase", enabled=False, namespace="supabase"
            ),
        ),
    )

    server = server_module.build_server(
        validate_provider=False,
        provider_runtime_settings=runtime_settings,
    )
    names = [tool.name for tool in asyncio.run(server.list_tools())]

    assert names.count("review_change_with_agent") == 1
    assert "benchmark_nvidia_model" not in names
    assert "kis_health" in names
    assert "kis_provider_status" in names
    assert "inspect_project" in names
    assert "inspect_change" in names

    search = asyncio.run(
        server.call_tool(
            "search_capabilities", {"query": "benchmark_nvidia_model", "limit": 10}
        )
    )
    operation = next(
        item
        for item in search.structured_content["operations"]
        if item["operation_name"] == "benchmark_nvidia_model"
    )
    assert operation["effects"] == ["external", "read_only"]
    assert operation["eligible"] is True
