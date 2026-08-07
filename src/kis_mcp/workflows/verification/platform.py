from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...config import RuntimeConfig
from ...discover.service import InspectProjectService
from .execution import VerificationExecutionService
from .tools import register_verification_tool


async def _run_with_middleware(
    server: FastMCP,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    result = await server.call_tool(
        tool_name,
        arguments,
        run_middleware=True,
    )
    if getattr(result, "is_error", False):
        text = _result_text(result) or "Nested Work operation failed."
        raise ToolError(text)
    return result


def register_platform_verification(
    server: FastMCP,
    runtime: RuntimeConfig,
) -> None:
    inspector = InspectProjectService(
        boundary=Path(runtime.project_boundary),
        settings=runtime.discover_settings,
    )

    async def runner(tool_name: str, arguments: dict[str, Any]) -> Any:
        return await _run_with_middleware(server, tool_name, arguments)

    register_verification_tool(
        server,
        VerificationExecutionService(
            inspector=inspector,
            runner=runner,
        ),
    )


def _result_text(result: Any) -> str:
    return "\n".join(
        text
        for block in getattr(result, "content", ())
        if isinstance((text := getattr(block, "text", None)), str)
    ).strip()


__all__ = ["register_platform_verification"]
