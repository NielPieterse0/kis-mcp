from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, cast

from fastmcp import Client
from fastmcp.server.providers.proxy import ProxyProvider


class ProviderClient(Protocol):
    async def __aenter__(self) -> ProviderClient: ...

    async def __aexit__(self, *args: object) -> None: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> object: ...

    async def list_tools(self) -> Sequence[Any]: ...


class ProviderStartupPhase(StrEnum):
    IDLE = "idle"
    STARTING = "starting"
    READY = "ready"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass(slots=True)
class ProviderStartupState:
    """Small provider-neutral state record for one shared client lifecycle."""

    phase: ProviderStartupPhase = ProviderStartupPhase.IDLE
    error_type: str | None = None
    protocol_mode: str | None = None
    protocol_version: str | None = None

    def mark_starting(self) -> None:
        self.phase = ProviderStartupPhase.STARTING
        self.error_type = None
        self.protocol_mode = None
        self.protocol_version = None

    def mark_protocol(self, *, mode: str, version: str | None) -> None:
        self.protocol_mode = mode
        self.protocol_version = version

    def mark_ready(self) -> None:
        self.phase = ProviderStartupPhase.READY
        self.error_type = None

    def mark_failed(self, error_type: str) -> None:
        self.phase = ProviderStartupPhase.FAILED
        self.error_type = error_type

    def mark_stopped(self) -> None:
        self.phase = ProviderStartupPhase.STOPPED
        self.error_type = None


class ProviderRuntimeToolState:
    """Publish an immutable snapshot of tools discovered by a running provider."""

    def __init__(self) -> None:
        self._tools: tuple[Any, ...] = ()

    def publish(self, tools: Sequence[Any]) -> None:
        self._tools = tuple(tools)

    def snapshot(self) -> tuple[Any, ...]:
        return self._tools


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

    Before the provider lifespan starts, component discovery is intentionally
    empty so aggregate gateway construction cannot create a disposable upstream
    process. The lifespan then opens one shared client, runs startup and initial
    tool discovery, and nested proxy calls reuse that connection until shutdown.
    """

    def __init__(
        self,
        client: ProviderClient,
        *,
        startup_call: ProviderStartupCall | None = None,
        startup_state: ProviderStartupState | None = None,
        runtime_tools: ProviderRuntimeToolState | None = None,
        cache_ttl: float | None = None,
    ) -> None:
        self.client = client
        self.startup_call = startup_call
        self.startup_state = startup_state or ProviderStartupState()
        self.runtime_tools = runtime_tools or ProviderRuntimeToolState()
        super().__init__(
            cast(Any, self.client_factory),
            cache_ttl=cache_ttl,
        )

    def client_factory(self) -> Client:
        return cast(Client, self.client)

    async def _list_tools(self):
        if self.startup_state.phase is not ProviderStartupPhase.READY:
            return []
        return await super()._list_tools()

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        self.startup_state.mark_starting()
        try:
            async with self.client:
                if self.startup_call is not None:
                    await self.client.call_tool(
                        self.startup_call.tool_name,
                        dict(self.startup_call.arguments),
                    )
                self.runtime_tools.publish(await self.client.list_tools())
                self.startup_state.mark_ready()
                try:
                    yield
                finally:
                    self.startup_state.mark_stopped()
        except Exception as exc:
            if self.startup_state.phase is ProviderStartupPhase.STARTING:
                self.startup_state.mark_failed(type(exc).__name__)
            raise


__all__ = [
    "PersistentClientProxyProvider",
    "ProviderRuntimeToolState",
    "ProviderStartupCall",
    "ProviderStartupPhase",
    "ProviderStartupState",
]
