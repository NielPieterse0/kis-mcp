from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import kis_mcp.gateway.foundation as foundation_module
import kis_mcp.providers.supabase.server as supabase_server
from kis_mcp.config import load_runtime_config
from kis_mcp.gateway.foundation import remote_mcp_implementation_status
from kis_mcp.projects import load_project_registry_settings
from kis_mcp.providers.client_runtime import ProviderStartupState
from kis_mcp.providers.supabase.routing import (
    SupabaseCommissioningState,
    SupabaseProjectRouting,
    SupabaseProjectRoutingMiddleware,
)
from kis_mcp.providers.supabase.server import provider_health
from kis_mcp.providers.supabase.config import load_supabase_provider_config
from kis_mcp.providers.supabase.runtime import provider_readiness
from kis_mcp.remote_runtime import RUNTIME_INSTANCE_ENV, run_remote_instance


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_REF = "mmxuicfrdalymczdapjq"
SUPABASE_CONFIG = load_supabase_provider_config(REPOSITORY_ROOT)


def _tool(name: str, *, read_only: bool) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        annotations=SimpleNamespace(readOnlyHint=read_only),
    )


def _routing() -> SupabaseProjectRouting:
    registry = load_project_registry_settings(
        REPOSITORY_ROOT / "settings" / "projects.settings.json",
        boundary=r"C:\Projects",
    )
    tools = (
        _tool("list_projects", read_only=True),
        _tool("get_project_url", read_only=True),
        _tool("apply_migration", read_only=False),
    )
    return SupabaseProjectRouting(registry, lambda: tools)


def _context(tool_name: str, arguments: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        message=SimpleNamespace(name=tool_name, arguments=arguments),
    )


def test_successful_registered_project_read_marks_live_verification() -> None:
    state = SupabaseCommissioningState()
    middleware = SupabaseProjectRoutingMiddleware(_routing(), state)

    async def call_next(_context: object) -> str:
        return "ok"

    result = asyncio.run(
        middleware.on_call_tool(
            _context("get_project_url", {"project_id": PROJECT_REF}),
            call_next,
        )
    )

    assert result == "ok"
    assert state.registered_project_read_verified is True


def test_failed_or_non_read_calls_do_not_mark_live_verification() -> None:
    async def fail(_context: object) -> str:
        raise RuntimeError("upstream failed")

    async def succeed(_context: object) -> str:
        return "ok"

    for tool_name, arguments, callback in (
        ("get_project_url", {"project_id": PROJECT_REF}, fail),
        ("apply_migration", {"project_id": PROJECT_REF}, succeed),
        ("list_projects", {}, succeed),
    ):
        state = SupabaseCommissioningState()
        middleware = SupabaseProjectRoutingMiddleware(_routing(), state)
        if callback is fail:
            with pytest.raises(RuntimeError, match="upstream failed"):
                asyncio.run(middleware.on_call_tool(_context(tool_name, arguments), callback))
        else:
            asyncio.run(middleware.on_call_tool(_context(tool_name, arguments), callback))
        assert state.registered_project_read_verified is False


def test_provider_health_reflects_current_runtime_live_verification(monkeypatch) -> None:
    monkeypatch.setattr(
        supabase_server,
        "provider_specific_readiness",
        lambda config, environment: provider_readiness(
            config,
            environment,
            keyring_available=True,
        ),
    )
    startup = ProviderStartupState()
    startup.mark_ready()
    state = SupabaseCommissioningState()

    pending = provider_health(SUPABASE_CONFIG, {}, startup, state)
    state.mark_registered_project_read("get_project_url")
    verified = provider_health(SUPABASE_CONFIG, {}, startup, state)

    assert pending.details["commissioning"]["live_verified"] == (
        "pending_registered_project_read"
    )
    assert verified.details["commissioning"]["live_verified"] == (
        "ready_registered_project_read"
    )


def _write_current_state(
    root: Path,
    *,
    instance: str = "development",
    endpoint: str,
    lifecycle: str = "ready",
    listener_pid: int = 4242,
) -> None:
    path = root / "tunnel-client" / "runtime" / instance / "current.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "lifecycle": lifecycle,
                "instance": instance,
                "endpoint": endpoint,
                "server_listener_pid": listener_pid,
            }
        ),
        encoding="utf-8",
    )


def test_remote_status_requires_matching_ready_current_runtime(tmp_path: Path) -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    instance = config.remote_instance("development")
    environment = {RUNTIME_INSTANCE_ENV: "development"}
    _write_current_state(tmp_path, endpoint=instance.endpoint_url)

    assert remote_mcp_implementation_status(
        config,
        environment=environment,
        current_pid=4242,
        state_root=tmp_path,
    ) == "local_http_discover_write_read_quarantine_verified_external_tunnel_ready"


@pytest.mark.parametrize(
    ("lifecycle", "instance_name", "endpoint_suffix", "listener_pid"),
    [
        ("stopped", "development", "", 4242),
        ("ready", "operation", "", 4242),
        ("ready", "development", "/wrong", 4242),
        ("ready", "development", "", 9999),
    ],
)
def test_remote_status_rejects_stale_or_mismatched_runtime_state(
    tmp_path: Path,
    lifecycle: str,
    instance_name: str,
    endpoint_suffix: str,
    listener_pid: int,
) -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    selected = config.remote_instance("development")
    _write_current_state(
        tmp_path,
        instance=instance_name,
        endpoint=selected.endpoint_url + endpoint_suffix,
        lifecycle=lifecycle,
        listener_pid=listener_pid,
    )

    assert remote_mcp_implementation_status(
        config,
        environment={RUNTIME_INSTANCE_ENV: "development"},
        current_pid=4242,
        state_root=tmp_path,
    ) is None


def test_remote_runtime_exposes_selected_instance_only_for_process_lifetime(
    monkeypatch,
) -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    observed: list[str | None] = []
    monkeypatch.setenv(RUNTIME_INSTANCE_ENV, "operation")

    class FakeServer:
        def run(self, **_kwargs: Any) -> None:
            observed.append(os.environ.get(RUNTIME_INSTANCE_ENV))

    def factory(_config: object) -> FakeServer:
        observed.append(os.environ.get(RUNTIME_INSTANCE_ENV))
        return FakeServer()

    run_remote_instance(config, "development", server_factory=factory)

    assert observed == ["development", "development"]
    assert os.environ[RUNTIME_INSTANCE_ENV] == "operation"


def test_health_response_uses_runtime_remote_status_without_mutating_settings(
    monkeypatch,
) -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    original = config.implementation_status["remote_mcp"]
    resolved = "local_http_discover_write_read_quarantine_verified_external_tunnel_ready"
    monkeypatch.setattr(
        foundation_module,
        "remote_mcp_implementation_status",
        lambda _runtime: resolved,
    )

    response = foundation_module.health_response(
        config,
        config.desktop_commander_launch,
    )

    assert response.implementation_status["remote_mcp"] == resolved
    assert config.implementation_status["remote_mcp"] == original
    assert original.endswith("external_tunnel_pending_configuration")


def test_health_response_exposes_process_stable_runtime_fingerprints(monkeypatch) -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    monkeypatch.setenv(RUNTIME_INSTANCE_ENV, "development")

    first = foundation_module.health_response(config, config.desktop_commander_launch)
    second = foundation_module.health_response(config, config.desktop_commander_launch)

    assert first.runtime_instance == "development"
    assert first.server_instance_id == second.server_instance_id
    assert first.server_started_at == second.server_started_at
    assert first.source_revision == second.source_revision
    assert len(first.contract_fingerprint) == 64
    assert first.contract_fingerprint == second.contract_fingerprint
    assert first.transport == {
        "kind": "streamable_http",
        "stateless_http": True,
        "json_response": True,
    }
