from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from fastmcp import FastMCP

from .runtime_settings import ProviderRuntimeSettings
from .service import ProviderService


RUNTIME_SCHEMA_VERSION = 1
_NOT_VERIFIED = "not_verified"


class ProviderMountState(StrEnum):
    DISABLED = "disabled"
    UNREGISTERED = "unregistered"
    BUILD_FAILED = "build_failed"
    INVALID_BUILDER_RESULT = "invalid_builder_result"
    MOUNT_FAILED = "mount_failed"
    MOUNTED = "mounted"


@dataclass(frozen=True, slots=True)
class ProviderMountResult:
    provider_id: str
    namespace: str
    registered: bool
    enabled: bool
    build_attempted: bool
    built: bool
    mounted: bool
    state: ProviderMountState
    error_type: str | None = None
    schema_version: int = RUNTIME_SCHEMA_VERSION

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "namespace": self.namespace,
            "registered": self.registered,
            "enabled": self.enabled,
            "build_attempted": self.build_attempted,
            "built": self.built,
            "mounted": self.mounted,
            "state": self.state.value,
            "error_type": self.error_type,
        }


@dataclass(frozen=True, slots=True)
class ProviderRuntimeComposition:
    results: tuple[ProviderMountResult, ...]
    schema_version: int = RUNTIME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RUNTIME_SCHEMA_VERSION:
            raise ValueError("provider runtime composition schema_version must be 1")
        if any(not isinstance(item, ProviderMountResult) for item in self.results):
            raise ValueError("results must contain ProviderMountResult values")
        provider_ids = [item.provider_id for item in self.results]
        if len(set(provider_ids)) != len(provider_ids):
            raise ValueError("results must contain unique provider_id values")
        object.__setattr__(
            self,
            "results",
            tuple(sorted(self.results, key=lambda item: item.provider_id)),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "results": [item.to_json_dict() for item in self.results],
        }


def _mount_result(
    *,
    provider_id: str,
    namespace: str,
    registered: bool,
    enabled: bool,
    build_attempted: bool,
    built: bool,
    mounted: bool,
    state: ProviderMountState,
    error_type: str | None = None,
) -> ProviderMountResult:
    return ProviderMountResult(
        provider_id=provider_id,
        namespace=namespace,
        registered=registered,
        enabled=enabled,
        build_attempted=build_attempted,
        built=built,
        mounted=mounted,
        state=state,
        error_type=error_type,
    )


def compose_provider_runtime(
    server: FastMCP,
    service: ProviderService,
    settings: ProviderRuntimeSettings,
) -> ProviderRuntimeComposition:
    results: list[ProviderMountResult] = []

    for setting in settings.providers:
        if not service.registry.contains(setting.provider_id):
            results.append(
                _mount_result(
                    provider_id=setting.provider_id,
                    namespace=setting.namespace,
                    registered=False,
                    enabled=setting.enabled,
                    build_attempted=False,
                    built=False,
                    mounted=False,
                    state=ProviderMountState.UNREGISTERED,
                )
            )
            continue

        if not setting.enabled:
            results.append(
                _mount_result(
                    provider_id=setting.provider_id,
                    namespace=setting.namespace,
                    registered=True,
                    enabled=False,
                    build_attempted=False,
                    built=False,
                    mounted=False,
                    state=ProviderMountState.DISABLED,
                )
            )
            continue

        try:
            provider = service.build(setting.provider_id)
        except Exception as exc:
            results.append(
                _mount_result(
                    provider_id=setting.provider_id,
                    namespace=setting.namespace,
                    registered=True,
                    enabled=True,
                    build_attempted=True,
                    built=False,
                    mounted=False,
                    state=ProviderMountState.BUILD_FAILED,
                    error_type=type(exc).__name__,
                )
            )
            continue

        if not isinstance(provider, FastMCP):
            results.append(
                _mount_result(
                    provider_id=setting.provider_id,
                    namespace=setting.namespace,
                    registered=True,
                    enabled=True,
                    build_attempted=True,
                    built=False,
                    mounted=False,
                    state=ProviderMountState.INVALID_BUILDER_RESULT,
                    error_type=type(provider).__name__,
                )
            )
            continue

        try:
            server.mount(provider, namespace=setting.namespace)
        except Exception as exc:
            results.append(
                _mount_result(
                    provider_id=setting.provider_id,
                    namespace=setting.namespace,
                    registered=True,
                    enabled=True,
                    build_attempted=True,
                    built=True,
                    mounted=False,
                    state=ProviderMountState.MOUNT_FAILED,
                    error_type=type(exc).__name__,
                )
            )
            continue

        results.append(
            _mount_result(
                provider_id=setting.provider_id,
                namespace=setting.namespace,
                registered=True,
                enabled=True,
                build_attempted=True,
                built=True,
                mounted=True,
                state=ProviderMountState.MOUNTED,
            )
        )

    return ProviderRuntimeComposition(results=tuple(results))


def provider_runtime_status(
    service: ProviderService,
    composition: ProviderRuntimeComposition,
) -> dict[str, Any]:
    health = service.health()
    readiness_by_provider = {
        item.provider_id: item.to_json_dict() for item in health.providers
    }
    external_providers: list[dict[str, Any]] = []

    for result in composition.results:
        provider = result.to_json_dict()
        provider["readiness"] = readiness_by_provider.get(result.provider_id)
        provider["commissioning"] = {
            "installed": _NOT_VERIFIED,
            "configured": _NOT_VERIFIED,
            "authenticated": _NOT_VERIFIED,
            "upstream_connected": _NOT_VERIFIED,
            "tools_discovered": _NOT_VERIFIED,
            "live_verified": _NOT_VERIFIED,
        }
        external_providers.append(provider)

    return {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "platform_health": health.to_json_dict(),
        "external_providers": external_providers,
    }


__all__ = [
    "ProviderMountResult",
    "ProviderMountState",
    "ProviderRuntimeComposition",
    "RUNTIME_SCHEMA_VERSION",
    "compose_provider_runtime",
    "provider_runtime_status",
]
