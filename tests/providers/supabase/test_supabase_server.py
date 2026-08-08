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
ENVIRONMENT: dict[str, str] = {}


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
        "mcp_url": "https://mcp.supabase.com/mcp",
        "client_name": "kis-mcp Supabase",
        "token_storage": storage,
        "additional_client_metadata": {
            "token_endpoint_auth_method": "client_secret_post"
        },
        "callback_host": "localhost",
        "callback_timeout": 300.0,
    }
    assert captured_transport == {
        "url": "https://mcp.supabase.com/mcp",
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
            {"SUPABASE_ACCESS_TOKEN": "forbidden-test-token"},
        )


def test_server_mounts_health_only_when_credential_storage_is_unavailable(
    monkeypatch,
) -> None:
    class FakeServer:
        name = CONFIG.server_name

        def __init__(self) -> None:
            self.tools: dict[str, object] = {}

        def add_provider(self, _provider: object) -> None:
            pytest.fail("upstream provider must not mount without credential storage")

        def add_middleware(self, _middleware: object) -> None:
            pytest.fail("routing middleware must not mount without upstream provider")

        def tool(self, function):
            self.tools[function.__name__] = function
            return function

    fake_server = FakeServer()
    monkeypatch.setattr(
        server_module,
        "provider_specific_readiness",
        lambda config, environment: provider_readiness(
            config,
            environment,
            keyring_available=False,
        ),
    )
    monkeypatch.setattr(server_module, "FastMCP", lambda name: fake_server)
    monkeypatch.setattr(
        server_module,
        "build_transport",
        lambda *_args, **_kwargs: pytest.fail(
            "upstream transport must not be built without credential storage"
        ),
    )

    result = server_module.build_server(CONFIG, {})

    assert result is fake_server
    payload = fake_server.tools["kis_supabase_health"]()
    assert payload["ready"] is False
    assert payload["account_scoped"] is True
    assert payload["project_routing"] == "registered_per_call"
    assert payload["token_storage_available"] is False


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
    assert callable(descriptor.builder)
    assert callable(descriptor.readiness_probe)
    assert descriptor.runtime_tools_probe is not None
    assert "account-scoped" in descriptor.capabilities[0].description
    assert "registered per-call" in descriptor.capabilities[0].description


def test_provider_health_maps_account_oauth_runtime_states(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "provider_specific_readiness",
        lambda config, environment: provider_readiness(
            config,
            environment,
            keyring_available=True,
        ),
    )

    idle = server_module.provider_health(CONFIG, {})
    startup = server_module.ProviderStartupState()
    startup.mark_ready()
    authenticated = server_module.provider_health(CONFIG, {}, startup)

    assert idle.state is ProviderState.READY
    assert idle.ready is True
    assert idle.summary == (
        "Supabase MCP is ready; one account OAuth login is required at runtime start."
    )
    assert idle.details["account_scoped"] is True
    assert idle.details["project_routing"] == "registered_per_call"
    assert idle.details["upstream_ready"] is True
    assert idle.details["runtime_phase"] == "idle"
    assert idle.details["user_status"]["state"] == "ready_authentication_required"
    assert idle.details["commissioning"] == {
        "installed": "ready",
        "configured": "ready",
        "authenticated": "required_at_runtime_start",
        "upstream_connected": "pending_authentication",
        "tools_discovered": "pending_authentication",
        "live_verified": "pending_authentication",
    }

    assert authenticated.state is ProviderState.READY
    assert authenticated.summary == (
        "Supabase MCP is authenticated for the current KIS runtime."
    )
    assert authenticated.details["runtime_phase"] == "ready"
    assert authenticated.details["user_status"]["state"] == "ready_authenticated"
    assert authenticated.details["commissioning"] == {
        "installed": "ready",
        "configured": "ready",
        "authenticated": "ready",
        "upstream_connected": "ready",
        "tools_discovered": "ready",
        "live_verified": "pending_registered_project_read",
    }


def test_provider_health_keeps_genuine_preflight_faults_degraded(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "provider_specific_readiness",
        lambda config, environment: provider_readiness(
            config,
            environment,
            keyring_available=False,
        ),
    )

    credential_storage = server_module.provider_health(CONFIG, {})

    assert credential_storage.state is ProviderState.DEGRADED
    assert credential_storage.details["user_status"] == {
        "state": "credential_storage_required",
        "label": "Unavailable — credential storage required",
        "required_action": (
            "Restore Windows credential storage before authenticating with Supabase."
        ),
    }
    assert credential_storage.details["commissioning"]["authenticated"] == (
        "blocked_credential_storage"
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
    pat_conflict = server_module.provider_health(
        CONFIG,
        {"SUPABASE_ACCESS_TOKEN": "forbidden-test-token"},
    )

    assert pat_conflict.state is ProviderState.DEGRADED
    assert pat_conflict.details["user_status"] == {
        "state": "configuration_conflict",
        "label": "Action required — remove legacy PAT",
        "required_action": "Remove SUPABASE_ACCESS_TOKEN before using account OAuth.",
    }
    assert pat_conflict.details["commissioning"]["configured"] == "conflict"
    assert "forbidden-test-token" not in str(pat_conflict.to_json_dict())


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


def test_server_uses_persistent_client_runtime_without_startup_tool_call(monkeypatch) -> None:
    upstream_transport = object()
    upstream_client = object()
    captured: dict[str, object] = {}

    class FakeServer:
        name = CONFIG.server_name

        def __init__(self) -> None:
            self.providers: list[object] = []
            self.middlewares: list[object] = []
            self.tools: dict[str, object] = {}

        def add_provider(self, provider: object) -> None:
            self.providers.append(provider)

        def add_middleware(self, middleware: object) -> None:
            self.middlewares.append(middleware)

        def tool(self, function):
            self.tools[function.__name__] = function
            return function

    class FakePersistentProvider:
        def __init__(self, client, **kwargs: object) -> None:
            captured["client"] = client
            captured.update(kwargs)
            self.startup_state = kwargs["startup_state"]
            self.runtime_tools = kwargs["runtime_tools"]

    fake_server = FakeServer()
    monkeypatch.setattr(
        server_module,
        "provider_specific_readiness",
        lambda config, environment: provider_readiness(
            config,
            environment,
            keyring_available=True,
        ),
    )
    monkeypatch.setattr(server_module, "FastMCP", lambda name: fake_server)
    monkeypatch.setattr(server_module, "build_transport", lambda *_args: upstream_transport)
    monkeypatch.setattr(server_module, "Client", lambda transport: upstream_client, raising=False)
    monkeypatch.setattr(
        server_module,
        "PersistentClientProxyProvider",
        FakePersistentProvider,
        raising=False,
    )
    monkeypatch.setattr(
        server_module,
        "create_proxy",
        lambda *_args, **_kwargs: pytest.fail("Supabase must use persistent provider lifecycle"),
        raising=False,
    )

    result = server_module.build_server(
        CONFIG,
        {},
        client_factory=lambda transport: upstream_client,
    )

    assert result is fake_server
    assert captured["client"] is upstream_client
    assert captured.get("startup_call") is None
    assert fake_server.providers
