from __future__ import annotations

import os
from collections.abc import Mapping

from ..contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from ..registry import ProviderRegistry
from .client import NvidiaNimClient
from .settings import NvidiaSettings


def _profile_details(settings: NvidiaSettings) -> dict[str, object]:
    return {
        alias: {"model": profile.model, "guidance": profile.guidance}
        for alias, profile in settings.profiles.items()
    }


def nvidia_provider_descriptor(
    settings: NvidiaSettings,
    *,
    environ: Mapping[str, str] | None = None,
) -> ProviderDescriptor:
    environment = os.environ if environ is None else environ

    def readiness() -> ProviderReadiness:
        if not settings.enabled:
            return ProviderReadiness(
                provider_id="nvidia-nim",
                state=ProviderState.DISABLED,
                summary="NVIDIA NIM is disabled by agent settings.",
            )
        if not environment.get(settings.api_key_env, "").strip():
            return ProviderReadiness(
                provider_id="nvidia-nim",
                state=ProviderState.DEGRADED,
                summary="NVIDIA NIM is ready for an API key.",
                details={"api_key_env": settings.api_key_env},
            )
        return ProviderReadiness(
            provider_id="nvidia-nim",
            state=ProviderState.READY,
            summary="NVIDIA NIM configuration and API key reference are ready.",
            details={
                "default_profile": settings.default_profile,
                "profiles": _profile_details(settings),
            },
        )

    def build() -> NvidiaNimClient:
        api_key = environment.get(settings.api_key_env, "").strip()
        return NvidiaNimClient(settings, api_key=api_key)

    return ProviderDescriptor(
        provider_id="nvidia-nim",
        display_name="NVIDIA NIM",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source="https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html",
        source_revision="openai-compatible-v1",
        capabilities=(
            ProviderCapability(
                capability_id="llm.inference.nvidia-nim",
                description="Run bounded advisory inference through NVIDIA NIM.",
                effects=("external_network",),
                tool_names=(),
            ),
        ),
        builder=build,
        readiness_probe=readiness,
        enabled=settings.enabled,
    )


def register_nvidia_provider(
    registry: ProviderRegistry,
    *,
    settings: NvidiaSettings,
    environ: Mapping[str, str] | None = None,
) -> ProviderDescriptor:
    return registry.register(
        nvidia_provider_descriptor(settings, environ=environ)
    )


__all__ = ["nvidia_provider_descriptor", "register_nvidia_provider"]
