from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from ..client_runtime import ProviderStartupPhase
from ..contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from ..registry import ProviderRegistry
from .adapter import SerenaRuntimeAdapter
from .settings import SerenaSettings


def _default_settings_path() -> Path:
    return Path(__file__).resolve().parents[4] / "settings" / "providers" / "serena.provider.json"


def load_serena_settings(path: Path | None = None) -> SerenaSettings:
    return SerenaSettings.load(path or _default_settings_path())


def serena_readiness(adapter: SerenaRuntimeAdapter) -> ProviderReadiness:
    settings = adapter.settings
    executable_present = settings.executable.is_file()
    install_present = settings.install_root.is_dir()
    phase = adapter.startup_state.phase
    if not settings.enabled:
        state = ProviderState.DISABLED
        summary = "Serena semantic provider is disabled by JSON settings."
    elif not executable_present or not install_present:
        state = ProviderState.UNAVAILABLE
        summary = "Serena pinned local installation is incomplete."
    elif phase is ProviderStartupPhase.FAILED:
        state = ProviderState.DEGRADED
        summary = "Serena failed to start; deterministic Discover fallback remains active."
    else:
        state = ProviderState.READY
        summary = "Serena pinned local semantic provider is ready with offline-only LSP startup."
    return ProviderReadiness(
        provider_id="serena-mcp",
        state=state,
        summary=summary,
        details={
            "package_version": settings.package_version,
            "source_revision": settings.source_revision,
            "executable_present": executable_present,
            "install_present": install_present,
            "runtime_phase": phase.value,
            "runtime_error_type": adapter.startup_state.error_type,
            "offline_enforced": True,
            "public_tools": [
                "get_symbols_overview",
                "find_symbol",
                "find_referencing_symbols",
            ],
            "provider_memory_is_kis_memory": False,
        },
    )


def serena_provider_descriptor(adapter: SerenaRuntimeAdapter) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id="serena-mcp",
        display_name="Serena Semantic MCP",
        provider_kind=ProviderKind.SEMANTIC,
        boundary=ProviderBoundary.LOCAL_READ_ONLY,
        authoritative_source=adapter.settings.source_repository,
        source_revision=adapter.settings.source_revision,
        capabilities=(
            ProviderCapability(
                capability_id="semantic.code.read",
                description="Read bounded semantic symbols and references through pinned Serena with deterministic Discover fallback.",
                effects=("repository_read", "local_process"),
                tool_names=(
                    "get_symbols_overview",
                    "find_symbol",
                    "find_referencing_symbols",
                ),
            ),
        ),
        builder=adapter.build_server,
        readiness_probe=lambda: serena_readiness(adapter),
        runtime_tools_probe=adapter.public_runtime_tools,
        enabled=adapter.settings.enabled,
    )


def register_serena_provider(
    registry: ProviderRegistry,
    adapter: SerenaRuntimeAdapter,
) -> ProviderDescriptor:
    return registry.register(serena_provider_descriptor(adapter))


def build_serena_adapter(
    *,
    settings: SerenaSettings | None = None,
    environment: Mapping[str, str] | None = None,
    default_project: str | None = None,
) -> SerenaRuntimeAdapter:
    return SerenaRuntimeAdapter(
        settings or load_serena_settings(),
        environment=os.environ if environment is None else environment,
        default_project=default_project,
    )


__all__ = [
    "build_serena_adapter",
    "load_serena_settings",
    "register_serena_provider",
    "serena_provider_descriptor",
    "serena_readiness",
]
