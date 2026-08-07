from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

from fastmcp import Client
from fastmcp.server.providers.proxy import ProxyProvider


class ProviderClient(Protocol):
    async def __aenter__(self) -> ProviderClient: ...

    async def __aexit__(self, *args: object) -> None: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> object: ...


@dataclass(frozen=True, slots=True)
class ProviderStartupCall:
    """One provider-specific tool call performed after the shared client connects."""

    tool_name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.tool_name, str) or not self.tool_name.strip():
            raise ValueError("tool_name must be a non-empty string")
        if not isinstance(self.arguments, Mapping):
            raise ValueError("arguments must be a mapping")
        object.__setattr__(self, "tool_name", self.tool_name.strip())
        object.__setattr__(self, "arguments", dict(self.arguments))


class PersistentClientProxyProvider(ProxyProvider):
    """Proxy one upstream MCP client for the complete parent-server lifespan.

    FastMCP clients are re-entrant. The outer provider lifespan owns the actual
    transport connection; nested proxy calls enter the same client without
    closing it until the parent server shuts down.
    """

    def __init__(
        self,
        client: ProviderClient,
        *,
        startup_call: ProviderStartupCall | None = None,
        cache_ttl: float | None = None,
    ) -> None:
        self.client = client
        self.startup_call = startup_call
        super().__init__(
            cast(Any, self.client_factory),
            cache_ttl=cache_ttl,
        )

    def client_factory(self) -> Client:
        return cast(Client, self.client)

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        async with self.client:
            if self.startup_call is not None:
                await self.client.call_tool(
                    self.startup_call.tool_name,
                    dict(self.startup_call.arguments),
                )
            yield


__all__ = [
    "PersistentClientProxyProvider",
    "ProviderStartupCall",
]
