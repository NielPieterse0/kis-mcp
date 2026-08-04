from __future__ import annotations

from pathlib import Path

import kis_mcp.providers.supabase.server as server_module
from kis_mcp.providers.supabase.config import load_supabase_provider_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG = load_supabase_provider_config(REPOSITORY_ROOT)
ENVIRONMENT = {
    "SUPABASE_PROJECT_REF": "test-project",
    "SUPABASE_ACCESS_TOKEN": "test-token",
}


def test_transport_uses_project_scope_bearer_auth_and_tls(monkeypatch) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_transport(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(server_module, "StreamableHttpTransport", fake_transport)

    transport = server_module.build_transport(CONFIG, ENVIRONMENT)

    assert transport is sentinel
    assert captured == {
        "url": "https://mcp.supabase.com/mcp?project_ref=test-project",
        "auth": "test-token",
        "verify": True,
    }


def test_server_builds_proxy_and_registers_redacted_health(monkeypatch) -> None:
    upstream_transport = object()
    proxy_client = object()
    captured: dict[str, object] = {}

    class FakeServer:
        name = CONFIG.server_name

        def __init__(self) -> None:
            self.tools: dict[str, object] = {}

        def tool(self, function):
            self.tools[function.__name__] = function
            return function

    fake_server = FakeServer()

    monkeypatch.setattr(
        server_module,
        "build_transport",
        lambda config, environment: upstream_transport,
    )

    def fake_proxy_client(transport: object) -> object:
        assert transport is upstream_transport
        return proxy_client

    def fake_create_proxy(client: object, *, name: str) -> FakeServer:
        captured.update({"client": client, "name": name})
        return fake_server

    monkeypatch.setattr(server_module, "ProxyClient", fake_proxy_client)
    monkeypatch.setattr(server_module, "create_proxy", fake_create_proxy)

    result = server_module.build_server(CONFIG, ENVIRONMENT)

    assert result is fake_server
    assert captured == {"client": proxy_client, "name": CONFIG.server_name}
    health = fake_server.tools["kis_supabase_health"]
    payload = health()
    assert payload["ready"] is True
    assert payload["project_scoped"] is True
    assert "test-token" not in str(payload)
    assert "test-project" not in str(payload)


def test_provider_descriptor_is_immutable_and_registry_ready() -> None:
    descriptor = server_module.SUPABASE_PROVIDER_DESCRIPTOR

    assert descriptor.provider_id == "supabase"
    assert descriptor.module == "kis_mcp.providers.supabase"
    assert descriptor.transport == "stdio"
    assert descriptor.external_connector is True
