from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import Client, FastMCP

from kis_mcp.config import load_runtime_config
from kis_mcp.providers.runtime_settings import (
    ProviderMountSetting,
    ProviderRuntimeSettings,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_primary_build_server_exposes_control_center_tool_and_ui_resource(
    monkeypatch,
) -> None:
    from kis_mcp import server as server_module

    monkeypatch.setattr(
        server_module,
        "create_proxy",
        lambda *_args, **_kwargs: FastMCP("test-primary-gateway"),
    )
    runtime_settings = ProviderRuntimeSettings(
        schema_version=1,
        providers=(
            ProviderMountSetting(
                provider_id="control-center",
                enabled=True,
                namespace="controlcenter",
            ),
            ProviderMountSetting(
                provider_id="github-mcp",
                enabled=False,
                namespace="github",
            ),
            ProviderMountSetting(
                provider_id="supabase",
                enabled=False,
                namespace="supabase",
            ),
        ),
    )

    server = server_module.build_server(
        config=load_runtime_config(REPOSITORY_ROOT),
        validate_provider=False,
        provider_runtime_settings=runtime_settings,
    )

    async def inspect() -> None:
        async with Client(server) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            result = await client.call_tool("controlcenter_open_kis_control_center", {})
        mounted_tool = next(
            item for item in tools if item.name == "controlcenter_open_kis_control_center"
        )
        expected_uri = "ui://controlcenter/kis-mcp/control-center.html"
        assert mounted_tool.meta["ui"]["resourceUri"] == expected_uri
        assert expected_uri in {str(item.uri) for item in resources}
        assert result.structured_content["schema_version"] == 1
        assert result.structured_content["provider_runtime"]

    asyncio.run(inspect())
