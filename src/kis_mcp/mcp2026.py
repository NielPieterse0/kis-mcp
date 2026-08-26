from __future__ import annotations

from datetime import timedelta

from fastmcp import FastMCP
from fastmcp.utilities.tasks import TaskConfig
from fastmcp_tasks import TasksExtension

MCP_TASKS_EXTENSION_ID = "io.modelcontextprotocol/tasks"
LONG_RUNNING_TASK_CONFIG = TaskConfig(
    mode="optional",
    poll_interval=timedelta(seconds=1),
)


def install_mcp2026_tasks(server: FastMCP) -> None:
    """Install the MCP 2026 Tasks extension without creating a second KIS authority."""
    server.add_extension(TasksExtension())


__all__ = [
    "LONG_RUNNING_TASK_CONFIG",
    "MCP_TASKS_EXTENSION_ID",
    "install_mcp2026_tasks",
]
