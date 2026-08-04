from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


ProviderBuilder = Callable[[], Any]


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    provider_kind: str
    boundary: str
    authoritative_source: str
    source_revision: str
    builder: ProviderBuilder


class ProviderRegistry:
    """Small provider catalogue with deterministic registration semantics."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderDescriptor] = {}

    def register(self, descriptor: ProviderDescriptor) -> ProviderDescriptor:
        provider_id = descriptor.provider_id.strip()
        if not provider_id:
            raise ValueError("provider_id must be non-empty")
        if provider_id in self._providers:
            raise ValueError(f"Provider is already registered: {provider_id}")
        self._providers[provider_id] = descriptor
        return descriptor

    def get(self, provider_id: str) -> ProviderDescriptor:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"Unknown provider: {provider_id}") from exc

    def list(self) -> tuple[ProviderDescriptor, ...]:
        return tuple(self._providers[key] for key in sorted(self._providers))
