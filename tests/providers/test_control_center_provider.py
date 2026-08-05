from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import Client, FastMCP

from kis_mcp.control_center.app import CONTROL_CENTER_RESOURCE_URI
from kis_mcp.providers import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderRegistry,
    ProviderService,
    ProviderState,
)
from kis_mcp.providers.control_center import (
    control_center_provider_descriptor,
    register_control_center_provider,
)
from kis_mcp.providers.runtime import compose_provider_runtime
from kis_mcp.providers.runtime_settings import (
    ProviderMountSetting,
    ProviderRuntimeSettings,
)


def _external_descriptor(provider_id: str) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=provider_id,
        display_name=provider_id,
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=f"test:{provider_id}",
        source_revision="test",
        capabilities=(
            ProviderCapability(
                capability_id=f"{provider_id}.test",
                description="Test capability.",
            ),
        ),
        builder=lambda: FastMCP(f"{provider_id}-test"),
        readiness_probe=lambda: ProviderReadiness(
            provider_id=provider_id,
            state=ProviderState.READY,
            summary="Test provider ready.",
        ),
    )


def test_control_center_descriptor_is_local_read_only_and_builds_mcp_app() -> None:
    descriptor = control_center_provider_descriptor(
        provider_status_source=lambda: {"external_providers": []}
    )

    assert descriptor.provider_id == "control-center"
    assert descriptor.display_name == "KIS Control Center"
    assert descriptor.provider_kind is ProviderKind.PLATFORM
    assert descriptor.boundary is ProviderBoundary.LOCAL_READ_ONLY
    assert [item.capability_id for item in descriptor.capabilities] == [
        "operations.dashboard"
    ]
    assert descriptor.capabilities[0].tool_names == ("open_kis_control_center",)
    assert descriptor.readiness_probe().state is ProviderState.READY

    server = descriptor.builder()
    assert isinstance(server, FastMCP)

    async def inspect() -> None:
        async with Client(server) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
        assert [item.name for item in tools] == ["open_kis_control_center"]
        assert [str(item.uri) for item in resources] == [CONTROL_CENTER_RESOURCE_URI]

    asyncio.run(inspect())


def test_control_center_mounts_through_normal_provider_runtime_without_second_process() -> None:
    registry = ProviderRegistry()
    register_control_center_provider(registry)
    registry.register(_external_descriptor("github-mcp"))
    registry.register(_external_descriptor("supabase"))
    service = ProviderService(registry)
    settings = ProviderRuntimeSettings(
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
    root = FastMCP("root")

    composition = compose_provider_runtime(root, service, settings)

    control_center = next(
        item for item in composition.results if item.provider_id == "control-center"
    )
    assert control_center.mounted is True

    async def inspect() -> None:
        async with Client(root) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            result = await client.call_tool("controlcenter_open_kis_control_center", {})
        mounted_tool = next(
            item for item in tools if item.name == "controlcenter_open_kis_control_center"
        )
        mounted_resource_uri = "ui://controlcenter/kis-mcp/control-center.html"
        assert mounted_tool.meta["ui"]["resourceUri"] == mounted_resource_uri
        assert mounted_resource_uri in {str(item.uri) for item in resources}
        assert result.structured_content["runtime"]["product"] == "kis-mcp"

    asyncio.run(inspect())
