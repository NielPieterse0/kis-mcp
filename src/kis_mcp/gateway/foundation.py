from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..config import RuntimeConfig
from ..models import HealthResponse, PolicyRuleResponse, QuarantineResponse
from ..quarantine import QuarantineRecord


_SERVER_INSTANCE_ID = uuid4().hex
_SERVER_STARTED_AT = datetime.now(UTC).isoformat()
_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _source_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=_REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    revision = result.stdout.strip().lower()
    if result.returncode != 0 or len(revision) != 40:
        return "unknown"
    return revision if all(char in "0123456789abcdef" for char in revision) else "unknown"


def _contract_fingerprint(runtime: RuntimeConfig, source_revision: str) -> str:
    payload = {
        "source_revision": source_revision,
        "settings": runtime.raw_settings,
        "policy": runtime.raw_policy,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def ensure_state_directories(config: RuntimeConfig) -> None:
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


def provider_environment(config: RuntimeConfig) -> dict[str, str]:
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


def policy_fingerprint(config: RuntimeConfig) -> str:
    encoded = json.dumps(config.raw_policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def policy_rule_response(rule: Mapping[str, Any]) -> PolicyRuleResponse:
    return PolicyRuleResponse(
        id=str(rule["id"]),
        name=str(rule["name"]),
        prohibited_outcome=str(rule["prohibited_outcome"]),
        decision=str(rule["decision"]),
    )


def quarantine_response(record: QuarantineRecord) -> QuarantineResponse:
    return QuarantineResponse(
        operation_id=record.operation_id,
        original_path=record.original_path,
        payload_path=record.payload_path,
        item_type=record.item_type,
        quarantined_at=record.quarantined_at,
        restored_at=record.restored_at,
    )


def quarantine_payload(record: QuarantineRecord) -> dict[str, Any]:
    response = quarantine_response(record)
    return {
        "operation_id": response.operation_id,
        "original_path": response.original_path,
        "payload_path": response.payload_path,
        "item_type": response.item_type,
        "quarantined_at": response.quarantined_at,
        "restored_at": response.restored_at,
        "schema_version": response.schema_version,
    }


def remote_mcp_implementation_status(
    runtime: RuntimeConfig,
    *,
    environment: Mapping[str, str] | None = None,
    current_pid: int | None = None,
    state_root: Path | None = None,
) -> str | None:
    env = environment if environment is not None else os.environ
    selected = env.get("KIS_MCP_RUNTIME_INSTANCE")
    if not isinstance(selected, str) or not selected.strip():
        return None
    try:
        instance = runtime.remote_instance(selected)
    except RuntimeError:
        return None
    path = (
        state_root if state_root is not None else Path(runtime.state_root)
    ) / "tunnel-client" / "runtime" / instance.name / "current.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    if not isinstance(document, Mapping):
        return None
    listener_pid = document.get("server_listener_pid")
    expected_pid = os.getpid() if current_pid is None else int(current_pid)
    if (
        document.get("schema_version") != 1
        or document.get("lifecycle") != "ready"
        or document.get("instance") != instance.name
        or document.get("endpoint") != instance.endpoint_url
        or isinstance(listener_pid, bool)
        or not isinstance(listener_pid, int)
        or listener_pid != expected_pid
    ):
        return None
    current = runtime.implementation_status.get("remote_mcp", "").strip()
    pending = "external_tunnel_pending_configuration"
    ready = "external_tunnel_ready"
    if current.endswith(pending):
        return f"{current[:-len(pending)]}{ready}"
    if current.endswith(ready):
        return current
    return ready


def health_response(runtime: RuntimeConfig, launch: Mapping[str, Any]) -> HealthResponse:
    entry = Path(str(launch.get("args", [""])[0]))
    implementation_status = dict(runtime.implementation_status)
    remote_status = remote_mcp_implementation_status(runtime)
    if remote_status is not None:
        implementation_status["remote_mcp"] = remote_status
    runtime_instance = os.environ.get("KIS_MCP_RUNTIME_INSTANCE", "stdio").strip() or "stdio"
    is_remote = runtime_instance != "stdio"
    source_revision = _source_revision()
    return HealthResponse(
        ready=entry.is_file(),
        server=runtime.server_name,
        project_boundary=runtime.project_boundary,
        quarantine_root=runtime.quarantine_root,
        desktop_commander_entry=str(entry),
        desktop_commander_installed=entry.is_file(),
        policy_rules=tuple(policy_rule_response(rule) for rule in runtime.raw_policy["rules"]),
        policy_fingerprint=policy_fingerprint(runtime),
        runtime_instance=runtime_instance,
        server_instance_id=_SERVER_INSTANCE_ID,
        server_started_at=_SERVER_STARTED_AT,
        source_revision=source_revision,
        contract_fingerprint=_contract_fingerprint(runtime, source_revision),
        transport={
            "kind": "streamable_http" if is_remote else "stdio",
            "stateless_http": runtime.remote_stateless_http if is_remote else False,
            "json_response": runtime.remote_json_response if is_remote else False,
        },
        implementation_status=implementation_status,
    )


__all__ = [
    "ensure_state_directories",
    "health_response",
    "remote_mcp_implementation_status",
    "provider_environment",
    "quarantine_payload",
    "quarantine_response",
]
