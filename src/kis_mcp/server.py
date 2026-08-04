from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import ProxyClient

from .config import RuntimeConfig, load_runtime_config
from .desktop_commander import DesktopCommanderEffectResolver
from .middleware import ThreeRuleMiddleware
from .models import (
    HealthResponse,
    PolicyRuleResponse,
    QuarantineListResponse,
    QuarantineResponse,
)
from .policy import ThreeRulePolicy
from .provider_lifecycle import prepare_provider_launch
from .provider_readiness import validate_provider_offline_readiness
from .quarantine import QuarantineError, QuarantineRecord, QuarantineService


def _ensure_state_directories(config: RuntimeConfig) -> None:
    paths = config.raw_settings["paths"]
    for key in (
        "state_root",
        "desktop_commander_root",
        "desktop_commander_config_root",
        "quarantine_root",
        "temp_root",
        "log_root",
        "npm_cache_root",
        "python_environment_root",
        "uv_cache_root",
        "python_cache_root",
        "pytest_cache_root",
    ):
        Path(str(paths[key])).mkdir(parents=True, exist_ok=True)


def _provider_environment(config: RuntimeConfig) -> dict[str, str]:
    state_root = Path(config.state_root)
    temp_root = Path(config.temp_root)
    appdata = state_root / "AppData" / "Roaming"
    local_appdata = state_root / "AppData" / "Local"
    for path in (appdata, local_appdata, temp_root):
        path.mkdir(parents=True, exist_ok=True)

    forwarded = {
        key: value
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
        if (value := os.environ.get(key))
    }
    launch_env = config.desktop_commander_launch.get("env", {})
    forwarded.update({str(key): str(value) for key, value in launch_env.items()})
    forwarded.update(
        {
            "HOME": str(state_root),
            "USERPROFILE": str(state_root),
            "APPDATA": str(appdata),
            "LOCALAPPDATA": str(local_appdata),
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
            "NPM_CONFIG_CACHE": config.npm_cache_root,
            "PUPPETEER_CACHE_DIR": config.puppeteer_cache_root,
            "NO_UPDATE_NOTIFIER": "1",
        }
    )
    return forwarded


def _policy_fingerprint(config: RuntimeConfig) -> str:
    encoded = json.dumps(
        config.raw_policy, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _policy_rule_response(rule: Mapping[str, Any]) -> PolicyRuleResponse:
    return PolicyRuleResponse(
        id=str(rule["id"]),
        name=str(rule["name"]),
        prohibited_outcome=str(rule["prohibited_outcome"]),
        decision=str(rule["decision"]),
    )


def _quarantine_response(record: QuarantineRecord) -> QuarantineResponse:
    return QuarantineResponse(
        operation_id=record.operation_id,
        original_path=record.original_path,
        payload_path=record.payload_path,
        item_type=record.item_type,
        quarantined_at=record.quarantined_at,
        restored_at=record.restored_at,
    )


def _quarantine_payload(record: QuarantineRecord) -> dict[str, Any]:
    response = _quarantine_response(record)
    return {
        "operation_id": response.operation_id,
        "original_path": response.original_path,
        "payload_path": response.payload_path,
        "item_type": response.item_type,
        "quarantined_at": response.quarantined_at,
        "restored_at": response.restored_at,
        "schema_version": response.schema_version,
    }


def _health_response(
    runtime: RuntimeConfig,
    launch: Mapping[str, Any],
) -> HealthResponse:
    entry = Path(str(launch.get("args", [""])[0]))
    return HealthResponse(
        ready=entry.is_file(),
        server=runtime.server_name,
        project_boundary=runtime.project_boundary,
        quarantine_root=runtime.quarantine_root,
        desktop_commander_entry=str(entry),
        desktop_commander_installed=entry.is_file(),
        policy_rules=tuple(
            _policy_rule_response(rule) for rule in runtime.raw_policy["rules"]
        ),
        policy_fingerprint=_policy_fingerprint(runtime),
        implementation_status=dict(runtime.implementation_status),
    )


def build_server(
    config: RuntimeConfig | None = None,
    *,
    validate_provider: bool = True,
) -> FastMCP:
    runtime = config or load_runtime_config()
    if validate_provider:
        validate_provider_offline_readiness(runtime)
    _ensure_state_directories(runtime)

    launch = runtime.desktop_commander_launch
    provider_args, provider_environment = prepare_provider_launch(
        args=launch.get("args", []),
        environment=_provider_environment(runtime),
        provider_state_file=runtime.provider_state_file,
    )
    transport = StdioTransport(
        command=str(launch["command"]),
        args=provider_args,
        cwd=str(launch["cwd"]),
        env=provider_environment,
    )
    server = create_proxy(
        ProxyClient(transport),
        name=runtime.server_name,
    )

    quarantine = QuarantineService(
        project_boundary=runtime.project_boundary,
        quarantine_root=runtime.quarantine_root,
    )
    resolver = DesktopCommanderEffectResolver(
        project_boundary=runtime.project_boundary,
        provider_state_file=runtime.provider_state_file,
    )
    policy = ThreeRulePolicy(
        project_boundary=runtime.project_boundary,
        quarantine_root=runtime.quarantine_root,
    )

    def quarantine_paths(paths: Sequence[str]) -> list[dict[str, Any]]:
        return [
            _quarantine_payload(record)
            for record in quarantine.quarantine_many(paths)
        ]

    def quarantine_or_tool_error(path: str) -> QuarantineResponse:
        try:
            return _quarantine_response(quarantine.quarantine(path))
        except QuarantineError as exc:
            raise ToolError(f"HR-003_QUARANTINE_FAILED: {exc}") from exc

    def restore_or_tool_error(operation_id: str) -> QuarantineResponse:
        try:
            return _quarantine_response(quarantine.restore(operation_id))
        except QuarantineError as exc:
            raise ToolError(f"HR-003_QUARANTINE_FAILED: {exc}") from exc

    @server.tool
    def kis_health() -> HealthResponse:
        """Report local provider, policy, and generated-state readiness."""

        return _health_response(runtime, launch)

    @server.tool
    def kis_quarantine_path(path: str) -> QuarantineResponse:
        """Move one path into recoverable local quarantine."""

        return quarantine_or_tool_error(path)

    @server.tool
    def kis_list_quarantine(limit: int = 50) -> QuarantineListResponse:
        """List bounded recoverable quarantine records."""

        return QuarantineListResponse(
            records=tuple(
                _quarantine_response(record)
                for record in quarantine.list_records(limit=limit)
            )
        )

    @server.tool
    def kis_restore_quarantine(operation_id: str) -> QuarantineResponse:
        """Restore one quarantine record without overwriting its original path."""

        return restore_or_tool_error(operation_id)

    server.add_middleware(
        ThreeRuleMiddleware(
            resolver=resolver,
            policy=policy,
            quarantine_paths=quarantine_paths,
        )
    )
    return server


def main() -> None:
    config = load_runtime_config()
    server = build_server(config)
    server.run(transport=config.transport)


if __name__ == "__main__":
    main()
