from __future__ import annotations

from collections.abc import Mapping

from ..config import RuntimeConfig
from .desktop_commander import register_desktop_commander_provider
from .github import GitHubProviderSettings, register_github_provider
from .registry import ProviderRegistry
from .service import ProviderService


def register_supabase_provider(registry: ProviderRegistry) -> None:
    """Register Supabase lazily so invalid optional config cannot break core startup."""

    try:
        from .supabase import register_provider
    except Exception as exc:
        is_configuration_error = (
            type(exc).__module__ == "kis_mcp.providers.supabase.config"
            and type(exc).__name__ == "SupabaseProviderConfigError"
        )
        if not is_configuration_error:
            raise
        return
    register_provider(registry)


def build_platform_provider_registry(
    *,
    runtime_config: RuntimeConfig | None = None,
    github_settings: GitHubProviderSettings | None = None,
    environment: Mapping[str, str] | None = None,
) -> ProviderRegistry:
    """Register approved providers explicitly without building or probing them."""

    registry = ProviderRegistry()
    register_desktop_commander_provider(registry, runtime_config)
    register_github_provider(
        registry,
        settings=github_settings,
        environ=environment,
    )
    register_supabase_provider(registry)
    return registry


def build_platform_provider_service(
    *,
    runtime_config: RuntimeConfig | None = None,
    github_settings: GitHubProviderSettings | None = None,
    environment: Mapping[str, str] | None = None,
) -> ProviderService:
    """Build the provider-neutral service over the explicit platform registry."""

    return ProviderService(
        build_platform_provider_registry(
            runtime_config=runtime_config,
            github_settings=github_settings,
            environment=environment,
        )
    )


__all__ = [
    "build_platform_provider_registry",
    "build_platform_provider_service",
]
