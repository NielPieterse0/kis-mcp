from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server import create_proxy

from .config import RuntimeConfig, load_runtime_config
from .gateway.composition import compose_gateway
from .gateway.foundation import (
    provider_environment as _provider_environment,
    quarantine_response as _quarantine_response,
)
from .provider_readiness import validate_provider_offline_readiness
from .providers.runtime_settings import ProviderRuntimeSettings
from .providers.service import ProviderService


def build_server(
    config: RuntimeConfig | None = None,
    *,
    validate_provider: bool = True,
    provider_service: ProviderService | None = None,
    provider_runtime_settings: ProviderRuntimeSettings | None = None,
) -> FastMCP:
    return compose_gateway(
        config,
        validate_provider=validate_provider,
        provider_service=provider_service,
        provider_runtime_settings=provider_runtime_settings,
        create_proxy_fn=create_proxy,
        provider_validator_fn=validate_provider_offline_readiness,
    ).server


def main() -> None:
    config = load_runtime_config()
    build_server(config).run(transport=config.transport)


if __name__ == "__main__":
    main()
