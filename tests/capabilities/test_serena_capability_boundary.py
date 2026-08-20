from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.execution import CapabilityExecutionRouter
from kis_mcp.capabilities.runtime import CapabilityRuntimeState
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.capabilities.tools import register_capability_tools
from kis_mcp.providers.platform import (
    provider_capability_contributions,
    provider_runtime_tools,
)
from kis_mcp.providers.registry import ProviderRegistry
from kis_mcp.providers.runtime import (
    ProviderMountResult,
    ProviderMountState,
    ProviderRuntimeComposition,
)
from kis_mcp.providers.serena import (
    SerenaRuntimeAdapter,
    load_serena_settings,
    serena_provider_descriptor,
)
from kis_mcp.providers.service import ProviderService

ROOT = Path(__file__).resolve().parents[2]

APPROVED = {
    "serena_get_symbols_overview",
    "serena_find_symbol",
    "serena_find_referencing_symbols",
}
FORBIDDEN = {
    "serena_delete_memory",
    "serena_edit_memory",
    "serena_execute_shell_command",
    "serena_replace_symbol_body",
    "serena_write_memory",
}


def _runtime_with_hostile_serena_metadata() -> tuple[
    CapabilityRuntimeState, ProviderService, ProviderRuntimeComposition
]:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    adapter = SerenaRuntimeAdapter(settings, environment={}, default_project=str(ROOT))
    tool_names = (
        "get_symbols_overview",
        "find_symbol",
        "find_referencing_symbols",
        "delete_memory",
        "edit_memory",
        "execute_shell_command",
        "replace_symbol_body",
        "write_memory",
        "get_current_config",
    )
    adapter.runtime_tools.publish(
        tuple(
            SimpleNamespace(
                name=name,
                description=f"Upstream Serena tool {name}.",
                annotations={"readOnlyHint": name.startswith(("get_", "find_"))},
                inputSchema={"type": "object", "properties": {}},
            )
            for name in tool_names
        )
    )
    descriptor = serena_provider_descriptor(adapter)
    service = ProviderService(ProviderRegistry((descriptor,)))
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
    runtime = CapabilityRuntimeState.build(
        CapabilityCatalogue(contributions, ()),
        load_capability_settings(),
        runtime_tools_source=lambda: provider_runtime_tools(service, composition),
        provider_namespaces={"serena-mcp": "serena"},
    )
    return runtime, service, composition


def test_hostile_upstream_serena_metadata_cannot_expand_catalogue() -> None:
    runtime, service, composition = _runtime_with_hostile_serena_metadata()
    serena = next(
        item for item in runtime.catalogue.contributions
        if item.contribution_id == "provider.serena-mcp"
    )

    assert {item.name for item in provider_runtime_tools(service, composition)} == APPROVED
    operation_names = {item.name for item in serena.operations}
    assert operation_names == APPROVED
    assert FORBIDDEN.isdisjoint(operation_names)


def test_capability_search_hides_forbidden_serena_operations() -> None:
    runtime, _, _ = _runtime_with_hostile_serena_metadata()
    server = FastMCP("serena-capability-search")
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool(
            "search_capabilities",
            {"query": "serena delete edit shell memory symbol", "limit": 100},
        )
    ).structured_content

    assert payload is not None
    names = {item["operation_name"] for item in payload["operations"]}
    assert FORBIDDEN.isdisjoint(names)
    assert names.intersection(APPROVED)


def test_generic_dispatch_rejects_forbidden_serena_operation_even_if_callable() -> None:
    runtime, _, _ = _runtime_with_hostile_serena_metadata()
    server = FastMCP("serena-capability-dispatch")

    @server.tool(name="serena_delete_memory")
    def leaked_upstream_tool(memory_file_name: str) -> str:
        return f"deleted:{memory_file_name}"

    router = CapabilityExecutionRouter(server, runtime)
    with pytest.raises(ToolError, match="UNKNOWN_CAPABILITY_OPERATION: serena_delete_memory"):
        asyncio.run(router.execute_change("serena_delete_memory", {"memory_file_name": "x"}))
