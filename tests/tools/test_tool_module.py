from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from kis_mcp.tools import (
    ToolBoundary,
    ToolCapability,
    ToolCatalogue,
    ToolDescriptor,
    ToolKind,
    ToolReadiness,
    ToolRegistry,
    ToolService,
    ToolState,
    aggregate_tool_health,
)


def _builder() -> object:
    return object()


def _descriptor(
    tool_id: str,
    capability_id: str,
    *,
    builder: Any = _builder,
    readiness_probe: Any = None,
    enabled: bool = True,
) -> ToolDescriptor:
    probe = readiness_probe or (
        lambda: ToolReadiness(
            tool_id=tool_id,
            state=ToolState.READY,
            summary=f"{tool_id} is ready.",
        )
    )
    return ToolDescriptor(
        tool_id=tool_id,
        display_name=tool_id.replace("-", " ").title(),
        tool_kind=ToolKind.LOCAL_EXECUTABLE,
        boundary=ToolBoundary.LOCAL_PROCESS,
        authoritative_source=f"https://example.test/{tool_id}",
        source_revision="v1",
        capabilities=(
            ToolCapability(
                capability_id=capability_id,
                description=f"Capability for {tool_id}.",
                effects=("local-read",),
                operation_names=("review",),
            ),
        ),
        builder=builder,
        readiness_probe=probe,
        enabled=enabled,
    )


def test_descriptor_projects_json_safe_metadata() -> None:
    descriptor = _descriptor("codex-cli", "code.review")

    assert descriptor.to_json_dict() == {
        "schema_version": 1,
        "tool_id": "codex-cli",
        "display_name": "Codex Cli",
        "tool_kind": "local_executable",
        "boundary": "local_process",
        "authoritative_source": "https://example.test/codex-cli",
        "source_revision": "v1",
        "enabled": True,
        "capabilities": [
            {
                "schema_version": 1,
                "capability_id": "code.review",
                "description": "Capability for codex-cli.",
                "effects": ["local-read"],
                "operation_names": ["review"],
            }
        ],
    }


def test_descriptor_rejects_duplicate_capabilities_and_invalid_identity() -> None:
    capability = ToolCapability(
        capability_id="code.review",
        description="Review code.",
    )
    with pytest.raises(ValueError, match="duplicate capability_id"):
        ToolDescriptor(
            tool_id="codex-cli",
            display_name="Codex CLI",
            tool_kind=ToolKind.LOCAL_EXECUTABLE,
            boundary=ToolBoundary.LOCAL_PROCESS,
            authoritative_source="https://github.com/openai/codex",
            source_revision="v1",
            capabilities=(capability, capability),
            builder=_builder,
            readiness_probe=lambda: ToolReadiness(
                tool_id="codex-cli",
                state=ToolState.READY,
                summary="Ready.",
            ),
        )

    with pytest.raises(ValueError, match="tool_id"):
        _descriptor("Codex CLI", "code.review")


def test_registry_is_deterministic_and_rejects_duplicate_ids() -> None:
    registry = ToolRegistry()
    registry.register(_descriptor("serena", "code.semantic"))
    registry.register(_descriptor("codex-cli", "code.review"))

    assert registry.contains("codex-cli") is True
    assert [item.tool_id for item in registry.list()] == ["codex-cli", "serena"]
    assert registry.get("codex-cli").display_name == "Codex Cli"

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_descriptor("codex-cli", "code.generate"))
    with pytest.raises(KeyError, match="Unknown tool"):
        registry.get("missing")


def test_catalogue_filters_without_building_tools() -> None:
    build_calls: list[str] = []

    def build_codex() -> object:
        build_calls.append("codex-cli")
        return object()

    registry = ToolRegistry(
        (
            _descriptor("serena", "code.semantic"),
            _descriptor("codex-cli", "code.review", builder=build_codex),
        )
    )

    catalogue = ToolCatalogue.from_registry(registry)

    assert [item.tool_id for item in catalogue.entries()] == ["codex-cli", "serena"]
    assert [
        item.tool_id for item in catalogue.find_by_capability("code.review")
    ] == ["codex-cli"]
    assert build_calls == []


def test_health_contains_failures_and_skips_disabled_tools() -> None:
    build_calls: list[str] = []
    disabled_probe_calls: list[str] = []

    def build_codex() -> object:
        build_calls.append("codex-cli")
        return object()

    def degraded() -> ToolReadiness:
        return ToolReadiness(
            tool_id="serena",
            state=ToolState.DEGRADED,
            summary="Language server is not ready.",
        )

    def disabled_probe() -> ToolReadiness:
        disabled_probe_calls.append("disabled")
        raise AssertionError("disabled tools must not be probed")

    summary = aggregate_tool_health(
        (
            _descriptor("serena", "code.semantic", readiness_probe=degraded),
            _descriptor("codex-cli", "code.review", builder=build_codex),
            _descriptor(
                "context7",
                "documentation.lookup",
                readiness_probe=disabled_probe,
                enabled=False,
            ),
        )
    )

    assert summary.state is ToolState.DEGRADED
    assert summary.ready_count == 1
    assert summary.degraded_count == 1
    assert summary.disabled_count == 1
    assert summary.unavailable_count == 0
    assert [item.tool_id for item in summary.tools] == [
        "codex-cli",
        "context7",
        "serena",
    ]
    assert build_calls == []
    assert disabled_probe_calls == []


def test_health_redacts_probe_failures_and_rejects_mismatched_identity() -> None:
    def failing_probe() -> ToolReadiness:
        raise RuntimeError("secret must not be exposed")

    failure = aggregate_tool_health(
        (_descriptor("codex-cli", "code.review", readiness_probe=failing_probe),)
    )
    assert failure.state is ToolState.UNAVAILABLE
    assert failure.tools[0].summary == "Tool readiness probe failed."
    assert failure.tools[0].details == {"error_type": "RuntimeError"}

    mismatch = aggregate_tool_health(
        (
            _descriptor(
                "codex-cli",
                "code.review",
                readiness_probe=lambda: ToolReadiness(
                    tool_id="serena",
                    state=ToolState.READY,
                    summary="Wrong identity.",
                ),
            ),
        )
    )
    assert mismatch.state is ToolState.UNAVAILABLE
    assert mismatch.tools[0].details == {"reported_tool_id": "serena"}


def test_service_build_is_explicit() -> None:
    built: list[str] = []

    def builder() -> object:
        built.append("codex-cli")
        return {"name": "codex-cli"}

    service = ToolService(
        ToolRegistry((_descriptor("codex-cli", "code.review", builder=builder),))
    )

    assert service.find_by_capability("code.review")[0].tool_id == "codex-cli"
    assert built == []
    assert service.health().ready_count == 1
    assert built == []
    assert service.build("codex-cli") == {"name": "codex-cli"}
    assert built == ["codex-cli"]


def test_tools_module_does_not_import_provider_or_gateway_internals() -> None:
    module_root = Path(__file__).resolve().parents[2] / "src" / "kis_mcp" / "tools"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in module_root.glob("*.py")
        if path.is_file()
    )

    assert "kis_mcp.providers" not in source
    assert "kis_mcp.server" not in source
    assert "kis_mcp.policy" not in source
