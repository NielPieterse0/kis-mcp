from __future__ import annotations

from types import SimpleNamespace

from kis_mcp.providers import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderRegistry,
    ProviderState,
)
from kis_mcp.providers.platform import provider_runtime_tools
from kis_mcp.providers.runtime import (
    ProviderMountResult,
    ProviderMountState,
    ProviderRuntimeComposition,
)
from kis_mcp.providers.service import ProviderService


def _service(tool: object) -> ProviderService:
    registry = ProviderRegistry()
    registry.register(
        ProviderDescriptor(
            provider_id="github-mcp",
            display_name="GitHub MCP",
            provider_kind=ProviderKind.CONNECTOR,
            boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
            authoritative_source="source:github",
            source_revision="1",
            capabilities=(
                ProviderCapability(
                    capability_id="repository.remote_read_write",
                    description="GitHub repository operations.",
                    effects=("external_network", "repository_read", "repository_write"),
                ),
            ),
            builder=lambda: object(),
            readiness_probe=lambda: ProviderReadiness(
                provider_id="github-mcp",
                state=ProviderState.READY,
                summary="Ready.",
            ),
            runtime_tools_probe=lambda: (tool,),
        )
    )
    return ProviderService(registry)


def _composition(state: ProviderMountState) -> ProviderRuntimeComposition:
    return ProviderRuntimeComposition(
        results=(
            ProviderMountResult(
                provider_id="github-mcp",
                namespace="github",
                registered=True,
                enabled=state is ProviderMountState.MOUNTED,
                build_attempted=state is ProviderMountState.MOUNTED,
                built=state is ProviderMountState.MOUNTED,
                mounted=state is ProviderMountState.MOUNTED,
                state=state,
            ),
        )
    )


def test_runtime_tools_are_namespaced_without_mutating_upstream_tool() -> None:
    upstream = SimpleNamespace(
        name="get_file_contents",
        description="Read repository contents.",
        annotations={"readOnlyHint": True},
    )

    tools = provider_runtime_tools(
        _service(upstream),
        _composition(ProviderMountState.MOUNTED),
    )

    assert len(tools) == 1
    assert tools[0].name == "github_get_file_contents"
    assert tools[0].description == upstream.description
    assert tools[0].annotations == upstream.annotations
    assert upstream.name == "get_file_contents"


def test_runtime_tools_are_absent_when_provider_is_not_mounted() -> None:
    upstream = SimpleNamespace(
        name="get_file_contents",
        description="Read repository contents.",
        annotations={"readOnlyHint": True},
    )

    assert provider_runtime_tools(
        _service(upstream),
        _composition(ProviderMountState.DISABLED),
    ) == ()
