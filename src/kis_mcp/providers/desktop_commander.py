from __future__ import annotations

from .contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from .registry import ProviderRegistry
from ..config import RuntimeConfig, load_runtime_config
from ..provider_readiness import validate_provider_offline_readiness


def desktop_commander_provider_readiness(
    config: RuntimeConfig | None = None,
) -> ProviderReadiness:
    """Project existing Work readiness into the shared provider contract."""

    runtime = config or load_runtime_config()
    try:
        validate_provider_offline_readiness(runtime)
    except Exception as exc:
        return ProviderReadiness(
            provider_id="desktop-commander",
            state=ProviderState.UNAVAILABLE,
            summary="Desktop Commander MCP is unavailable.",
            details={"error_type": type(exc).__name__},
        )

    return ProviderReadiness(
        provider_id="desktop-commander",
        state=ProviderState.READY,
        summary="Desktop Commander MCP is ready.",
        details={
            "package": runtime.desktop_commander_package,
            "version": runtime.desktop_commander_version,
        },
    )


def desktop_commander_provider_descriptor(
    config: RuntimeConfig | None = None,
) -> ProviderDescriptor:
    """Describe the Work backend without starting or importing its composition root."""

    runtime = config or load_runtime_config()

    def build_work_server():
        from ..server import build_server

        return build_server(runtime)

    return ProviderDescriptor(
        provider_id="desktop-commander",
        display_name="Desktop Commander MCP",
        provider_kind=ProviderKind.LOCAL_BACKEND,
        boundary=ProviderBoundary.WORK_BACKEND,
        authoritative_source=f"npm:{runtime.desktop_commander_package}",
        source_revision=runtime.desktop_commander_version,
        capabilities=(
            ProviderCapability(
                capability_id="filesystem.local",
                description="Read and write local project filesystem content through Work.",
                effects=("filesystem_read", "filesystem_write"),
            ),
            ProviderCapability(
                capability_id="editing.local",
                description="Apply local project edits through Work.",
                effects=("filesystem_write",),
            ),
            ProviderCapability(
                capability_id="search.local",
                description="Search local project content through Work.",
                effects=("filesystem_read",),
            ),
            ProviderCapability(
                capability_id="process.local",
                description="Run supervised local project processes through Work.",
                effects=("local_process",),
            ),
            ProviderCapability(
                capability_id="documents.local",
                description="Read and write local project documents through Work.",
                effects=("document_read", "document_write"),
            ),
        ),
        builder=build_work_server,
        readiness_probe=lambda: desktop_commander_provider_readiness(runtime),
    )


def register_desktop_commander_provider(
    registry: ProviderRegistry,
    config: RuntimeConfig | None = None,
) -> ProviderDescriptor:
    """Explicitly register the Desktop Commander Work backend."""

    return registry.register(desktop_commander_provider_descriptor(config))


__all__ = [
    "desktop_commander_provider_descriptor",
    "desktop_commander_provider_readiness",
    "register_desktop_commander_provider",
]
