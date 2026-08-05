from __future__ import annotations

from kis_mcp.providers import ProviderDescriptor, ProviderRegistry


def test_provider_registry_is_exposed_from_canonical_provider_package() -> None:
    registry = ProviderRegistry()

    assert registry.list() == ()
    assert ProviderDescriptor.__module__ == "kis_mcp.providers.contracts"
