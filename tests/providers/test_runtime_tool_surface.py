from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from kis_mcp.capabilities.surface import augment_with_runtime_surface
from kis_mcp.providers import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderRegistry,
    ProviderState,
)
from kis_mcp.providers.platform import (
    provider_capability_contributions,
    provider_runtime_tools,
)
from kis_mcp.providers.serena import (
    SerenaRuntimeAdapter,
    load_serena_settings,
    serena_provider_descriptor,
)
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
        inputSchema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )

    tools = provider_runtime_tools(
        _service(upstream),
        _composition(ProviderMountState.MOUNTED),
    )

    assert len(tools) == 1
    assert tools[0].name == "github_get_file_contents"
    assert tools[0].description == upstream.description
    assert tools[0].annotations == upstream.annotations
    assert tools[0].input_schema == upstream.inputSchema
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


def test_runtime_merge_named_validation_tool_preserves_fastmcp_contract() -> None:
    parameters = {
        "type": "object",
        "properties": {
            "record": {"type": "object"},
            "trace": {"type": "object"},
            "pull_request_number": {"type": "integer"},
        },
        "required": ["record", "trace", "pull_request_number"],
    }
    tool = SimpleNamespace(
        name="project_management_merge_readiness",
        description="Evaluate exact-head traceability and pre-merge documentation readiness.",
        annotations={},
        parameters=parameters,
    )

    augmented = augment_with_runtime_surface((), (tool,), {})
    runtime = next(item for item in augmented if item.contribution_id == "runtime-surface")
    operation = next(
        item for item in runtime.operations if item.name == "project_management_merge_readiness"
    )

    assert operation.approval_required is False
    assert operation.input_schema == parameters


def test_serena_runtime_snapshot_keeps_public_semantic_operations_eligible() -> None:
    root = Path(__file__).resolve().parents[2]
    settings = load_serena_settings(root / "settings/providers/serena.provider.json")
    adapter = SerenaRuntimeAdapter(settings, environment={}, default_project=str(root))
    adapter.runtime_tools.publish(
        tuple(
            SimpleNamespace(
                name=name,
                description=f"Serena {name}",
                annotations={"readOnlyHint": True},
                inputSchema={"type": "object", "properties": {}},
            )
            for name in ("get_symbols_overview", "find_symbol", "find_referencing_symbols")
        )
    )
    registry = ProviderRegistry()
    registry.register(serena_provider_descriptor(adapter))
    service = ProviderService(registry)
    composition = ProviderRuntimeComposition(
        results=(
            ProviderMountResult(
                provider_id="serena-mcp",
                namespace="serena",
                registered=True,
                enabled=True,
                build_attempted=True,
                built=True,
                mounted=True,
                state=ProviderMountState.MOUNTED,
            ),
        )
    )
    contributions = provider_capability_contributions(service, composition)
    runtime_tools = provider_runtime_tools(service, composition)
    augmented = augment_with_runtime_surface(
        contributions,
        runtime_tools,
        {"serena-mcp": "serena"},
    )

    serena = next(item for item in augmented if item.contribution_id == "provider.serena-mcp")
    assert {item.name for item in serena.operations} == {
        "serena_get_symbols_overview",
        "serena_find_symbol",
        "serena_find_referencing_symbols",
    }
    assert all(item.enabled for item in serena.operations)
