from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ...control_center.app import build_control_center_server
from ...control_center.settings import (
    ControlCenterSettingsError,
    load_control_center_settings,
)
from ...control_center.snapshot import ControlCenterSnapshotService
from ..contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from ..registry import ProviderRegistry

ProviderStatusSource = Callable[[], Mapping[str, Any]]


def control_center_provider_descriptor(
    *,
    provider_status_source: ProviderStatusSource | None = None,
    settings_path: str | Path | None = None,
) -> ProviderDescriptor:
    """Describe the local read-only Control Center MCP App provider."""

    def readiness() -> ProviderReadiness:
        try:
            settings = load_control_center_settings(settings_path)
        except ControlCenterSettingsError as exc:
            return ProviderReadiness(
                provider_id="control-center",
                state=ProviderState.UNAVAILABLE,
                summary="Control Center settings are unavailable.",
                details={"error_type": type(exc).__name__},
            )
        return ProviderReadiness(
            provider_id="control-center",
            state=ProviderState.READY,
            summary="Local read-only operational dashboard is ready to mount.",
            details={
                "project_configured": bool(str(settings.project_path)),
                "discover_enabled": settings.discover_enabled,
            },
        )

    def build() -> Any:
        settings = load_control_center_settings(settings_path)
        service = ControlCenterSnapshotService(
            settings,
            provider_status_source=provider_status_source,
        )
        return build_control_center_server(
            settings=settings,
            snapshot_service=service,
            app_resource_uri="ui://controlcenter/kis-mcp/control-center.html",
        )

    return ProviderDescriptor(
        provider_id="control-center",
        display_name="KIS Control Center",
        provider_kind=ProviderKind.PLATFORM,
        boundary=ProviderBoundary.LOCAL_READ_ONLY,
        authoritative_source="repository:src/kis_mcp/control_center",
        source_revision="1",
        capabilities=(
            ProviderCapability(
                capability_id="operations.dashboard",
                description=(
                    "Read-only local operational dashboard with structured fallback content."
                ),
                effects=("reads_local_status",),
                tool_names=("open_kis_control_center",),
            ),
        ),
        builder=build,
        readiness_probe=readiness,
    )


def register_control_center_provider(
    registry: ProviderRegistry,
    *,
    provider_status_source: ProviderStatusSource | None = None,
    settings_path: str | Path | None = None,
) -> ProviderDescriptor:
    """Register Control Center with live evidence from this provider registry."""

    return registry.register(
        control_center_provider_descriptor(
            provider_status_source=provider_status_source or (lambda: {"external_providers": []}),
            settings_path=settings_path,
        )
    )


__all__ = [
    "ProviderStatusSource",
    "control_center_provider_descriptor",
    "register_control_center_provider",
]
