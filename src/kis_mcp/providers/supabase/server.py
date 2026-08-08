from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx
from fastmcp import Client, FastMCP
from fastmcp.client.auth import OAuth
from fastmcp.client.transports import StreamableHttpTransport

from kis_mcp.projects import ProjectRegistry, load_project_registry_settings
from kis_mcp.providers.client_runtime import (
    PersistentClientProxyProvider,
    ProviderRuntimeToolState,
    ProviderStartupPhase,
    ProviderStartupState,
)

from ..contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from ..registry import ProviderRegistry
from .config import (
    SupabaseProviderConfig,
    SupabaseProviderConfigError,
    load_supabase_provider_config,
)
from .routing import SupabaseProjectRouting, SupabaseProjectRoutingMiddleware
from .runtime import (
    SupabaseProviderRuntimeError,
    build_oauth_token_storage,
    build_upstream_url,
    legacy_pat_conflict,
    provider_readiness as provider_specific_readiness,
)


class SupabaseOAuth(OAuth):
    """Adapt Supabase DCR responses that omit their required secret auth method."""

    async def _exchange_token_authorization_code(
        self,
        auth_code: str,
        code_verifier: str,
        *,
        token_data: dict[str, Any] | None = None,
    ) -> httpx.Request:
        client_info = self.context.client_info
        if (
            client_info is not None
            and client_info.client_secret
            and client_info.token_endpoint_auth_method in (None, "none")
        ):
            client_info = client_info.model_copy(
                update={"token_endpoint_auth_method": "client_secret_post"}
            )
            self.context.client_info = client_info
            await self.context.storage.set_client_info(client_info)
        return await super()._exchange_token_authorization_code(
            auth_code,
            code_verifier,
            token_data=token_data,
        )


def build_transport(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
) -> StreamableHttpTransport:
    if legacy_pat_conflict(config, environment):
        raise SupabaseProviderRuntimeError(
            "SUPABASE_LEGACY_PAT_CONFLICT: remove the legacy PAT environment "
            "variable before starting browser OAuth"
        )
    upstream_url = build_upstream_url(config)
    oauth = SupabaseOAuth(
        mcp_url=upstream_url,
        client_name=config.client_name,
        token_storage=build_oauth_token_storage(config),
        additional_client_metadata={
            "token_endpoint_auth_method": "client_secret_post"
        },
        callback_host=config.callback_host,
        callback_timeout=float(config.callback_timeout_seconds),
    )
    return StreamableHttpTransport(
        url=upstream_url,
        auth=oauth,
        verify=config.verify_tls,
    )


def build_server(
    config: SupabaseProviderConfig | None = None,
    environment: Mapping[str, str] | None = None,
    *,
    project_registry: ProjectRegistry | None = None,
    client_factory: Callable[[Any], Any] = Client,
    startup_state: ProviderStartupState | None = None,
    runtime_tools: ProviderRuntimeToolState | None = None,
) -> FastMCP:
    runtime = config or load_supabase_provider_config()
    runtime_environment = environment if environment is not None else os.environ
    readiness = provider_specific_readiness(runtime, runtime_environment)
    server = FastMCP(runtime.server_name)
    shared_startup_state = startup_state or ProviderStartupState()
    shared_runtime_tools = runtime_tools or ProviderRuntimeToolState()

    if readiness.ready:
        transport = build_transport(runtime, runtime_environment)
        provider = PersistentClientProxyProvider(
            client_factory(transport),
            startup_state=shared_startup_state,
            runtime_tools=shared_runtime_tools,
        )
        server.add_provider(provider)
        projects = project_registry or load_project_registry_settings()
        server.add_middleware(
            SupabaseProjectRoutingMiddleware(
                SupabaseProjectRouting(projects, shared_runtime_tools.snapshot)
            )
        )

    @server.tool
    def kis_supabase_health() -> dict[str, object]:
        """Report redacted Supabase account OAuth and routing readiness."""

        return readiness.as_dict()

    return server


def provider_health(
    config: SupabaseProviderConfig | None = None,
    environment: Mapping[str, str] | None = None,
    startup_state: ProviderStartupState | None = None,
) -> ProviderReadiness:
    """Return account-OAuth preflight and runtime-lifetime connection readiness."""

    runtime = config or load_supabase_provider_config()
    runtime_environment = environment if environment is not None else os.environ
    readiness = provider_specific_readiness(runtime, runtime_environment)
    phase = ProviderStartupPhase.IDLE if startup_state is None else startup_state.phase

    if readiness.legacy_pat_conflict:
        state = ProviderState.DEGRADED
        summary = "Supabase MCP configuration conflicts with the commissioned OAuth flow."
        user_status = {
            "state": "configuration_conflict",
            "label": "Action required — remove legacy PAT",
            "required_action": "Remove SUPABASE_ACCESS_TOKEN before using account OAuth.",
        }
        commissioning = {
            "installed": "ready",
            "configured": "conflict",
            "authenticated": "blocked_configuration",
            "upstream_connected": "blocked_configuration",
            "tools_discovered": "blocked_configuration",
            "live_verified": "blocked_configuration",
        }
    elif not readiness.token_storage_available:
        state = ProviderState.DEGRADED
        summary = "Supabase MCP requires Windows credential storage for OAuth."
        user_status = {
            "state": "credential_storage_required",
            "label": "Unavailable — credential storage required",
            "required_action": "Restore Windows credential storage before authenticating with Supabase.",
        }
        commissioning = {
            "installed": "ready",
            "configured": "credential_storage_required",
            "authenticated": "blocked_credential_storage",
            "upstream_connected": "blocked_credential_storage",
            "tools_discovered": "blocked_credential_storage",
            "live_verified": "blocked_credential_storage",
        }
    elif phase is ProviderStartupPhase.FAILED:
        state = ProviderState.DEGRADED
        summary = "Supabase MCP runtime connection failed during account OAuth startup."
        user_status = {
            "state": "runtime_start_failed",
            "label": "Unavailable — runtime connection failed",
            "required_action": "Retry Supabase OAuth startup and inspect the provider error type if it fails again.",
        }
        commissioning = {
            "installed": "ready",
            "configured": "ready",
            "authenticated": "failed",
            "upstream_connected": "failed",
            "tools_discovered": "failed",
            "live_verified": "blocked_runtime_failure",
        }
    elif phase is ProviderStartupPhase.READY:
        state = ProviderState.READY
        summary = "Supabase MCP is authenticated for the current KIS runtime."
        user_status = {
            "state": "ready_authenticated",
            "label": "Ready — authenticated",
            "required_action": "No authentication action is required for this running KIS runtime.",
        }
        commissioning = {
            "installed": "ready",
            "configured": "ready",
            "authenticated": "ready",
            "upstream_connected": "ready",
            "tools_discovered": "ready",
            "live_verified": "pending_registered_project_read",
        }
    else:
        state = ProviderState.READY
        summary = "Supabase MCP is ready; one account OAuth login is required at runtime start."
        user_status = {
            "state": "ready_authentication_required",
            "label": "Ready — authentication required",
            "required_action": "Sign in once; registered project calls then reuse the runtime-scoped connection.",
        }
        commissioning = {
            "installed": "ready",
            "configured": "ready",
            "authenticated": "required_at_runtime_start",
            "upstream_connected": "pending_authentication",
            "tools_discovered": "pending_authentication",
            "live_verified": "pending_authentication",
        }

    details = readiness.as_dict()
    details.pop("provider_id")
    details.pop("server_name")
    details.pop("ready")
    details["upstream_ready"] = readiness.ready
    details["runtime_phase"] = phase.value
    details["runtime_error_type"] = None if startup_state is None else startup_state.error_type
    details["user_status"] = user_status
    details["commissioning"] = commissioning
    return ProviderReadiness(
        provider_id=runtime.provider_id,
        state=state,
        summary=summary,
        details=details,
    )


def build_provider_descriptor(
    config: SupabaseProviderConfig | None = None,
) -> ProviderDescriptor:
    """Build the shared descriptor without loading configuration at import time."""

    runtime = config or load_supabase_provider_config()
    startup_state = ProviderStartupState()
    runtime_tools = ProviderRuntimeToolState()
    return ProviderDescriptor(
        provider_id=runtime.provider_id,
        display_name="Supabase MCP",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=runtime.source_repository,
        source_revision=runtime.source_revision,
        capabilities=(
            ProviderCapability(
                capability_id="database.manage",
                description=(
                    "Use the official account-scoped Supabase MCP surface with "
                    "registered per-call project routing."
                ),
                effects=("database_read", "database_write", "external_network"),
            ),
        ),
        builder=lambda: build_server(
            runtime,
            startup_state=startup_state,
            runtime_tools=runtime_tools,
        ),
        readiness_probe=lambda: provider_health(
            runtime,
            startup_state=startup_state,
        ),
        runtime_tools_probe=runtime_tools.snapshot,
    )


def register_provider(
    registry: ProviderRegistry,
    config: SupabaseProviderConfig | None = None,
) -> ProviderDescriptor | None:
    """Register Supabase when configuration is valid; otherwise leave it absent."""

    try:
        descriptor = build_provider_descriptor(config)
    except SupabaseProviderConfigError:
        return None
    return registry.register(descriptor)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m kis_mcp.providers.supabase",
        description="Run or inspect the standalone kis-mcp Supabase MCP provider.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate configuration and print redacted OAuth preflight readiness.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    config: SupabaseProviderConfig | None = None,
) -> int:
    arguments = _argument_parser().parse_args(argv)
    runtime = config or load_supabase_provider_config()
    if arguments.check:
        print(
            json.dumps(
                provider_specific_readiness(runtime, os.environ).as_dict(),
                sort_keys=True,
            )
        )
        return 0

    server = build_server(runtime, os.environ)
    server.run(transport=runtime.downstream_transport)
    return 0


__all__ = [
    "build_provider_descriptor",
    "build_server",
    "build_transport",
    "main",
    "provider_health",
    "register_provider",
]
