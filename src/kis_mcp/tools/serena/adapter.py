from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import ProxyClient

from ..mcp_stdio import StdioMcpCommand
from .settings import SerenaSettings

ProxyFactory = Callable[[str, tuple[str, ...], dict[str, str]], FastMCP]


def _proxy_factory(
    command: str,
    arguments: tuple[str, ...],
    environment: dict[str, str],
) -> FastMCP:
    transport = StdioTransport(
        command=command,
        args=list(arguments),
        cwd=None,
        env=environment,
    )
    return create_proxy(ProxyClient(transport), name="serena-mcp")


@dataclass(frozen=True, slots=True)
class SerenaAdapter:
    settings: SerenaSettings
    environment: Mapping[str, str] = field(default_factory=lambda: os.environ)
    proxy_factory: ProxyFactory = _proxy_factory

    @property
    def command(self) -> StdioMcpCommand:
        return StdioMcpCommand(
            executable=str(self.settings.executable),
            arguments=self.settings.arguments,
            environment_names=self.settings.environment_names,
        )

    def _provider_environment(self) -> dict[str, str]:
        selected = {
            name: value
            for name in self.settings.environment_names
            if (value := self.environment.get(name))
        }
        selected.update(
            {
                "HOME": str(self.settings.home_root),
                "USERPROFILE": str(self.settings.home_root),
                "APPDATA": str(self.settings.home_root / "AppData" / "Roaming"),
                "LOCALAPPDATA": str(self.settings.home_root / "AppData" / "Local"),
                "TEMP": str(self.settings.temp_root),
                "TMP": str(self.settings.temp_root),
                "SERENA_USAGE_REPORTING": "false",
            }
        )
        if path_value := self.environment.get("PATH"):
            selected["PATH"] = path_value
        if system_root := self.environment.get("SYSTEMROOT"):
            selected["SYSTEMROOT"] = system_root
        if windir := self.environment.get("WINDIR"):
            selected["WINDIR"] = windir
        return selected

    def build_server(self) -> FastMCP:
        command = self.command
        return self.proxy_factory(
            command.executable,
            command.arguments,
            self._provider_environment(),
        )

    def __repr__(self) -> str:
        return (
            "SerenaAdapter("
            f"package_version={self.settings.package_version!r}, "
            f"executable={str(self.settings.executable)!r})"
        )


__all__ = ["ProxyFactory", "SerenaAdapter"]