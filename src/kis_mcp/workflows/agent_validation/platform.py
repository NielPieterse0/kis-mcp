from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...config import RuntimeConfig
from .execution import AgentValidationService
from .settings import AgnixValidationSettings
from .tools import register_agent_validation_tool


async def _run_with_middleware(
    server: FastMCP,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    result = await server.call_tool(tool_name, arguments, run_middleware=True)
    if getattr(result, "is_error", False):
        text = "\n".join(
            block.text
            for block in getattr(result, "content", ())
            if isinstance(getattr(block, "text", None), str)
        ).strip()
        raise ToolError(text or "Nested Work operation failed.")
    return result


def register_platform_agent_validation(
    server: FastMCP,
    runtime: RuntimeConfig,
    *,
    repository_root: Path | None = None,
) -> None:
    root = (repository_root or Path(__file__).resolve().parents[4]).resolve()
    settings = AgnixValidationSettings.load(
        root / "settings" / "bootstrap" / "agnix.install.json"
    )

    async def runner(tool_name: str, arguments: dict[str, Any]) -> Any:
        return await _run_with_middleware(server, tool_name, arguments)

    register_agent_validation_tool(
        server,
        AgentValidationService(
            boundary=Path(runtime.project_boundary),
            settings=settings,
            runner=runner,
        ),
    )


__all__ = ["register_platform_agent_validation"]
