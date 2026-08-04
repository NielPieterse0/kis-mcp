from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.shared.auth import OAuthClientInformationFull

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
from kis_mcp.providers.supabase.runtime import (
    SupabaseProviderRuntimeError,
    provider_readiness,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG = load_supabase_provider_config(REPOSITORY_ROOT)
ENVIRONMENT = {"SUPABASE_PROJECT_REF": "test-project"}


def test_transport_uses_persistent_oauth_and_tls_without_pat(monkeypatch) -> None:
    captured_oauth: dict[str, object] = {}
    captured_transport: dict[str, object] = {}
    storage = object()
    oauth = object()
    transport = object()

    monkeypatch.setattr(
        server_module,
        "build_oauth_token_storage",
        lambda config: storage,
    )

    def fake_oauth(**kwargs: object) -> object:
        captured_oauth.update(kwargs)
        return oauth

    def fake_transport(**kwargs: object) -> object:
        captured_transport.update(kwargs)
        return transport

    monkeypatch.setattr(server_module, "SupabaseOAuth", fake_oauth)
    monkeypatch.setattr(server_module, "StreamableHttpTransport", fake_transport)

    result = server_module.build_transport(CONFIG, ENVIRONMENT)

    assert result is transport
    assert captured_oauth == {
        "mcp_url": "https://mcp.supabase.com/mcp?project_ref=test-project",
        "client_name": "kis-mcp Supabase",
        "token_storage": storage,
        "additional_client_metadata": {
            "token_endpoint_auth_method": "client_secret_post"
        },
        "callback_host": "localhost",
        "callback_timeout": 300.0,
    }
    assert captured_transport == {
        "url": "https://mcp.supabase.com/mcp?project_ref=test-project",
        "auth": oauth,
        "verify": True,
    }


def test_supabase_oauth_normalizes_secret_bearing_dcr_client(monkeypatch) -> None:
    stored_client_info: list[OAuthClientInformationFull] = []
    observed: dict[str, object] = {}
    response = object()

    class FakeStorage:
        async def set_client_info(
            self,
            client_info: OAuthClientInformationFull,
        ) -> None:
            stored_client_info.append(client_info)

    async def fake_exchange(
        self,
        auth_code: str,
        code_verifier: str,
        *,
        token_data=None,
    ) -> object:
        observed["auth_method"] = (
            self.context.client_info.token_endpoint_auth_method
        )
        observed["auth_code"] = auth_code
        observed["code_verifier"] = code_verifier
        observed["token_data"] = token_data
        return response

    monkeypatch.setattr(
        server_module.OAuth,
        "_exchange_token_authorization_code",
        fake_exchange,
    )
    oauth = object.__new__(server_module.SupabaseOAuth)
    oauth.context = SimpleNamespace(
        client_info=OAuthClientInformationFull(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uris=["http://localhost/callback"],
            token_endpoint_auth_method=None,
        ),
        storage=FakeStorage(),
    )

    result = asyncio.run(
        oauth._exchange_token_authorization_code(
            "authorization-code",
            "code-verifier",
            token_data={"resource": "project"},
        )
    )

    assert result is response
    assert observed == {
        "auth_method": "client_secret_post",
        "auth_code": "authorization-code",
        "code_verifier": "code-verifier",
        "token_data": {"resource": "project"},
    }
    assert len(stored_client_info) == 1
    assert stored_client_info[0].client_secret == "client-secret"
    assert (
        stored_client_info[0].token_endpoint_auth_method
        == "client_secret_post"
    )


def test_transport_rejects_legacy_pat_conflict_before_oauth(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "StreamableHttpTransport",
        lambda **kwargs: pytest.fail("transport must not be built"),
    )

    with pytest.raises(
        SupabaseProviderRuntimeError,
        match="SUPABASE_LEGACY_PAT_CONFLICT",
    ):
        server_module.build_transport(
            CONFIG,
            {
                "SUPABASE_PROJECT_REF": "test-project",
                "SUPABASE_ACCESS_TOKEN": "forbidden-test-token",
            },
        )


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
    monkeypatch.setattr(
        server_module,
        "provider_specific_readiness",
        lambda config, environment: provider_readiness(
            config,
            environment,
            keyring_available=True,
        ),
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
    assert payload["authentication_mode"] == "oauth-dcr"
    assert payload["token_storage"] == "windows-keyring"
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


def test_provider_health_maps_oauth_preflight_to_shared_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "provider_specific_readiness",
        lambda config, environment: provider_readiness(
            config,
            environment,
            keyring_available=True,
        ),
    )

    missing = server_module.provider_health(CONFIG, {})
    ready = server_module.provider_health(CONFIG, ENVIRONMENT)

    assert missing.state is ProviderState.DEGRADED
    assert missing.ready is False
    assert missing.details["project_ref_present"] is False
    assert missing.details["authentication_mode"] == "oauth-dcr"
    assert ready.state is ProviderState.READY
    assert ready.ready is True
    assert ready.details["token_storage"] == "windows-keyring"
    assert "test-project" not in str(ready.to_json_dict())


def test_register_provider_explicitly_builds_descriptor_for_registry() -> None:
    registry = ProviderRegistry()

    descriptor = server_module.register_provider(registry, CONFIG)

    assert descriptor is not None
    assert registry.get("supabase") is descriptor
    assert descriptor.authoritative_source == CONFIG.source_repository
    assert descriptor.source_revision == CONFIG.source_revision


def test_register_provider_contains_invalid_configuration(monkeypatch) -> None:
    registry = ProviderRegistry()

    def fail_load():
        raise config_module.SupabaseProviderConfigError("invalid provider config")

    monkeypatch.setattr(server_module, "load_supabase_provider_config", fail_load)

    descriptor = server_module.register_provider(registry)

    assert descriptor is None
    assert registry.contains("supabase") is False


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
