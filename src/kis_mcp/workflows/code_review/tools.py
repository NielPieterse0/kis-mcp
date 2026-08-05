from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .reviewer import CodeReviewAgent


def register_agent_tools(server: FastMCP, agent: CodeReviewAgent) -> None:
    """Register the single advisory code-review agent additively."""

    agent_server = FastMCP("kis-mcp-code-review-agent")

    @agent_server.tool
    def review_change_with_agent(
        path: str,
        instructions: str = "",
        backend: str | None = None,
    ) -> dict[str, Any]:
        """Review one current Git working-tree change without modifying the repository."""

        try:
            return agent.review(path, instructions=instructions, backend=backend)
        except Exception as exc:
            raise ToolError(f"AGENT_REVIEW_FAILED:{type(exc).__name__}") from exc

    server.mount(agent_server)


__all__ = ["register_agent_tools"]
