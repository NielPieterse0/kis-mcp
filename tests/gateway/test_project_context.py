from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from kis_mcp.config import load_runtime_config
from kis_mcp.gateway.composition import compose_gateway
from kis_mcp.providers.contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from kis_mcp.providers.registry import ProviderRegistry
from kis_mcp.providers.runtime_settings import ProviderMountSetting, ProviderRuntimeSettings
from kis_mcp.providers.service import ProviderService


def _descriptor(provider_id: str) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=provider_id,
        display_name=provider_id,
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=f"test:{provider_id}",
        source_revision="test",
        capabilities=(
            ProviderCapability(
                capability_id=f"{provider_id}.operate",
                description=f"Operate {provider_id}.",
                effects=("external_network",),
            ),
        ),
        builder=lambda: FastMCP(provider_id),
        readiness_probe=lambda: ProviderReadiness(
            provider_id=provider_id,
            state=ProviderState.READY,
            summary="ready",
        ),
    )


def _service() -> ProviderService:
    return ProviderService(
        ProviderRegistry((_descriptor("github-mcp"), _descriptor("supabase")))
    )


def _runtime_settings() -> ProviderRuntimeSettings:
    return ProviderRuntimeSettings(
        schema_version=1,
        providers=(
            ProviderMountSetting(
                provider_id="github-mcp",
                enabled=True,
                namespace="github",
            ),
            ProviderMountSetting(
                provider_id="supabase",
                enabled=False,
                namespace="supabase",
            ),
        ),
    )


def test_gateway_owns_registry_injects_provider_routing_and_exposes_projects() -> None:
    composed = compose_gateway(
        load_runtime_config(),
        validate_provider=False,
        provider_service=_service(),
        provider_runtime_settings=_runtime_settings(),
        create_proxy_fn=lambda *_args, **_kwargs: FastMCP("project-context"),
    )

    assert composed.projects.default_project_id == "kis-mcp"
    assert composed.projects.project("gpt-os").github.repository == "nielpieterse0/gpt-os"
    names = {tool.name for tool in asyncio.run(composed.server.list_tools())}
    assert {"kis_list_projects", "kis_project_status"}.issubset(names)
    assert {"kis_list_projects", "kis_project_status"}.issubset(
        composed.exposure.direct_operations
    )
