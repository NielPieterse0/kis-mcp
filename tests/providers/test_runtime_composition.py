from __future__ import annotations

import asyncio
import importlib
import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastmcp import FastMCP
from jsonschema import Draft202012Validator

from kis_mcp.providers import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderRegistry,
    ProviderService,
    ProviderState,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = REPOSITORY_ROOT / "settings" / "providers" / "platform-runtime.provider.json"
SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "contracts"
    / "providers"
    / "runtime"
    / "platform-runtime.schema.json"
)


def _settings_module() -> Any:
    try:
        return importlib.import_module("kis_mcp.providers.runtime_settings")
    except ModuleNotFoundError as exc:
        pytest.fail(f"provider runtime settings module is not implemented: {exc}")


def _runtime_module() -> Any:
    try:
        return importlib.import_module("kis_mcp.providers.runtime")
    except ModuleNotFoundError as exc:
        pytest.fail(f"provider runtime composition module is not implemented: {exc}")


def _write_settings(root: Path, document: dict[str, Any]) -> Path:
    path = root / "settings" / "providers" / "platform-runtime.provider.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _valid_document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "providers": [
            {"provider_id": "github-mcp", "enabled": True, "namespace": "github"},
            {"provider_id": "supabase", "enabled": True, "namespace": "supabase"},
        ],
    }


def _runtime_settings(
    *,
    github_enabled: bool = True,
    supabase_enabled: bool = True,
) -> Any:
    module = _settings_module()
    return module.ProviderRuntimeSettings(
        schema_version=1,
        providers=(
            module.ProviderMountSetting(
                provider_id="github-mcp",
                enabled=github_enabled,
                namespace="github",
            ),
            module.ProviderMountSetting(
                provider_id="supabase",
                enabled=supabase_enabled,
                namespace="supabase",
            ),
        ),
    )


def _descriptor(
    provider_id: str,
    *,
    builder: Callable[[], Any],
    readiness: ProviderReadiness | None = None,
) -> ProviderDescriptor:
    result = readiness or ProviderReadiness(
        provider_id=provider_id,
        state=ProviderState.READY,
        summary="Provider is locally ready.",
    )
    return ProviderDescriptor(
        provider_id=provider_id,
        display_name=provider_id,
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=f"source:{provider_id}",
        source_revision="test",
        capabilities=(
            ProviderCapability(
                capability_id=f"{provider_id}.test",
                description=f"Test capability for {provider_id}.",
            ),
        ),
        builder=builder,
        readiness_probe=lambda: result,
    )


def _service(*descriptors: ProviderDescriptor) -> ProviderService:
    return ProviderService(ProviderRegistry(descriptors))


def _child_server(label: str) -> FastMCP:
    server = FastMCP(f"{label}-provider")

    @server.tool(name="echo")
    def echo(value: str) -> str:
        return f"{label}:{value}"

    return server


def _all_tools(server: FastMCP) -> list[Any]:
    return list(asyncio.run(server.list_tools()))


def test_canonical_runtime_settings_select_exact_approved_providers() -> None:
    module = _settings_module()

    settings = module.load_provider_runtime_settings(REPOSITORY_ROOT)

    assert settings.schema_version == 1
    assert [item.provider_id for item in settings.providers] == [
        "github-mcp",
        "supabase",
    ]
    assert [item.namespace for item in settings.providers] == ["github", "supabase"]
    assert all(item.enabled for item in settings.providers)


def test_runtime_settings_schema_is_closed_and_matches_canonical_contract() -> None:
    settings_document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == 1
    assert set(schema["required"]) == set(schema["properties"])
    provider_schema = schema["properties"]["providers"]["items"]
    assert provider_schema["additionalProperties"] is False
    assert set(provider_schema["required"]) == set(provider_schema["properties"])
    assert set(provider_schema["properties"]["provider_id"]["enum"]) == {
        "github-mcp",
        "supabase",
    }
    assert settings_document == _valid_document()

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(settings_document)) == []

    duplicate_namespace = deepcopy(settings_document)
    duplicate_namespace["providers"][1]["namespace"] = "github"
    assert list(validator.iter_errors(duplicate_namespace))

    mismatched_namespace = deepcopy(settings_document)
    mismatched_namespace["providers"][0]["namespace"] = "git"
    assert list(validator.iter_errors(mismatched_namespace))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda document: document.update({"unexpected": True}),
            "unknown keys",
        ),
        (
            lambda document: document["providers"].append(
                {
                    "provider_id": "unknown",
                    "enabled": True,
                    "namespace": "unknown",
                }
            ),
            "approved external provider",
        ),
        (
            lambda document: document["providers"].append(
                {
                    "provider_id": "github-mcp",
                    "enabled": False,
                    "namespace": "github",
                }
            ),
            "duplicate provider_id",
        ),
        (
            lambda document: document["providers"][1].update(
                {"namespace": "github"}
            ),
            "must be supabase",
        ),
        (
            lambda document: document["providers"][0].update(
                {"namespace": "GitHub"}
            ),
            "namespace",
        ),
        (
            lambda document: document["providers"][0].update(
                {"namespace": "git"}
            ),
            "must be github",
        ),
        (
            lambda document: document["providers"][0].update(
                {"enabled": "yes"}
            ),
            "enabled must be a boolean",
        ),
        (
            lambda document: document["providers"][0].pop("namespace"),
            "missing required keys",
        ),
        (
            lambda document: document["providers"].pop(),
            "exactly the approved external providers",
        ),
    ],
)
def test_runtime_settings_reject_invalid_documents(
    tmp_path: Path,
    mutate: Any,
    message: str,
) -> None:
    module = _settings_module()
    document = _valid_document()
    mutate(document)
    _write_settings(tmp_path, document)

    with pytest.raises(module.ProviderRuntimeSettingsError, match=message):
        module.load_provider_runtime_settings(tmp_path)


def test_runtime_settings_records_reject_invalid_direct_construction() -> None:
    module = _settings_module()

    with pytest.raises(
        module.ProviderRuntimeSettingsError,
        match="exactly the approved external providers",
    ):
        module.ProviderRuntimeSettings(
            schema_version=1,
            providers=(
                module.ProviderMountSetting(
                    provider_id="github-mcp",
                    enabled=True,
                    namespace="github",
                ),
            ),
        )


def test_disabled_providers_are_not_built() -> None:
    runtime = _runtime_module()
    build_calls: list[str] = []
    service = _service(
        _descriptor(
            "github-mcp",
            builder=lambda: build_calls.append("github-mcp"),
        ),
        _descriptor(
            "supabase",
            builder=lambda: build_calls.append("supabase"),
        ),
    )

    composition = runtime.compose_provider_runtime(
        FastMCP("root"),
        service,
        _runtime_settings(github_enabled=False, supabase_enabled=False),
    )

    assert build_calls == []
    assert [item.state.value for item in composition.results] == [
        "disabled",
        "disabled",
    ]
    assert all(not item.build_attempted for item in composition.results)
    assert all(not item.mounted for item in composition.results)


def test_enabled_providers_mount_in_stable_namespaces() -> None:
    runtime = _runtime_module()
    build_calls: list[str] = []

    def build(provider_id: str, label: str) -> Callable[[], FastMCP]:
        def builder() -> FastMCP:
            build_calls.append(provider_id)
            return _child_server(label)

        return builder

    service = _service(
        _descriptor("supabase", builder=build("supabase", "supabase")),
        _descriptor("github-mcp", builder=build("github-mcp", "github")),
    )
    root = FastMCP("root")

    composition = runtime.compose_provider_runtime(
        root,
        service,
        _runtime_settings(),
    )

    assert build_calls == ["github-mcp", "supabase"]
    assert [item.provider_id for item in composition.results] == [
        "github-mcp",
        "supabase",
    ]
    assert [item.state.value for item in composition.results] == [
        "mounted",
        "mounted",
    ]
    assert {tool.name for tool in _all_tools(root)} == {
        "github_echo",
        "supabase_echo",
    }
    result = asyncio.run(root.call_tool("github_echo", {"value": "ok"}))
    assert result.content[0].text == "github:ok"


def test_unregistered_provider_is_contained_without_build_attempt() -> None:
    runtime = _runtime_module()
    service = _service(
        _descriptor("github-mcp", builder=lambda: _child_server("github")),
    )

    composition = runtime.compose_provider_runtime(
        FastMCP("root"),
        service,
        _runtime_settings(),
    )

    supabase = composition.results[1]
    assert supabase.provider_id == "supabase"
    assert supabase.state.value == "unregistered"
    assert supabase.registered is False
    assert supabase.build_attempted is False


def test_builder_failures_and_invalid_results_are_redacted_and_contained() -> None:
    runtime = _runtime_module()

    def fail() -> FastMCP:
        raise RuntimeError("secret-token-value and machine path")

    service = _service(
        _descriptor("github-mcp", builder=fail),
        _descriptor("supabase", builder=lambda: object()),
    )
    root = FastMCP("root")

    @root.tool(name="core")
    def core() -> str:
        return "available"

    composition = runtime.compose_provider_runtime(
        root,
        service,
        _runtime_settings(),
    )
    rendered = composition.to_json_dict()

    assert [item.state.value for item in composition.results] == [
        "build_failed",
        "invalid_builder_result",
    ]
    assert composition.results[0].error_type == "RuntimeError"
    assert composition.results[1].error_type == "object"
    assert "secret-token-value" not in json.dumps(rendered)
    assert {tool.name for tool in _all_tools(root)} == {"core"}


def test_provider_runtime_status_separates_mounting_from_commissioning() -> None:
    runtime = _runtime_module()
    github_user_status = {
        "state": "ready_authentication_required",
        "label": "Ready — authentication required",
        "required_action": "Authenticate before live operations.",
    }
    github_commissioning = {
        "installed": "ready",
        "configured": "ready",
        "authenticated": "required",
        "upstream_connected": "pending_authentication",
        "tools_discovered": "pending_authentication",
        "live_verified": "pending_authentication",
    }
    service = _service(
        _descriptor(
            "github-mcp",
            builder=lambda: _child_server("github"),
            readiness=ProviderReadiness(
                provider_id="github-mcp",
                state=ProviderState.READY,
                summary="Local preflight is ready.",
                details={
                    "configured": True,
                    "user_status": github_user_status,
                    "commissioning": github_commissioning,
                },
            ),
        ),
        _descriptor(
            "supabase",
            builder=lambda: _child_server("supabase"),
            readiness=ProviderReadiness(
                provider_id="supabase",
                state=ProviderState.UNAVAILABLE,
                summary="Credentials are absent.",
            ),
        ),
    )
    composition = runtime.compose_provider_runtime(
        FastMCP("root"),
        service,
        _runtime_settings(),
    )

    status = runtime.provider_runtime_status(service, composition)

    assert status["schema_version"] == 1
    assert status["platform_health"]["state"] == "degraded"
    platform_providers = {
        item["provider_id"]: item
        for item in status["platform_health"]["providers"]
    }
    assert platform_providers["github-mcp"]["details"] == {"configured": True}
    assert platform_providers["supabase"]["details"] == {}
    providers = {item["provider_id"]: item for item in status["external_providers"]}
    github = providers["github-mcp"]
    assert github["mounted"] is True
    assert github["readiness"]["state"] == "ready"
    assert github["readiness"]["details"] == {"configured": True}
    assert github["user_status"] == github_user_status
    assert github["commissioning"] == github_commissioning

    supabase = providers["supabase"]
    assert supabase["mounted"] is True
    assert supabase["readiness"]["state"] == "unavailable"
    assert supabase["user_status"] is None
    assert supabase["commissioning"] == {
        "installed": "not_verified",
        "configured": "not_verified",
        "authenticated": "not_verified",
        "upstream_connected": "not_verified",
        "tools_discovered": "not_verified",
        "live_verified": "not_verified",
    }


def test_provider_runtime_status_prioritizes_mount_failure_over_ready_preflight() -> None:
    runtime = _runtime_module()
    service = _service(
        _descriptor(
            "github-mcp",
            builder=lambda: _child_server("github"),
            readiness=ProviderReadiness(
                provider_id="github-mcp",
                state=ProviderState.READY,
                summary="Local preflight is ready.",
                details={
                    "user_status": {
                        "state": "ready_authentication_required",
                        "label": "Ready — authentication required",
                        "required_action": "Authenticate before live operations.",
                    },
                    "commissioning": {
                        "installed": "ready",
                        "configured": "ready",
                        "authenticated": "required",
                        "upstream_connected": "pending_authentication",
                        "tools_discovered": "pending_authentication",
                        "live_verified": "pending_authentication",
                    },
                },
            ),
        ),
    )
    composition = runtime.ProviderRuntimeComposition(
        results=(
            runtime.ProviderMountResult(
                provider_id="github-mcp",
                namespace="github",
                registered=True,
                enabled=True,
                build_attempted=True,
                built=True,
                mounted=False,
                state=runtime.ProviderMountState.MOUNT_FAILED,
                error_type="RuntimeError",
            ),
        )
    )

    status = runtime.provider_runtime_status(service, composition)

    provider = status["external_providers"][0]
    assert provider["state"] == "mount_failed"
    assert provider["user_status"] == {
        "state": "mount_failed",
        "label": "Unavailable — provider mount failed",
        "required_action": (
            "Inspect the provider namespace and gateway mount failure, then restart "
            "the gateway."
        ),
    }


def test_build_server_mounts_injected_provider_and_exposes_status(monkeypatch: Any) -> None:
    from kis_mcp import server as server_module

    monkeypatch.setattr(
        server_module,
        "create_proxy",
        lambda *_args, **_kwargs: FastMCP("test-root"),
    )

    def unexpected_supabase_build() -> FastMCP:
        raise AssertionError("disabled Supabase builder must not run")

    service = _service(
        _descriptor("github-mcp", builder=lambda: _child_server("github")),
        _descriptor("supabase", builder=unexpected_supabase_build),
    )

    server = server_module.build_server(
        validate_provider=False,
        provider_service=service,
        provider_runtime_settings=_runtime_settings(supabase_enabled=False),
    )

    names = {tool.name for tool in _all_tools(server)}
    assert {
        "github_echo",
        "inspect_project",
        "kis_health",
        "kis_list_quarantine",
        "kis_provider_status",
        "kis_quarantine_path",
        "kis_restore_quarantine",
    }.issubset(names)

    result = asyncio.run(server.call_tool("github_echo", {"value": "through-root"}))
    assert result.content[0].text == "github:through-root"

    status_result = asyncio.run(server.call_tool("kis_provider_status", {}))
    status = status_result.structured_content
    assert status is not None
    providers = {item["provider_id"]: item for item in status["external_providers"]}
    assert providers["github-mcp"]["state"] == "mounted"
    assert providers["supabase"]["state"] == "disabled"


def test_build_server_contains_provider_builder_failures(monkeypatch: Any) -> None:
    from kis_mcp import server as server_module

    monkeypatch.setattr(
        server_module,
        "create_proxy",
        lambda *_args, **_kwargs: FastMCP("test-root"),
    )

    def fail_github() -> FastMCP:
        raise RuntimeError("github-secret-value")

    def fail_supabase() -> FastMCP:
        raise ValueError("supabase-secret-value")

    ready_user_status = {
        "state": "ready_authentication_required",
        "label": "Ready — authentication required",
        "required_action": "Authenticate before live operations.",
    }
    ready_commissioning = {
        "installed": "ready",
        "configured": "ready",
        "authenticated": "required",
        "upstream_connected": "pending_authentication",
        "tools_discovered": "pending_authentication",
        "live_verified": "pending_authentication",
    }

    def ready_readiness(provider_id: str) -> ProviderReadiness:
        return ProviderReadiness(
            provider_id=provider_id,
            state=ProviderState.READY,
            summary="Local preflight is ready.",
            details={
                "user_status": ready_user_status,
                "commissioning": ready_commissioning,
            },
        )

    server = server_module.build_server(
        validate_provider=False,
        provider_service=_service(
            _descriptor(
                "github-mcp",
                builder=fail_github,
                readiness=ready_readiness("github-mcp"),
            ),
            _descriptor(
                "supabase",
                builder=fail_supabase,
                readiness=ready_readiness("supabase"),
            ),
        ),
        provider_runtime_settings=_runtime_settings(),
    )

    names = {tool.name for tool in _all_tools(server)}
    assert "kis_health" in names
    assert "kis_provider_status" in names
    assert "github_echo" not in names
    assert "supabase_echo" not in names

    status_result = asyncio.run(server.call_tool("kis_provider_status", {}))
    status = status_result.structured_content
    assert status is not None
    rendered = json.dumps(status)
    assert "github-secret-value" not in rendered
    assert "supabase-secret-value" not in rendered
    providers = {item["provider_id"]: item for item in status["external_providers"]}
    assert providers["github-mcp"]["state"] == "build_failed"
    assert providers["github-mcp"]["error_type"] == "RuntimeError"
    assert providers["github-mcp"]["user_status"] == {
        "state": "build_failed",
        "label": "Unavailable — provider build failed",
        "required_action": (
            "Inspect provider readiness and local configuration, then restart the gateway."
        ),
    }
    assert providers["supabase"]["state"] == "build_failed"
    assert providers["supabase"]["error_type"] == "ValueError"
    assert providers["supabase"]["user_status"] == {
        "state": "build_failed",
        "label": "Unavailable — provider build failed",
        "required_action": (
            "Inspect provider readiness and local configuration, then restart the gateway."
        ),
    }
