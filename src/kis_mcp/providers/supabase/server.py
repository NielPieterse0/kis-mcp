from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import ProxyClient

from .config import SupabaseProviderConfig, load_supabase_provider_config
from .runtime import (
    build_upstream_url,
    provider_readiness,
    require_runtime_credentials,
)


@dataclass(frozen=True, slots=True)
class SupabaseProviderDescriptor:
    provider_id: str
    module: str
    transport: str
    external_connector: bool


SUPABASE_PROVIDER_DESCRIPTOR = SupabaseProviderDescriptor(
    provider_id="supabase",
    module="kis_mcp.providers.supabase",
    transport="stdio",
    external_connector=True,
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

        return provider_readiness(runtime, runtime_environment).as_dict()

    return server


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
                provider_readiness(runtime, os.environ).as_dict(),
                sort_keys=True,
            )
        )
        return 0

    server = build_server(runtime, os.environ)
    server.run(transport=runtime.downstream_transport)
    return 0
