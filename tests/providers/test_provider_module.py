from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.providers import (
    ProviderBoundary,
    ProviderCapability,
    ProviderCatalogue,
    ProviderCatalogueEntry,
    ProviderDescriptor,
    ProviderHealthSummary,
    ProviderKind,
    ProviderReadiness,
    ProviderRegistry,
    ProviderService,
    ProviderState,
    aggregate_provider_health,
)


def _builder() -> object:
    return object()


def _ready() -> ProviderReadiness:
    return ProviderReadiness(
        provider_id="github",
        state=ProviderState.READY,
        summary="GitHub provider is ready.",
        details={"tool_count": 12},
    )


def test_provider_descriptor_exposes_json_safe_provider_metadata() -> None:
    descriptor = ProviderDescriptor(
        provider_id="github",
        display_name="GitHub MCP",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source="https://github.com/github/github-mcp-server",
        source_revision="v1.2.3",
        capabilities=(
            ProviderCapability(
                capability_id="repository.remote_read",
                description="Read trusted GitHub repository evidence.",
                effects=("github-read",),
                tool_names=("get_file_contents", "list_pull_requests"),
            ),
        ),
        builder=_builder,
        readiness_probe=_ready,
    )

    assert descriptor.to_json_dict() == {
        "schema_version": 1,
        "provider_id": "github",
        "display_name": "GitHub MCP",
        "provider_kind": "connector",
        "boundary": "approved_external_connector",
        "authoritative_source": "https://github.com/github/github-mcp-server",
        "source_revision": "v1.2.3",
        "enabled": True,
        "capabilities": [
            {
                "schema_version": 1,
                "capability_id": "repository.remote_read",
                "description": "Read trusted GitHub repository evidence.",
                "effects": ["github-read"],
                "tool_names": ["get_file_contents", "list_pull_requests"],
            }
        ],
    }


def test_provider_descriptor_rejects_duplicate_capability_ids() -> None:
    capability = ProviderCapability(
        capability_id="repository.remote_read",
        description="Read trusted remote evidence.",
    )

    with pytest.raises(ValueError, match="duplicate capability_id"):
        ProviderDescriptor(
            provider_id="github",
            display_name="GitHub MCP",
            provider_kind=ProviderKind.CONNECTOR,
            boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
            authoritative_source="https://github.com/github/github-mcp-server",
            source_revision="v1.2.3",
            capabilities=(capability, capability),
            builder=_builder,
            readiness_probe=_ready,
        )


def test_provider_descriptor_rejects_invalid_provider_id() -> None:
    with pytest.raises(ValueError, match="provider_id"):
        ProviderDescriptor(
            provider_id="GitHub Provider",
            display_name="GitHub MCP",
            provider_kind=ProviderKind.CONNECTOR,
            boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
            authoritative_source="https://github.com/github/github-mcp-server",
            source_revision="v1.2.3",
            capabilities=(),
            builder=_builder,
            readiness_probe=_ready,
        )


def test_provider_descriptor_rejects_untyped_enums_and_enabled_state() -> None:
    base = {
        "provider_id": "github",
        "display_name": "GitHub MCP",
        "provider_kind": ProviderKind.CONNECTOR,
        "boundary": ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        "authoritative_source": "https://github.com/github/github-mcp-server",
        "source_revision": "v1.2.3",
        "capabilities": (),
        "builder": _builder,
        "readiness_probe": _ready,
    }

    with pytest.raises(ValueError, match="provider_kind"):
        ProviderDescriptor(**{**base, "provider_kind": "connector"})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="boundary"):
        ProviderDescriptor(
            **{**base, "boundary": "approved_external_connector"}  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="enabled"):
        ProviderDescriptor(**{**base, "enabled": 1})  # type: ignore[arg-type]


def test_provider_descriptor_rejects_non_capability_members() -> None:
    with pytest.raises(ValueError, match="capabilities"):
        ProviderDescriptor(
            provider_id="github",
            display_name="GitHub MCP",
            provider_kind=ProviderKind.CONNECTOR,
            boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
            authoritative_source="https://github.com/github/github-mcp-server",
            source_revision="v1.2.3",
            capabilities=("repository.remote_read",),  # type: ignore[arg-type]
            builder=_builder,
            readiness_probe=_ready,
        )


def test_provider_readiness_rejects_untyped_state() -> None:
    with pytest.raises(ValueError, match="state"):
        ProviderReadiness(
            provider_id="github",
            state="ready",  # type: ignore[arg-type]
            summary="Ready.",
        )


def test_provider_readiness_rejects_non_mapping_details() -> None:
    with pytest.raises(ValueError, match="details"):
        ProviderReadiness(
            provider_id="github",
            state=ProviderState.READY,
            summary="Ready.",
            details=[],  # type: ignore[arg-type]
        )


def test_provider_readiness_copies_and_freezes_details() -> None:
    details = {"tool_count": 12}
    readiness = ProviderReadiness(
        provider_id="github",
        state=ProviderState.READY,
        summary="Ready.",
        details=details,
    )

    details["tool_count"] = 99

    assert readiness.details == {"tool_count": 12}
    with pytest.raises(TypeError):
        readiness.details["tool_count"] = 13  # type: ignore[index]


def test_provider_readiness_rejects_non_json_details() -> None:
    with pytest.raises(ValueError, match="JSON-compatible"):
        ProviderReadiness(
            provider_id="github",
            state=ProviderState.READY,
            summary="Ready.",
            details={"value": object()},
        )


def _descriptor(
    provider_id: str,
    capability_id: str,
    *,
    builder: Any = _builder,
    readiness_probe: Any = None,
    enabled: bool = True,
) -> ProviderDescriptor:
    probe = readiness_probe or (
        lambda: ProviderReadiness(
            provider_id=provider_id,
            state=ProviderState.READY,
            summary=f"{provider_id} is ready.",
        )
    )
    return ProviderDescriptor(
        provider_id=provider_id,
        display_name=f"{provider_id.title()} MCP",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=f"https://example.test/{provider_id}",
        source_revision="v1",
        capabilities=(
            ProviderCapability(
                capability_id=capability_id,
                description=f"Capability for {provider_id}.",
            ),
        ),
        builder=builder,
        readiness_probe=probe,
        enabled=enabled,
    )


def test_registry_lists_providers_in_stable_id_order() -> None:
    registry = ProviderRegistry()
    registry.register(_descriptor("supabase", "database.manage"))
    registry.register(_descriptor("github", "repository.remote_read"))

    assert registry.contains("github") is True
    assert [item.provider_id for item in registry.list()] == ["github", "supabase"]
    assert registry.get("github").display_name == "Github MCP"


def test_registry_rejects_duplicate_provider_ids() -> None:
    registry = ProviderRegistry()
    registry.register(_descriptor("github", "repository.remote_read"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_descriptor("github", "repository.remote_write"))


def test_registry_reports_unknown_provider() -> None:
    registry = ProviderRegistry()

    with pytest.raises(KeyError, match="Unknown provider"):
        registry.get("missing")


def test_catalogue_filters_capabilities_without_building_providers() -> None:
    build_calls: list[str] = []

    def github_builder() -> object:
        build_calls.append("github")
        return object()

    registry = ProviderRegistry()
    registry.register(
        _descriptor(
            "github",
            "repository.remote_read",
            builder=github_builder,
        )
    )
    registry.register(_descriptor("supabase", "database.manage"))

    catalogue = ProviderCatalogue.from_registry(registry)

    assert [item.provider_id for item in catalogue.entries()] == ["github", "supabase"]
    assert [
        item.provider_id
        for item in catalogue.find_by_capability("repository.remote_read")
    ] == ["github"]
    assert build_calls == []


def test_health_aggregates_ready_degraded_and_disabled_without_building() -> None:
    build_calls: list[str] = []
    disabled_probe_calls: list[str] = []

    def build_github() -> object:
        build_calls.append("github")
        return object()

    def degraded_supabase() -> ProviderReadiness:
        return ProviderReadiness(
            provider_id="supabase",
            state=ProviderState.DEGRADED,
            summary="Supabase credentials are missing.",
        )

    def disabled_probe() -> ProviderReadiness:
        disabled_probe_calls.append("disabled")
        raise AssertionError("disabled providers must not be probed")

    summary = aggregate_provider_health(
        (
            _descriptor(
                "supabase",
                "database.manage",
                readiness_probe=degraded_supabase,
            ),
            _descriptor(
                "github",
                "repository.remote_read",
                builder=build_github,
            ),
            _descriptor(
                "semantic",
                "code.semantic",
                readiness_probe=disabled_probe,
                enabled=False,
            ),
        )
    )

    assert summary.state is ProviderState.DEGRADED
    assert summary.ready_count == 1
    assert summary.degraded_count == 1
    assert summary.disabled_count == 1
    assert summary.unavailable_count == 0
    assert [item.provider_id for item in summary.providers] == [
        "github",
        "semantic",
        "supabase",
    ]
    assert build_calls == []
    assert disabled_probe_calls == []


def test_health_contains_probe_failures_without_exposing_messages() -> None:
    def failing_probe() -> ProviderReadiness:
        raise RuntimeError("credential value must not be exposed")

    summary = aggregate_provider_health(
        (
            _descriptor(
                "github",
                "repository.remote_read",
                readiness_probe=failing_probe,
            ),
        )
    )

    assert summary.state is ProviderState.UNAVAILABLE
    assert summary.unavailable_count == 1
    assert summary.providers[0].summary == "Provider readiness probe failed."
    assert summary.providers[0].details == {"error_type": "RuntimeError"}


def test_health_rejects_mismatched_probe_identity_as_unavailable() -> None:
    summary = aggregate_provider_health(
        (
            _descriptor(
                "github",
                "repository.remote_read",
                readiness_probe=lambda: ProviderReadiness(
                    provider_id="supabase",
                    state=ProviderState.READY,
                    summary="Wrong provider.",
                ),
            ),
        )
    )

    assert summary.state is ProviderState.UNAVAILABLE
    assert summary.providers[0].summary == (
        "Provider readiness probe returned mismatched identity."
    )
    assert summary.providers[0].details == {"reported_provider_id": "supabase"}


def test_service_builds_only_when_explicitly_requested() -> None:
    build_calls: list[str] = []
    probe_calls: list[str] = []
    built = object()

    def builder() -> object:
        build_calls.append("github")
        return built

    def probe() -> ProviderReadiness:
        probe_calls.append("github")
        return ProviderReadiness(
            provider_id="github",
            state=ProviderState.READY,
            summary="Ready.",
        )

    registry = ProviderRegistry(
        (
            _descriptor(
                "github",
                "repository.remote_read",
                builder=builder,
                readiness_probe=probe,
            ),
        )
    )
    service = ProviderService(registry)

    assert [item.provider_id for item in service.catalogue().entries()] == ["github"]
    assert service.health().ready_count == 1
    assert build_calls == []
    assert probe_calls == ["github"]
    assert service.build("github") is built
    assert build_calls == ["github"]


def test_catalogue_entry_rejects_untyped_public_values() -> None:
    base = {
        "provider_id": "github",
        "display_name": "GitHub MCP",
        "provider_kind": ProviderKind.CONNECTOR,
        "boundary": ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        "enabled": True,
        "authoritative_source": "https://example.test/github",
        "source_revision": "v1",
        "capabilities": ("repository.remote_read",),
    }

    with pytest.raises(ValueError, match="provider_kind"):
        ProviderCatalogueEntry(
            **{**base, "provider_kind": "connector"}  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="boundary"):
        ProviderCatalogueEntry(
            **{**base, "boundary": "approved_external_connector"}  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="enabled"):
        ProviderCatalogueEntry(**{**base, "enabled": 1})  # type: ignore[arg-type]


def test_health_summary_rejects_untyped_public_values() -> None:
    ready = ProviderReadiness(
        provider_id="github",
        state=ProviderState.READY,
        summary="Ready.",
    )

    with pytest.raises(ValueError, match="state"):
        ProviderHealthSummary(
            state="ready",  # type: ignore[arg-type]
            providers=(ready,),
        )
    with pytest.raises(ValueError, match="providers"):
        ProviderHealthSummary(
            state=ProviderState.READY,
            providers=("github",),  # type: ignore[arg-type]
        )


def test_provider_module_schema_is_versioned_and_closed() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    schema_path = (
        repository_root
        / "contracts"
        / "providers"
        / "module"
        / "provider-module.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "https://kis-mcp.local/contracts/providers/module/v1"
    assert schema["title"] == "kis-mcp Provider Module Contracts"
    assert schema["oneOf"] == [
        {"$ref": "#/$defs/providerDescriptor"},
        {"$ref": "#/$defs/providerCapability"},
        {"$ref": "#/$defs/providerReadiness"},
        {"$ref": "#/$defs/providerCatalogueEntry"},
        {"$ref": "#/$defs/providerHealthSummary"},
    ]
    for definition in (
        "providerDescriptor",
        "providerCapability",
        "providerReadiness",
        "providerCatalogueEntry",
        "providerHealthSummary",
    ):
        assert schema["$defs"][definition]["additionalProperties"] is False
        assert "schema_version" in schema["$defs"][definition]["required"]
