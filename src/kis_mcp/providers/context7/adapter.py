from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import ProxyClient

from .settings import Context7Settings
from .stdio import ProviderStdioCommand

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
    return create_proxy(ProxyClient(transport), name="context7-mcp")


@dataclass(frozen=True, slots=True)
class Context7Adapter:
    settings: Context7Settings
    environment: Mapping[str, str] = field(default_factory=lambda: os.environ)
    proxy_factory: ProxyFactory = _proxy_factory

    @property
    def command(self) -> ProviderStdioCommand:
        return ProviderStdioCommand(
            executable=self.settings.executable,
            arguments=(str(self.settings.entry_point), *self.settings.arguments),
            environment_names=self.settings.environment_names,
        )

    def build_server(self) -> FastMCP:
        selected = {
            name: value
            for name in self.settings.environment_names
            if (value := self.environment.get(name))
        }
        command = self.command
        return self.proxy_factory(
            command.executable,
            command.arguments,
            selected,
        )

    def __repr__(self) -> str:
        return (
            "Context7Adapter("
            f"package_version={self.settings.package_version!r}, "
            f"entry_point={str(self.settings.entry_point)!r})"
        )


__all__ = ["Context7Adapter", "ProxyFactory"]