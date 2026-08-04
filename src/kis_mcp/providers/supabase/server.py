from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence

from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import ProxyClient

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
from .runtime import (
    build_upstream_url,
    provider_readiness as provider_specific_readiness,
    require_runtime_credentials,
)


def build_transport(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
) -> StreamableHttpTransport:
    _, access_token = require_runtime_credentials(config, environment)
    return StreamableHttpTransport(
        url=build_upstream_url(config, environment),
        auth=access_token,
        verify=config.verify_tls,
    )


def build_server(
    config: SupabaseProviderConfig | None = None,
    environment: Mapping[str, str] | None = None,
) -> FastMCP:
    runtime = config or load_supabase_provider_config()
    runtime_environment = environment if environment is not None else os.environ
    transport = build_transport(runtime, runtime_environment)
    server = create_proxy(
        ProxyClient(transport),
        name=runtime.server_name,
    )

    @server.tool
    def kis_supabase_health() -> dict[str, object]:
        """Report redacted Supabase provider identity, scope, and readiness."""

        return provider_specific_readiness(runtime, runtime_environment).as_dict()

    return server


def provider_health(
    config: SupabaseProviderConfig | None = None,
    environment: Mapping[str, str] | None = None,
) -> ProviderReadiness:
    """Return provider-neutral, redacted readiness without network access."""

    runtime = config or load_supabase_provider_config()
    runtime_environment = environment if environment is not None else os.environ
    readiness = provider_specific_readiness(runtime, runtime_environment)
    state = ProviderState.READY if readiness.ready else ProviderState.DEGRADED
    summary = (
        "Supabase provider is ready."
        if readiness.ready
        else "Supabase provider credentials are incomplete."
    )
    details = readiness.as_dict()
    details.pop("provider_id")
    details.pop("server_name")
    details.pop("ready")
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
                    "Use the official project-scoped Supabase MCP tool surface."
                ),
                effects=("database_read", "database_write", "external_network"),
            ),
        ),
        builder=build_server,
        readiness_probe=provider_health,
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
        help="Validate configuration and print redacted readiness without network access.",
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
