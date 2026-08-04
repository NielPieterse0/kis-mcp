from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .contracts import (
    PUBLIC_SCHEMA_VERSION,
    ProviderDescriptor,
    ProviderReadiness,
    ProviderState,
    _require_enum,
)


@dataclass(frozen=True, slots=True)
class ProviderHealthSummary:
    state: ProviderState
    providers: tuple[ProviderReadiness, ...]
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("provider health summary schema_version must be 1")
        _require_enum(self.state, ProviderState, "state")
        if any(
            not isinstance(item, ProviderReadiness) for item in self.providers
        ):
            raise ValueError("providers must contain ProviderReadiness values")
        provider_ids = [item.provider_id for item in self.providers]
        if len(set(provider_ids)) != len(provider_ids):
            raise ValueError("providers must contain unique provider_id values")
        object.__setattr__(
            self,
            "providers",
            tuple(sorted(self.providers, key=lambda item: item.provider_id)),
        )

    @property
    def ready_count(self) -> int:
        return self._count(ProviderState.READY)

    @property
    def degraded_count(self) -> int:
        return self._count(ProviderState.DEGRADED)

    @property
    def disabled_count(self) -> int:
        return self._count(ProviderState.DISABLED)

    @property
    def unavailable_count(self) -> int:
        return self._count(ProviderState.UNAVAILABLE)

    def _count(self, state: ProviderState) -> int:
        return sum(item.state is state for item in self.providers)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "state": self.state.value,
            "ready_count": self.ready_count,
            "degraded_count": self.degraded_count,
            "disabled_count": self.disabled_count,
            "unavailable_count": self.unavailable_count,
            "providers": [item.to_json_dict() for item in self.providers],
        }


def _probe_provider(descriptor: ProviderDescriptor) -> ProviderReadiness:
    if not descriptor.enabled:
        return ProviderReadiness(
            provider_id=descriptor.provider_id,
            state=ProviderState.DISABLED,
            summary="Provider is disabled.",
        )

    try:
        readiness = descriptor.readiness_probe()
    except Exception as exc:
        return ProviderReadiness(
            provider_id=descriptor.provider_id,
            state=ProviderState.UNAVAILABLE,
            summary="Provider readiness probe failed.",
            details={"error_type": type(exc).__name__},
        )

    if readiness.provider_id != descriptor.provider_id:
        return ProviderReadiness(
            provider_id=descriptor.provider_id,
            state=ProviderState.UNAVAILABLE,
            summary="Provider readiness probe returned mismatched identity.",
            details={"reported_provider_id": readiness.provider_id},
        )
    return readiness


def _aggregate_state(readiness: tuple[ProviderReadiness, ...]) -> ProviderState:
    if not readiness:
        return ProviderState.UNAVAILABLE
    active = tuple(item for item in readiness if item.state is not ProviderState.DISABLED)
    if not active:
        return ProviderState.DISABLED
    if all(item.state is ProviderState.UNAVAILABLE for item in active):
        return ProviderState.UNAVAILABLE
    if any(
        item.state in {ProviderState.DEGRADED, ProviderState.UNAVAILABLE}
        for item in active
    ):
        return ProviderState.DEGRADED
    return ProviderState.READY


def aggregate_provider_health(
    descriptors: Iterable[ProviderDescriptor],
) -> ProviderHealthSummary:
    readiness = tuple(
        _probe_provider(descriptor)
        for descriptor in sorted(descriptors, key=lambda item: item.provider_id)
    )
    return ProviderHealthSummary(
        state=_aggregate_state(readiness),
        providers=readiness,
    )


__all__ = ["ProviderHealthSummary", "aggregate_provider_health"]
