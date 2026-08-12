from __future__ import annotations

from collections.abc import Mapping

from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import ProxyClient
from fastmcp.tools.tool_transform import ToolTransformConfig

from .settings import ALL_TOOLS, PUBLIC_TOOLS, DockerHubSettings

INTERNAL_PAT_ENV = "KIS_MCP_DOCKERHUB_PAT"


def _proxy(command: str, arguments: tuple[str, ...], environment: dict[str, str]) -> FastMCP:
    transport = StdioTransport(command=command, args=list(arguments), cwd=None, env=environment)
    return create_proxy(ProxyClient(transport), name="dockerhub-mcp")


class DockerHubAdapter:
    def __init__(self, settings: DockerHubSettings, *, environment: Mapping[str, str]) -> None:
        self.settings = settings
        self.environment = environment

    def child_environment(self) -> dict[str, str]:
        if self.settings.auth_mode == "public":
            return {}
        value = self.environment.get(INTERNAL_PAT_ENV)
        if not value:
            raise RuntimeError("DOCKERHUB_PAT_NOT_COMMISSIONED")
        return {"HUB_PAT_TOKEN": value}

    def arguments(self) -> tuple[str, ...]:
        args = [str(self.settings.entry_point), "--transport=stdio"]
        if self.settings.auth_mode == "pat":
            args.append(f"--username={self.settings.username}")
        return tuple(args)

    def build_server(self) -> FastMCP:
        server = _proxy(
            self.settings.node_executable,
            self.arguments(),
            self.child_environment(),
        )
        if self.settings.auth_mode == "public":
            for tool in sorted(set(ALL_TOOLS) - set(PUBLIC_TOOLS)):
                server.add_tool_transformation(tool, ToolTransformConfig(enabled=False))
        return server


__all__ = ["DockerHubAdapter", "INTERNAL_PAT_ENV"]
