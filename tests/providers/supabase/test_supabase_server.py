from __future__ import annotations

import importlib
from pathlib import Path

import kis_mcp.providers.supabase as supabase_module
import kis_mcp.providers.supabase.config as config_module
import kis_mcp.providers.supabase.server as server_module
from kis_mcp.providers import (
    ProviderBoundary,
    ProviderDescriptor,
    ProviderKind,
    ProviderRegistry,
    ProviderState,
)
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


def test_provider_descriptor_uses_shared_provider_contract() -> None:
    descriptor = server_module.build_provider_descriptor(CONFIG)

    assert isinstance(descriptor, ProviderDescriptor)
    assert descriptor.provider_id == "supabase"
    assert descriptor.display_name == "Supabase MCP"
    assert descriptor.provider_kind is ProviderKind.CONNECTOR
    assert descriptor.boundary is ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR
    assert descriptor.authoritative_source == CONFIG.source_repository
    assert descriptor.source_revision == CONFIG.source_revision
    assert [item.capability_id for item in descriptor.capabilities] == [
        "database.manage"
    ]
    assert descriptor.capabilities[0].effects == (
        "database_read",
        "database_write",
        "external_network",
    )
    assert descriptor.builder is server_module.build_server
    assert descriptor.readiness_probe is server_module.provider_health


def test_provider_health_maps_redacted_local_readiness_to_shared_contract() -> None:
    missing = server_module.provider_health(CONFIG, {})
    ready = server_module.provider_health(CONFIG, ENVIRONMENT)

    assert missing.state is ProviderState.DEGRADED
    assert missing.ready is False
    assert missing.details["project_ref_present"] is False
    assert missing.details["access_token_present"] is False
    assert ready.state is ProviderState.READY
    assert ready.ready is True
    assert "test-token" not in str(ready.to_json_dict())
    assert "test-project" not in str(ready.to_json_dict())


def test_register_provider_explicitly_builds_descriptor_for_registry() -> None:
    registry = ProviderRegistry()

    descriptor = server_module.register_provider(registry, CONFIG)

    assert registry.get("supabase") is descriptor
    assert descriptor.authoritative_source == CONFIG.source_repository
    assert descriptor.source_revision == CONFIG.source_revision


def test_package_exposes_shared_provider_registration_surface() -> None:
    assert supabase_module.build_provider_descriptor is server_module.build_provider_descriptor
    assert supabase_module.provider_health is server_module.provider_health
    assert supabase_module.register_provider is server_module.register_provider


def test_import_does_not_load_provider_configuration(monkeypatch) -> None:
    def fail_load(*_args, **_kwargs):
        raise AssertionError("provider configuration loaded during import")

    with monkeypatch.context() as context:
        context.setattr(config_module, "load_supabase_provider_config", fail_load)
        reloaded = importlib.reload(server_module)
        assert callable(reloaded.build_provider_descriptor)

    importlib.reload(server_module)
