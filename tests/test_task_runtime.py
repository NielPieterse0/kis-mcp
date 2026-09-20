from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.task_runtime import (
    TaskRuntimeSettings,
    build_tasks_extension,
    load_task_runtime_settings,
    runtime_instance,
    task_role,
)


def _settings(**overrides) -> TaskRuntimeSettings:
    values = {
        "enabled": True,
        "backend_image": "valkey/valkey:9.1.2-alpine",
        "backend_url": "redis://127.0.0.1:6380/0",
        "queue_prefix": "kis-mcp",
        "worker_concurrency": 2,
        "redelivery_timeout_seconds": 900,
        "reconnection_delay_seconds": 5,
        "minimum_check_interval_milliseconds": 100,
    }
    values.update(overrides)
    return TaskRuntimeSettings(**values)


def test_disabled_repository_settings_preserve_in_process_backend() -> None:
    root = Path(__file__).parents[1]
    settings = load_task_runtime_settings(root / "settings" / "task-runtime.settings.json")
    assert settings.enabled is False
    extension = build_tasks_extension(settings, {})
    assert extension.docket_settings.url == "memory://"


def test_enabled_frontend_and_worker_share_queue_but_not_worker_concurrency() -> None:
    settings = _settings()
    frontend = build_tasks_extension(
        settings,
        {"KIS_MCP_RUNTIME_INSTANCE": "development", "KIS_MCP_TASK_ROLE": "frontend"},
    )
    worker = build_tasks_extension(
        settings,
        {"KIS_MCP_RUNTIME_INSTANCE": "development", "KIS_MCP_TASK_ROLE": "worker"},
    )
    assert frontend.docket_settings.url == "redis://127.0.0.1:6380/0"
    assert frontend.docket_settings.name == worker.docket_settings.name == "kis-mcp-development"
    assert frontend.docket_settings.concurrency == 0
    assert worker.docket_settings.concurrency == 2


def test_enabled_queue_is_instance_scoped() -> None:
    settings = _settings()
    dev = build_tasks_extension(
        settings,
        {"KIS_MCP_RUNTIME_INSTANCE": "development", "KIS_MCP_TASK_ROLE": "worker"},
    )
    op = build_tasks_extension(
        settings,
        {"KIS_MCP_RUNTIME_INSTANCE": "operation", "KIS_MCP_TASK_ROLE": "worker"},
    )
    assert dev.docket_settings.name == "kis-mcp-development"
    assert op.docket_settings.name == "kis-mcp-operation"


def test_invalid_runtime_identity_and_role_fail_closed() -> None:
    with pytest.raises(ValueError, match="TASK_RUNTIME_INSTANCE_INVALID"):
        runtime_instance({"KIS_MCP_RUNTIME_INSTANCE": "other"})
    with pytest.raises(ValueError, match="TASK_RUNTIME_ROLE_INVALID"):
        task_role({"KIS_MCP_TASK_ROLE": "other"})


def test_settings_reject_wrong_types_and_non_valkey_image(tmp_path: Path) -> None:
    payload = {
        "schema_version": 1,
        "enabled": "false",
        "backend_image": "redis:latest",
        "backend_url": "redis://127.0.0.1:6380/0",
        "queue_prefix": "kis-mcp",
        "worker_concurrency": 2,
        "redelivery_timeout_seconds": 900,
        "reconnection_delay_seconds": 5,
        "minimum_check_interval_milliseconds": 100,
    }
    path = tmp_path / "task-runtime.settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="TASK_RUNTIME_SETTINGS_INVALID"):
        load_task_runtime_settings(path)

    payload["enabled"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="TASK_RUNTIME_BACKEND_IMAGE_INVALID"):
        load_task_runtime_settings(path)

    payload["backend_image"] = "valkey/valkey:latest"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="TASK_RUNTIME_BACKEND_IMAGE_INVALID"):
        load_task_runtime_settings(path)
