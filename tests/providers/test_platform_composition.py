from __future__ import annotations

import builtins
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.config import RuntimeConfig, load_runtime_config
from kis_mcp.providers import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderRegistry,
    ProviderState,
)
from kis_mcp.providers import desktop_commander as desktop_module
from kis_mcp.providers import platform as platform_module


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _runtime() -> RuntimeConfig:
    return load_runtime_config(REPOSITORY_ROOT)


def _descriptor(
    provider_id: str,
    *,
    builder: Callable[[], Any],
    readiness_probe: Callable[[], ProviderReadiness],
) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=provider_id,
        display_name=provider_id,
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=f"source:{provider_id}",
        source_revision="1",
        capabilities=(
            ProviderCapability(
                capability_id=f"{provider_id}.capability",
                description=f"Capability for {provider_id}.",
            ),
        ),
        builder=builder,
        readiness_probe=readiness_probe,
    )


def test_desktop_commander_descriptor_preserves_work_boundary() -> None:
    runtime = _runtime()

    descriptor = desktop_module.desktop_commander_provider_descriptor(runtime)

    assert descriptor.provider_id == "desktop-commander"
    assert descriptor.display_name == "Desktop Commander MCP"
    assert descriptor.provider_kind is ProviderKind.LOCAL_BACKEND
    assert descriptor.boundary is ProviderBoundary.WORK_BACKEND
    assert descriptor.authoritative_source == "npm:@wonderwhy-er/desktop-commander"
    assert descriptor.source_revision == runtime.desktop_commander_version
    assert [item.capability_id for item in descriptor.capabilities] == [
        "documents.local",
        "editing.local",
        "filesystem.local",
        "process.local",
        "search.local",
    ]


def test_desktop_commander_readiness_is_redacted_and_provider_neutral(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime()
    calls: list[RuntimeConfig] = []

    def validate(config: RuntimeConfig) -> None:
        calls.append(config)

    monkeypatch.setattr(
        desktop_module,
        "validate_provider_offline_readiness",
        validate,
    )

    readiness = desktop_module.desktop_commander_provider_readiness(runtime)

    assert calls == [runtime]
    assert readiness.provider_id == "desktop-commander"
    assert readiness.state is ProviderState.READY
    assert readiness.details == {
        "package": runtime.desktop_commander_package,
        "version": runtime.desktop_commander_version,
    }


def test_desktop_commander_readiness_contains_failure_without_raw_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime()

    def fail(_: RuntimeConfig) -> None:
        raise RuntimeError("sensitive machine path and provider state")

    monkeypatch.setattr(
        desktop_module,
        "validate_provider_offline_readiness",
        fail,
    )

    readiness = desktop_module.desktop_commander_provider_readiness(runtime)
    rendered = readiness.to_json_dict()

    assert readiness.state is ProviderState.UNAVAILABLE
    assert readiness.details == {"error_type": "RuntimeError"}
    assert "sensitive machine path" not in str(rendered)


def test_platform_registry_contains_exact_approved_providers_without_probing() -> None:
    registry = platform_module.build_platform_provider_registry(
        runtime_config=_runtime(),
        environment={},
    )

    assert [item.provider_id for item in registry.list()] == [
        "desktop-commander",
        "github-mcp",
        "nvidia-nim",
        "supabase",
    ]
    assert [item.provider_id for item in platform_module.ProviderService(registry).catalogue().entries()] == [
        "desktop-commander",
        "github-mcp",
        "nvidia-nim",
        "supabase",
    ]


def test_platform_registry_and_catalogue_do_not_build_or_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builders = 0
    probes = 0

    def builder() -> object:
        nonlocal builders
        builders += 1
        return object()

    def probe(provider_id: str) -> ProviderReadiness:
        nonlocal probes
        probes += 1
        return ProviderReadiness(
            provider_id=provider_id,
            state=ProviderState.READY,
            summary="Ready.",
        )

    def registrar(provider_id: str):
        def register(registry: ProviderRegistry, *args: Any, **kwargs: Any) -> ProviderDescriptor:
            return registry.register(
                _descriptor(
                    provider_id,
                    builder=builder,
                    readiness_probe=lambda: probe(provider_id),
                )
            )

        return register

    monkeypatch.setattr(
        platform_module,
        "register_desktop_commander_provider",
        registrar("desktop-commander"),
    )
    monkeypatch.setattr(
        platform_module,
        "register_github_provider",
        registrar("github-mcp"),
    )
    monkeypatch.setattr(
        platform_module,
        "register_nvidia_provider",
        registrar("nvidia-nim"),
    )
    monkeypatch.setattr(
        platform_module,
        "register_supabase_provider",
        registrar("supabase"),
    )

    registry = platform_module.build_platform_provider_registry(
        runtime_config=_runtime(),
        environment={},
    )
    entries = platform_module.ProviderService(registry).catalogue().entries()

    assert len(entries) == 4
    assert builders == 0
    assert probes == 0


def test_platform_health_probes_all_providers_but_builds_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builders = 0
    probes: list[str] = []

    def builder() -> object:
        nonlocal builders
        builders += 1
        return object()

    def registrar(provider_id: str):
        def register(registry: ProviderRegistry, *args: Any, **kwargs: Any) -> ProviderDescriptor:
            def probe() -> ProviderReadiness:
                probes.append(provider_id)
                return ProviderReadiness(
                    provider_id=provider_id,
                    state=ProviderState.READY,
                    summary="Ready.",
                )

            return registry.register(
                _descriptor(
                    provider_id,
                    builder=builder,
                    readiness_probe=probe,
                )
            )

        return register

    monkeypatch.setattr(
        platform_module,
        "register_desktop_commander_provider",
        registrar("desktop-commander"),
    )
    monkeypatch.setattr(
        platform_module,
        "register_github_provider",
        registrar("github-mcp"),
    )
    monkeypatch.setattr(
        platform_module,
        "register_nvidia_provider",
        registrar("nvidia-nim"),
    )
    monkeypatch.setattr(
        platform_module,
        "register_supabase_provider",
        registrar("supabase"),
    )

    service = platform_module.build_platform_provider_service(
        runtime_config=_runtime(),
        environment={},
    )
    health = service.health()

    assert health.state is ProviderState.READY
    assert probes == [
        "desktop-commander",
        "github-mcp",
        "nvidia-nim",
        "supabase",
    ]
    assert builders == 0


def test_supabase_registration_reraises_unexpected_import_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fail_supabase_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "supabase" and level == 1:
            raise RuntimeError("unexpected provider defect")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_supabase_import)

    with pytest.raises(RuntimeError, match="unexpected provider defect"):
        platform_module.register_supabase_provider(ProviderRegistry())


@pytest.mark.parametrize("config_mode", ["missing", "malformed"])
def test_core_server_contains_invalid_supabase_configuration(config_mode: str) -> None:
    script = r'''
import asyncio
import json
import os
from pathlib import Path

from fastmcp import FastMCP

original_read_text = Path.read_text


def patched_read_text(path, *args, **kwargs):
    if path.name == "supabase-mcp.provider.json":
        if os.environ["SUPABASE_CONFIG_MODE"] == "missing":
            raise FileNotFoundError(str(path))
        return "{"
    return original_read_text(path, *args, **kwargs)


Path.read_text = patched_read_text

from kis_mcp import server as server_module
from kis_mcp.providers.runtime_settings import (
    ProviderMountSetting,
    ProviderRuntimeSettings,
)

server_module.create_proxy = lambda *_args, **_kwargs: FastMCP("test-root")
runtime_settings = ProviderRuntimeSettings(
    schema_version=1,
    providers=(
        ProviderMountSetting(
            provider_id="github-mcp",
            enabled=False,
            namespace="github",
        ),
        ProviderMountSetting(
            provider_id="supabase",
            enabled=False,
            namespace="supabase",
        ),
    ),
)
server = server_module.build_server(
    validate_provider=False,
    provider_runtime_settings=runtime_settings,
)
names = sorted(tool.name for tool in asyncio.run(server.list_tools()))
status_result = asyncio.run(server.call_tool("kis_provider_status", {}))
status = status_result.structured_content
supabase = next(
    item for item in status["external_providers"] if item["provider_id"] == "supabase"
)
print(json.dumps({"names": names, "supabase": supabase}, sort_keys=True))
'''
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")
    environment["SUPABASE_CONFIG_MODE"] = config_mode

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert "kis_health" in payload["names"]
    assert "kis_provider_status" in payload["names"]
    assert payload["supabase"]["registered"] is False
    assert payload["supabase"]["state"] == "unregistered"
