from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from kis_mcp.providers.client_runtime import (
    PersistentClientProxyProvider,
    ProviderRuntimeToolState,
    ProviderStartupCall,
    ProviderStartupPhase,
    ProviderStartupState,
)


@dataclass(frozen=True)
class FakeTool:
    name: str
    description: str = "fake tool"
    annotations: object | None = None


class FakeClient:
    def __init__(self) -> None:
        self.nesting = 0
        self.connect_count = 0
        self.disconnect_count = 0
        self.list_tools_count = 0
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.tools = (FakeTool("get_me"), FakeTool("get_file_contents"))

    async def __aenter__(self) -> FakeClient:
        if self.nesting == 0:
            self.connect_count += 1
        self.nesting += 1
        return self

    async def __aexit__(self, *_: object) -> None:
        self.nesting -= 1
        if self.nesting == 0:
            self.disconnect_count += 1

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
        self.calls.append((name, dict(arguments)))
        return object()

    async def list_tools(self) -> tuple[FakeTool, ...]:
        self.list_tools_count += 1
        return self.tools


def test_provider_component_listing_before_lifespan_does_not_connect_upstream() -> None:
    async def scenario() -> None:
        client = FakeClient()
        provider = PersistentClientProxyProvider(
            client,
            startup_call=ProviderStartupCall("get_me"),
        )

        assert await provider._list_tools() == []
        assert client.connect_count == 0
        assert client.disconnect_count == 0
        assert client.list_tools_count == 0
        assert client.calls == []

    asyncio.run(scenario())


def test_provider_lifespan_keeps_one_client_connection_for_startup_discovery_and_nested_calls() -> None:
    async def scenario() -> None:
        client = FakeClient()
        startup = ProviderStartupState()
        runtime_tools = ProviderRuntimeToolState()
        provider = PersistentClientProxyProvider(
            client,
            startup_call=ProviderStartupCall("get_me"),
            startup_state=startup,
            runtime_tools=runtime_tools,
        )

        assert provider.client_factory() is client
        assert startup.phase is ProviderStartupPhase.IDLE
        assert runtime_tools.snapshot() == ()

        async with provider.lifespan():
            assert client.connect_count == 1
            assert client.disconnect_count == 0
            assert client.calls == [("get_me", {})]
            assert client.list_tools_count == 1
            assert startup.phase is ProviderStartupPhase.READY
            assert startup.error_type is None
            assert tuple(tool.name for tool in runtime_tools.snapshot()) == (
                "get_me",
                "get_file_contents",
            )

            async with client:
                await client.call_tool(
                    "get_file_contents", {"owner": "o", "repo": "r"}
                )

            assert client.connect_count == 1
            assert client.disconnect_count == 0

        assert startup.phase is ProviderStartupPhase.STOPPED
        assert client.disconnect_count == 1
        assert client.calls == [
            ("get_me", {}),
            ("get_file_contents", {"owner": "o", "repo": "r"}),
        ]

    asyncio.run(scenario())


def test_startup_call_and_runtime_discovery_run_once_per_provider_runtime() -> None:
    async def scenario() -> None:
        client = FakeClient()
        startup = ProviderStartupState()
        runtime_tools = ProviderRuntimeToolState()
        provider = PersistentClientProxyProvider(
            client,
            startup_call=ProviderStartupCall("get_me", {"refresh": False}),
            startup_state=startup,
            runtime_tools=runtime_tools,
        )

        async with provider.lifespan():
            async with client:
                pass
            async with client:
                pass

        assert client.calls == [("get_me", {"refresh": False})]
        assert client.list_tools_count == 1
        assert client.connect_count == 1
        assert client.disconnect_count == 1
        assert startup.phase is ProviderStartupPhase.STOPPED

        async with provider.lifespan():
            pass

        assert client.calls == [
            ("get_me", {"refresh": False}),
            ("get_me", {"refresh": False}),
        ]
        assert client.list_tools_count == 2
        assert client.connect_count == 2
        assert client.disconnect_count == 2

    asyncio.run(scenario())


def test_startup_failure_records_error_and_closes_the_client() -> None:
    class FailingClient(FakeClient):
        async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
            await super().call_tool(name, arguments)
            raise RuntimeError("authentication failed")

    async def scenario() -> None:
        client = FailingClient()
        startup = ProviderStartupState()
        runtime_tools = ProviderRuntimeToolState()
        provider = PersistentClientProxyProvider(
            client,
            startup_call=ProviderStartupCall("get_me"),
            startup_state=startup,
            runtime_tools=runtime_tools,
        )

        with pytest.raises(RuntimeError, match="authentication failed"):
            async with provider.lifespan():
                raise AssertionError("unreachable")

        assert startup.phase is ProviderStartupPhase.FAILED
        assert startup.error_type == "RuntimeError"
        assert runtime_tools.snapshot() == ()
        assert client.list_tools_count == 0
        assert client.connect_count == 1
        assert client.disconnect_count == 1

    asyncio.run(scenario())
