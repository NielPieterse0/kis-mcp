from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from ..contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from .settings import PythonSdkSettings

VersionLookup = Callable[[str], str]
Importer = Callable[[str], Any]


def python_sdk_provider_descriptor(
    settings: PythonSdkSettings,
    *,
    version_lookup: VersionLookup = version,
    importer: Importer = import_module,
) -> ProviderDescriptor:
    def build() -> Any:
        return importer(settings.module_name)

    def readiness() -> ProviderReadiness:
        details = {
            "distribution_name": settings.distribution_name,
            "module_name": settings.module_name,
            "expected_version": settings.expected_version,
        }
        if not settings.enabled:
            return ProviderReadiness(
                provider_id="mcp-python-sdk",
                state=ProviderState.DISABLED,
                summary="MCP Python SDK provider is disabled.",
                details=details,
            )
        try:
            installed_version = version_lookup(settings.distribution_name)
        except (LookupError, PackageNotFoundError):
            return ProviderReadiness(
                provider_id="mcp-python-sdk",
                state=ProviderState.UNAVAILABLE,
                summary="MCP Python SDK distribution is unavailable.",
                details=details,
            )
        details = {**details, "installed_version": installed_version}
        if installed_version != settings.expected_version:
            return ProviderReadiness(
                provider_id="mcp-python-sdk",
                state=ProviderState.DEGRADED,
                summary="Installed MCP Python SDK version differs from the pinned version.",
                details=details,
            )
        return ProviderReadiness(
            provider_id="mcp-python-sdk",
            state=ProviderState.READY,
            summary="Pinned MCP Python SDK is available locally.",
            details=details,
        )

    return ProviderDescriptor(
        provider_id="mcp-python-sdk",
        display_name="MCP Python SDK",
        provider_kind=ProviderKind.PLATFORM,
        boundary=ProviderBoundary.PLATFORM_INTERNAL,
        authoritative_source=settings.source_repository,
        source_revision=settings.source_revision,
        capabilities=(
            ProviderCapability(
                capability_id="mcp.python.library",
                description="Provide the official pinned MCP Python SDK as a local library.",
                effects=("local_import",),
                tool_names=(settings.module_name,),
            ),
        ),
        builder=build,
        readiness_probe=readiness,
        enabled=settings.enabled,
    )


__all__ = ["python_sdk_provider_descriptor"]
