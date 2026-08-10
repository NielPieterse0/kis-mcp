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
        model: str | None = None,
    ) -> dict[str, Any]:
        """Review one Git working-tree change without modifying it.

        For NVIDIA NIM, model may be nano, super, or ultra: nano is for fast
        focused iteration, super is the default substantive review, and ultra
        is for the deepest high-impact analysis. Supplying model selects NVIDIA
        explicitly; NVIDIA model aliases are invalid with the Codex backend.
        """

        try:
            return agent.review(
                path,
                instructions=instructions,
                backend=backend,
                model=model,
            )
        except Exception as exc:
            raise ToolError(f"AGENT_REVIEW_FAILED:{type(exc).__name__}") from exc

    server.mount(agent_server)


__all__ = ["register_agent_tools"]
