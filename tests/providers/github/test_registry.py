from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from kis_mcp.provider_registry import ProviderDescriptor, ProviderRegistry


def _descriptor(provider_id: str = "github-mcp") -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=provider_id,
        provider_kind="connector",
        boundary="approved_external_connector",
        authoritative_source="https://github.com/github/github-mcp-server",
        source_revision="3" * 40,
        builder=lambda: object(),
    )


def test_registry_registers_and_lists_providers_deterministically() -> None:
    registry = ProviderRegistry()
    github = _descriptor("github-mcp")
    other = _descriptor("another-provider")

    registry.register(github)
    registry.register(other)

    assert registry.get("github-mcp") is github
    assert [item.provider_id for item in registry.list()] == [
        "another-provider",
        "github-mcp",
    ]


def test_registry_rejects_duplicate_provider_ids() -> None:
    registry = ProviderRegistry()
    registry.register(_descriptor())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_descriptor())


def test_provider_descriptor_is_immutable() -> None:
    descriptor = _descriptor()

    with pytest.raises(FrozenInstanceError):
        descriptor.provider_id = "changed"  # type: ignore[misc]
