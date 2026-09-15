from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Mapping, Sequence

from fastmcp_tasks import TasksExtension

TASK_ROLE_ENV = "KIS_MCP_TASK_ROLE"
RUNTIME_INSTANCE_ENV = "KIS_MCP_RUNTIME_INSTANCE"
_ALLOWED_INSTANCES = frozenset({"operation", "development"})
_ALLOWED_ROLES = frozenset({"frontend", "worker"})


@dataclass(frozen=True, slots=True)
class TaskRuntimeSettings:
    enabled: bool
    backend_image: str
    backend_url: str
    queue_prefix: str
    worker_concurrency: int
    redelivery_timeout_seconds: int
    reconnection_delay_seconds: int
    minimum_check_interval_milliseconds: int


def _settings_path() -> Path:
    return Path(__file__).resolve().parents[2] / "settings" / "task-runtime.settings.json"


def load_task_runtime_settings(path: Path | None = None) -> TaskRuntimeSettings:
    selected = path or _settings_path()
    raw = json.loads(selected.read_text(encoding="utf-8"))
    expected = {
        "schema_version", "enabled", "backend_image", "backend_url", "queue_prefix",
        "worker_concurrency", "redelivery_timeout_seconds",
        "reconnection_delay_seconds", "minimum_check_interval_milliseconds",
    }
    if set(raw) != expected or raw["schema_version"] != 1:
        raise ValueError("TASK_RUNTIME_SETTINGS_INVALID")
    if type(raw["enabled"]) is not bool:
        raise ValueError("TASK_RUNTIME_SETTINGS_INVALID")
    integer_fields = (
        "worker_concurrency", "redelivery_timeout_seconds",
        "reconnection_delay_seconds", "minimum_check_interval_milliseconds",
    )
    if any(type(raw[field]) is not int for field in integer_fields):
        raise ValueError("TASK_RUNTIME_SETTINGS_INVALID")
    settings = TaskRuntimeSettings(
        enabled=raw["enabled"],
        backend_image=str(raw["backend_image"]),
        backend_url=str(raw["backend_url"]),
        queue_prefix=str(raw["queue_prefix"]),
        worker_concurrency=raw["worker_concurrency"],
        redelivery_timeout_seconds=raw["redelivery_timeout_seconds"],
        reconnection_delay_seconds=raw["reconnection_delay_seconds"],
        minimum_check_interval_milliseconds=raw["minimum_check_interval_milliseconds"],
    )
    _validate_settings(settings)
    return settings


def _validate_settings(settings: TaskRuntimeSettings) -> None:
    prefix = "valkey/valkey:"
    if not settings.backend_image.startswith(prefix):
        raise ValueError("TASK_RUNTIME_BACKEND_IMAGE_INVALID")
    tag = settings.backend_image.removeprefix(prefix)
    version, separator, variant = tag.partition("-")
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("TASK_RUNTIME_BACKEND_IMAGE_INVALID")
    if separator and variant != "alpine":
        raise ValueError("TASK_RUNTIME_BACKEND_IMAGE_INVALID")
    if not settings.backend_url.startswith("redis://127.0.0.1:"):
        raise ValueError("TASK_RUNTIME_BACKEND_NOT_LOOPBACK_REDIS")
    if not settings.queue_prefix or not settings.queue_prefix.replace("-", "").isalnum():
        raise ValueError("TASK_RUNTIME_QUEUE_PREFIX_INVALID")
    if settings.worker_concurrency < 1 or settings.worker_concurrency > 32:
        raise ValueError("TASK_RUNTIME_WORKER_CONCURRENCY_INVALID")
    if settings.redelivery_timeout_seconds < 60:
        raise ValueError("TASK_RUNTIME_REDELIVERY_TIMEOUT_INVALID")
    if settings.reconnection_delay_seconds < 1:
        raise ValueError("TASK_RUNTIME_RECONNECTION_DELAY_INVALID")
    if settings.minimum_check_interval_milliseconds < 10:
        raise ValueError("TASK_RUNTIME_CHECK_INTERVAL_INVALID")


def runtime_instance(environment: Mapping[str, str]) -> str:
    value = environment.get(RUNTIME_INSTANCE_ENV, "").strip().lower()
    if value not in _ALLOWED_INSTANCES:
        raise ValueError("TASK_RUNTIME_INSTANCE_INVALID")
    return value


def task_role(environment: Mapping[str, str]) -> str:
    value = environment.get(TASK_ROLE_ENV, "frontend").strip().lower()
    if value not in _ALLOWED_ROLES:
        raise ValueError("TASK_RUNTIME_ROLE_INVALID")
    return value


def build_tasks_extension(
    settings: TaskRuntimeSettings,
    environment: Mapping[str, str],
) -> TasksExtension:
    if not settings.enabled:
        return TasksExtension()
    instance = runtime_instance(environment)
    role = task_role(environment)
    concurrency = settings.worker_concurrency if role == "worker" else 0
    return TasksExtension(
        url=settings.backend_url,
        name=f"{settings.queue_prefix}-{instance}",
        worker_name=f"{instance}-{role}",
        concurrency=concurrency,
        redelivery_timeout=timedelta(seconds=settings.redelivery_timeout_seconds),
        reconnection_delay=timedelta(seconds=settings.reconnection_delay_seconds),
        minimum_check_interval=timedelta(
            milliseconds=settings.minimum_check_interval_milliseconds
        ),
    )


def install_task_runtime(server, *, environment: Mapping[str, str] | None = None) -> None:
    selected_environment = environment if environment is not None else os.environ
    settings = load_task_runtime_settings()
    server.add_extension(build_tasks_extension(settings, selected_environment))


async def run_worker(instance: str) -> None:
    if instance not in _ALLOWED_INSTANCES:
        raise ValueError("TASK_RUNTIME_INSTANCE_INVALID")
    settings = load_task_runtime_settings()
    if not settings.enabled:
        raise RuntimeError("TASK_RUNTIME_DURABLE_BACKEND_DISABLED")
    os.environ[RUNTIME_INSTANCE_ENV] = instance
    os.environ[TASK_ROLE_ENV] = "worker"
    from .config import load_runtime_config
    from .server import build_server

    server = build_server(load_runtime_config())
    async with server._lifespan_manager():
        while True:
            await asyncio.sleep(3600)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one independent durable KIS task worker.")
    parser.add_argument("--instance", choices=tuple(sorted(_ALLOWED_INSTANCES)), required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    asyncio.run(run_worker(args.instance))


if __name__ == "__main__":
    main()
