from __future__ import annotations

import asyncio
import os

import pytest
from fastmcp import Client, FastMCP
from fastmcp_tasks.client import _send_get, call_tool_task

from kis_mcp.mcp2026 import DURABLE_EXTERNAL_TASK_CONFIG
from kis_mcp.task_runtime import TaskRuntimeSettings, build_tasks_extension


def _redis_settings(url: str) -> TaskRuntimeSettings:
    return TaskRuntimeSettings(
        enabled=True,
        backend_image="valkey/valkey:9.1.2-alpine",
        backend_url=url,
        queue_prefix="kis-mcp-resilience-test",
        worker_concurrency=1,
        redelivery_timeout_seconds=60,
        reconnection_delay_seconds=1,
        minimum_check_interval_milliseconds=20,
    )


def _server(settings: TaskRuntimeSettings, role: str) -> FastMCP:
    server = FastMCP(f"task-resilience-{role}")
    server.add_extension(
        build_tasks_extension(
            settings,
            {"KIS_MCP_RUNTIME_INSTANCE": "development", "KIS_MCP_TASK_ROLE": role},
        )
    )

    @server.tool(task=DURABLE_EXTERNAL_TASK_CONFIG)
    async def resilient_probe() -> dict[str, str]:
        await asyncio.sleep(0.25)
        return {"state": "completed"}

    return server


def test_task_survives_frontend_restart_with_independent_worker() -> None:
    url = os.environ.get("KIS_MCP_TEST_REDIS_URL")
    if not url:
        pytest.skip("KIS_MCP_TEST_REDIS_URL is not configured")
    settings = _redis_settings(url)
    worker = _server(settings, "worker")

    async def run() -> None:
        async with worker._lifespan_manager():
            frontend = _server(settings, "frontend")
            async with frontend._lifespan_manager():
                async with Client(frontend) as client:
                    handle = await call_tool_task(client, "resilient_probe", {})
                    task_id = handle.task_id
                    state = await _send_get(client.session, task_id)
                    assert state.status in {"working", "completed"}

            replacement = _server(settings, "frontend")
            async with replacement._lifespan_manager():
                async with Client(replacement) as reconnected:
                    state = await _send_get(reconnected.session, task_id)
                    for _ in range(100):
                        if state.status in {"completed", "failed", "cancelled"}:
                            break
                        await asyncio.sleep(0.02)
                        state = await _send_get(reconnected.session, task_id)
                    assert state.status == "completed"
                    assert state.result is not None
                    assert state.result.get("structuredContent") == {"state": "completed"}

    asyncio.run(run())
