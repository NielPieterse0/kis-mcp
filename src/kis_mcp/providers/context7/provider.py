from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from ..contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from ..registry import ProviderRegistry
from .adapter import Context7Adapter
from .settings import Context7Settings


def _default_settings_path() -> Path:
    return Path(__file__).resolve().parents[4] / "settings" / "providers" / "context7.provider.json"


def load_context7_settings(path: Path | None = None) -> Context7Settings:
    return Context7Settings.load(path or _default_settings_path())


def context7_readiness(
    settings: Context7Settings,
    environment: Mapping[str, str] | None = None,
) -> ProviderReadiness:
    source = os.environ if environment is None else environment
    executable_present = shutil.which(settings.executable) is not None
    entry_point_present = settings.entry_point.is_file()
    api_key_present = bool(str(source.get("CONTEXT7_API_KEY", "")).strip())
    if not settings.enabled:
        state = ProviderState.DISABLED
        summary = "Context7 provider is disabled by JSON settings."
    elif not executable_present or not entry_point_present:
        state = ProviderState.UNAVAILABLE
        summary = "Context7 pinned local installation is incomplete."
    else:
        state = ProviderState.READY
        summary = "Context7 pinned local MCP launcher is ready."
    return ProviderReadiness(
        provider_id="context7-mcp",
        state=state,
        summary=summary,
        details={
            "package_version": settings.package_version,
            "source_revision": settings.source_revision,
            "executable_present": executable_present,
            "entry_point_present": entry_point_present,
            "api_key_present": api_key_present,
        },
    )


def context7_provider_descriptor(
    settings: Context7Settings | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> ProviderDescriptor:
    runtime = settings or load_context7_settings()
    source = os.environ if environment is None else environment
    adapter = Context7Adapter(runtime, source)
    return ProviderDescriptor(
        provider_id="context7-mcp",
        display_name="Context7 MCP",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=runtime.source_repository,
        source_revision=runtime.source_revision,
        capabilities=(
            ProviderCapability(
                capability_id="documentation.context7.read",
                description="Resolve libraries and query current external documentation through pinned Context7 MCP.",
                effects=("external_network", "documentation_read"),
                tool_names=("resolve-library-id", "query-docs"),
            ),
        ),
        builder=adapter.build_server,
        readiness_probe=lambda: context7_readiness(runtime, source),
        enabled=runtime.enabled,
    )


def register_context7_provider(
    registry: ProviderRegistry,
    settings: Context7Settings | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> ProviderDescriptor:
    return registry.register(
        context7_provider_descriptor(settings, environment=environment)
    )


__all__ = [
    "context7_provider_descriptor",
    "context7_readiness",
    "load_context7_settings",
    "register_context7_provider",
]
