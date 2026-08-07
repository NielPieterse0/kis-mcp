from __future__ import annotations

from typing import Any

import pytest

from kis_mcp.providers.client_runtime import (
    PersistentClientProxyProvider,
    ProviderStartupCall,
)


class FakeClient:
    def __init__(self) -> None:
        self.nesting = 0
        self.connect_count = 0
        self.disconnect_count = 0
        self.calls: list[tuple[str, dict[str, Any]]] = []

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


@pytest.mark.asyncio
async def test_provider_lifespan_keeps_one_client_connection_for_nested_proxy_calls() -> None:
    client = FakeClient()
    provider = PersistentClientProxyProvider(
        client,
        startup_call=ProviderStartupCall("get_me"),
    )

    assert provider.client_factory() is client

    async with provider.lifespan():
        assert client.connect_count == 1
        assert client.disconnect_count == 0
        assert client.calls == [("get_me", {})]

        async with client:
            await client.call_tool("get_file_contents", {"owner": "o", "repo": "r"})

        assert client.connect_count == 1
        assert client.disconnect_count == 0

    assert client.disconnect_count == 1
    assert client.calls == [
        ("get_me", {}),
        ("get_file_contents", {"owner": "o", "repo": "r"}),
    ]


@pytest.mark.asyncio
async def test_startup_call_runs_once_per_provider_runtime() -> None:
    client = FakeClient()
    provider = PersistentClientProxyProvider(
        client,
        startup_call=ProviderStartupCall("get_me", {"refresh": False}),
    )

    async with provider.lifespan():
        async with client:
            pass
        async with client:
            pass

    assert client.calls == [("get_me", {"refresh": False})]
    assert client.connect_count == 1
    assert client.disconnect_count == 1

    async with provider.lifespan():
        pass

    assert client.calls == [
        ("get_me", {"refresh": False}),
        ("get_me", {"refresh": False}),
    ]
    assert client.connect_count == 2
    assert client.disconnect_count == 2


@pytest.mark.asyncio
async def test_startup_failure_closes_the_client() -> None:
    class FailingClient(FakeClient):
        async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
            await super().call_tool(name, arguments)
            raise RuntimeError("authentication failed")

    client = FailingClient()
    provider = PersistentClientProxyProvider(
        client,
        startup_call=ProviderStartupCall("get_me"),
    )

    with pytest.raises(RuntimeError, match="authentication failed"):
        async with provider.lifespan():
            raise AssertionError("unreachable")

    assert client.connect_count == 1
    assert client.disconnect_count == 1
