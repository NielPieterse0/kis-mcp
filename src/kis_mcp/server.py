from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from dataclasses import asdict
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
from .policy import ThreeRulePolicy
from .provider_readiness import validate_provider_offline_readiness
from .quarantine import QuarantineError, QuarantineService


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
    transport = StdioTransport(
        command=str(launch["command"]),
        args=[str(value) for value in launch.get("args", [])],
        cwd=str(launch["cwd"]),
        env=_provider_environment(runtime),
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
        return [asdict(quarantine.quarantine(path)) for path in paths]

    def quarantine_or_tool_error(path: str) -> dict[str, Any]:
        try:
            return asdict(quarantine.quarantine(path))
        except QuarantineError as exc:
            raise ToolError(f"HR-003_QUARANTINE_FAILED: {exc}") from exc

    def restore_or_tool_error(operation_id: str) -> dict[str, Any]:
        try:
            return asdict(quarantine.restore(operation_id))
        except QuarantineError as exc:
            raise ToolError(f"HR-003_QUARANTINE_FAILED: {exc}") from exc

    @server.tool
    def kis_health() -> dict[str, Any]:
        """Report local provider, policy, and generated-state readiness."""

        entry = Path(str(launch.get("args", [""])[0]))
        return {
            "ready": entry.is_file(),
            "server": runtime.server_name,
            "project_boundary": runtime.project_boundary,
            "quarantine_root": runtime.quarantine_root,
            "desktop_commander_entry": str(entry),
            "desktop_commander_installed": entry.is_file(),
            "policy_rules": list(runtime.raw_policy["rules"]),
            "policy_fingerprint": _policy_fingerprint(runtime),
            "implementation_status": runtime.implementation_status,
        }

    @server.tool
    def kis_quarantine_path(path: str) -> dict[str, Any]:
        """Move one path into recoverable local quarantine."""

        return quarantine_or_tool_error(path)

    @server.tool
    def kis_list_quarantine(limit: int = 50) -> list[dict[str, Any]]:
        """List bounded recoverable quarantine records."""

        return [asdict(record) for record in quarantine.list_records(limit=limit)]

    @server.tool
    def kis_restore_quarantine(operation_id: str) -> dict[str, Any]:
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
