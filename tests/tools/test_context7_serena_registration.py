from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from kis_mcp.contracts import ProviderCapabilities
from kis_mcp.models import InvocationEffects
from kis_mcp.tools.platform import (
    ToolMountState,
    compose_tool_runtime,
)

ROOT = Path(__file__).resolve().parents[2]


class DesktopResolverFixture:
    capabilities = ProviderCapabilities(
        network_only_tools=frozenset({"provider-feedback"}),
        direct_delete_tools=frozenset({"delete_file"}),
        unexposed_tool_arguments={"read_file": frozenset({"isUrl"})},
        unexposed_config_keys=frozenset({"blockedCommands"}),
        configuration_tool_name="set_config_value",
    )

    def resolve(self, tool_name: str, arguments: object) -> InvocationEffects:
        if tool_name == "write_file":
            return InvocationEffects(write_paths=(r"C:\Projects\file.txt",))
        return InvocationEffects()

    def observe_success(self, tool_name: str, arguments: object, result: object) -> None:
        return None


def test_tool_runtime_mounts_context7_and_serena_independently() -> None:
    server = FastMCP("root")

    def context7_factory(*_: object) -> FastMCP:
        raise RuntimeError("context7 unavailable")

    def serena_factory(*_: object) -> FastMCP:
        return FastMCP("serena-fixture")

    composition = compose_tool_runtime(
        server,
        DesktopResolverFixture(),
        project_root=Path(r"C:\Projects\kis-mcp"),
        repository_root=ROOT,
        context7_proxy_factory=context7_factory,
        serena_proxy_factory=serena_factory,
    )
    results = {item.tool_id: item for item in composition.results}

    assert results["context7-mcp"].state is ToolMountState.BUILD_FAILED
    assert results["serena-mcp"].state is ToolMountState.MOUNTED
    assert results["serena-mcp"].mounted is True


def test_composite_resolver_preserves_desktop_capabilities_and_adds_serena_delete() -> None:
    composition = compose_tool_runtime(
        FastMCP("root"),
        DesktopResolverFixture(),
        project_root=Path(r"C:\Projects\kis-mcp"),
        repository_root=ROOT,
        context7_proxy_factory=lambda *_: FastMCP("context7"),
        serena_proxy_factory=lambda *_: FastMCP("serena"),
    )
    capabilities = composition.resolver.capabilities

    assert capabilities.network_only_tools == frozenset({"provider-feedback"})
    assert capabilities.direct_delete_tools == frozenset(
        {"delete_file", "serena_delete_memory"}
    )
    assert capabilities.unexposed_tool_arguments["read_file"] == frozenset({"isUrl"})
    assert capabilities.configuration_tool_name == "set_config_value"


def test_composite_resolver_routes_only_namespaced_serena_operations() -> None:
    composition = compose_tool_runtime(
        FastMCP("root"),
        DesktopResolverFixture(),
        project_root=Path(r"C:\Projects\kis-mcp"),
        repository_root=ROOT,
        context7_proxy_factory=lambda *_: FastMCP("context7"),
        serena_proxy_factory=lambda *_: FastMCP("serena"),
    )
    resolver = composition.resolver

    assert resolver.resolve("write_file", {}) == InvocationEffects(
        write_paths=(r"C:\Projects\file.txt",)
    )
    assert resolver.resolve(
        "serena_replace_content",
        {"relative_path": "src/module.py"},
    ).write_paths == (r"C:\Projects\kis-mcp\src\module.py",)
    assert resolver.resolve(
        "context7_query-docs",
        {"libraryId": "/pytest-dev/pytest", "query": "fixtures"},
    ) == InvocationEffects()


def test_server_composition_imports_tools_platform_not_adapter_internals() -> None:
    source = (ROOT / "src" / "kis_mcp" / "server.py").read_text(encoding="utf-8")
    assert "tools.platform" in source
    assert "tools.context7" not in source
    assert "tools.serena" not in source
