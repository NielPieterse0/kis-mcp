from __future__ import annotations

from datetime import timedelta

from fastmcp import FastMCP
from fastmcp.utilities.tasks import TaskConfig

from .task_runtime import install_task_runtime

MCP_TASKS_EXTENSION_ID = "io.modelcontextprotocol/tasks"
LONG_RUNNING_TASK_CONFIG = TaskConfig(
    mode="optional",
    poll_interval=timedelta(seconds=1),
)
DURABLE_EXTERNAL_TASK_CONFIG = TaskConfig(
    mode="required",
    poll_interval=timedelta(seconds=1),
)
SYNC_FALLBACK_TASK_CONFIG = TaskConfig(mode="forbidden")


def install_mcp2026_tasks(server: FastMCP) -> None:
    """Install the configured MCP 2026 task runtime without creating KIS authority."""
    install_task_runtime(server)


__all__ = [
    "DURABLE_EXTERNAL_TASK_CONFIG",
    "LONG_RUNNING_TASK_CONFIG",
    "MCP_TASKS_EXTENSION_ID",
    "SYNC_FALLBACK_TASK_CONFIG",
    "install_mcp2026_tasks",
]
