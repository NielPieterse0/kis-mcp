from __future__ import annotations

from collections.abc import Iterable

from .contracts import ProviderDescriptor


class ProviderRegistry:
    """Deterministic registry for provider descriptors only."""

    def __init__(self, descriptors: Iterable[ProviderDescriptor] = ()) -> None:
        self._providers: dict[str, ProviderDescriptor] = {}
        for descriptor in descriptors:
            self.register(descriptor)

    def register(self, descriptor: ProviderDescriptor) -> ProviderDescriptor:
        if descriptor.provider_id in self._providers:
            raise ValueError(f"Provider is already registered: {descriptor.provider_id}")
        self._providers[descriptor.provider_id] = descriptor
        return descriptor

    def contains(self, provider_id: str) -> bool:
        return provider_id in self._providers

    def get(self, provider_id: str) -> ProviderDescriptor:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"Unknown provider: {provider_id}") from exc

    def list(self) -> tuple[ProviderDescriptor, ...]:
        return tuple(self._providers[key] for key in sorted(self._providers))

    def __len__(self) -> int:
        return len(self._providers)


__all__ = ["ProviderRegistry"]
