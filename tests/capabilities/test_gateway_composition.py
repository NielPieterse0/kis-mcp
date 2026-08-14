from __future__ import annotations

import asyncio
import inspect

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


def child(label: str) -> FastMCP:
    server = FastMCP(label)

    @server.tool(name="echo")
    def echo(value: str) -> str:
        return f"{label}:{value}"

    return server


def descriptor(provider_id: str, *, state: ProviderState = ProviderState.READY) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=provider_id,
        display_name=provider_id,
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=f"source:{provider_id}",
        source_revision="test",
        capabilities=(
            ProviderCapability(
                capability_id=f"{provider_id}.operate",
                description=f"Operate {provider_id}.",
                effects=("external_network",),
            ),
        ),
        builder=lambda: child(provider_id),
        readiness_probe=lambda: ProviderReadiness(
            provider_id=provider_id,
            state=state,
            summary=state.value,
        ),
    )


def runtime_settings() -> ProviderRuntimeSettings:
    return ProviderRuntimeSettings(
        schema_version=1,
        providers=(
            ProviderMountSetting(provider_id="github-mcp", enabled=True, namespace="github"),
            ProviderMountSetting(provider_id="supabase", enabled=False, namespace="supabase"),
        ),
    )


def service() -> ProviderService:
    return ProviderService(
        ProviderRegistry(
            (
                descriptor("github-mcp", state=ProviderState.UNAVAILABLE),
                descriptor("supabase"),
            )
        )
    )


def test_compose_gateway_owns_instance_scoped_capability_state() -> None:
    runtime = load_runtime_config()
    first = compose_gateway(
        runtime,
        validate_provider=False,
        provider_service=service(),
        provider_runtime_settings=runtime_settings(),
        create_proxy_fn=lambda *_args, **_kwargs: FastMCP("first"),
    )
    second = compose_gateway(
        runtime,
        validate_provider=False,
        provider_service=service(),
        provider_runtime_settings=runtime_settings(),
        create_proxy_fn=lambda *_args, **_kwargs: FastMCP("second"),
    )

    assert first.capabilities is not second.capabilities
    assert first.provider_composition is not second.provider_composition
    assert first.server.name == "first"
    assert second.server.name == "second"


def test_gateway_exposes_curated_surface_and_discovers_hidden_tools() -> None:
    composed = compose_gateway(
        load_runtime_config(),
        validate_provider=False,
        provider_service=service(),
        provider_runtime_settings=runtime_settings(),
        create_proxy_fn=lambda *_args, **_kwargs: FastMCP("curated"),
    )

    names = {tool.name for tool in asyncio.run(composed.server.list_tools())}
    assert {
        "kis_health",
        "kis_provider_status",
        "inspect_project",
        "inspect_change",
        "search_capabilities",
        "describe_capability",
        "recommend_workflow",
        "execute_read_action",
        "execute_change_action",
        "execute_external_action",
    }.issubset(names)
    assert "list_skills" not in names
    assert "github_echo" not in names

    search = asyncio.run(
        composed.server.call_tool(
            "search_capabilities",
            {"query": "list skills", "limit": 20},
        )
    )
    payload = search.structured_content
    assert payload is not None
    assert any(item["operation_name"] == "list_skills" for item in payload["operations"])

    result = asyncio.run(
        composed.server.call_tool(
            "execute_read_action",
            {"operation": "list_skills", "arguments": {"limit": 1}},
        )
    )
    assert result.structured_content is not None

    telemetry_search = asyncio.run(
        composed.server.call_tool(
            "search_capabilities",
            {"query": "skill telemetry", "limit": 20},
        )
    )
    telemetry_operations = {
        item["operation_name"]: item
        for item in telemetry_search.structured_content["operations"]
    }
    assert telemetry_operations["record_skill_outcome"]["effects"] == ["local_change"]
    assert telemetry_operations["skill_telemetry_report"]["effects"] == ["read_only"]


def test_unavailable_mounted_provider_is_status_visible_but_not_recommended() -> None:
    composed = compose_gateway(
        load_runtime_config(),
        validate_provider=False,
        provider_service=service(),
        provider_runtime_settings=runtime_settings(),
        create_proxy_fn=lambda *_args, **_kwargs: FastMCP("provider-readiness"),
    )

    status = asyncio.run(composed.server.call_tool("kis_provider_status", {})).structured_content
    assert status is not None
    github = next(item for item in status["external_providers"] if item["provider_id"] == "github-mcp")
    assert github["mounted"] is True

    search = asyncio.run(
        composed.server.call_tool(
            "search_capabilities", {"query": "github echo", "limit": 20}
        )
    ).structured_content
    assert search is not None
    match = next(item for item in search["operations"] if item["operation_name"] == "github_echo")
    assert match["readiness"] == "unavailable"
    assert match["eligible"] is False


def test_server_module_is_thin_compatibility_facade() -> None:
    from kis_mcp import server

    source = inspect.getsource(server)
    assert "def build_server" in source
    assert "compose_gateway" in source
    assert "register_discover_tools" not in source
    assert "compose_provider_runtime" not in source
    assert len(source.splitlines()) <= 80



def test_capability_search_returns_workflow_without_optional_skill_fixture() -> None:
    composed = compose_gateway(
        load_runtime_config(),
        validate_provider=False,
        provider_service=service(),
        provider_runtime_settings=runtime_settings(),
        create_proxy_fn=lambda *_args, **_kwargs: FastMCP("cross-domain-search"),
    )

    payload = asyncio.run(
        composed.server.call_tool(
            "search_capabilities", {"query": "modularity", "limit": 20}
        )
    ).structured_content

    assert payload is not None
    assert any(
        item["workflow_id"] == "assess-repository-modularity"
        for item in payload["workflows"]
    )