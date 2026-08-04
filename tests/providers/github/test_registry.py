from __future__ import annotations

from kis_mcp import provider_registry as compatibility_registry
from kis_mcp.providers import ProviderDescriptor, ProviderRegistry


def test_root_provider_registry_is_a_compatibility_shim() -> None:
    assert compatibility_registry.ProviderDescriptor is ProviderDescriptor
    assert compatibility_registry.ProviderRegistry is ProviderRegistry
