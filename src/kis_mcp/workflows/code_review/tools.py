from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .reviewer import CodeReviewAgent


def register_agent_tools(server: FastMCP, agent: CodeReviewAgent) -> None:
    """Register the single advisory code-review agent additively."""

    agent_server = FastMCP("kis-mcp-code-review-agent")

    @agent_server.tool
    def benchmark_nvidia_model(model: str, runs: int = 1) -> dict[str, Any]:
        """Smoke-test one allowlisted experimental NVIDIA model.

        This benchmark never changes production reviewer profiles. It runs one
        through three fixed read-only review probes, records end-to-end latency,
        and requires both correctness and security findings on every run.
        """

        try:
            return agent.benchmark_nvidia_model(model=model, runs=runs)
        except Exception as exc:
            raise ToolError(f"AGENT_BENCHMARK_FAILED:{type(exc).__name__}") from exc

    @agent_server.tool
    def review_change_with_agent(
        path: str,
        instructions: str = "",
        backend: str | None = None,
        model: str | None = None,
        review_type: str = "code-quality",
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        deadline_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Review one bounded Git change source without modifying it.

        review_type is code-quality (default), safety-security, architecture,
        performance, test-quality, documentation, or api-contracts. With no
        backend/model override, KIS selects the qualified purpose-specific
        NVIDIA route, streams provider deltas for liveness, validates the strict
        result contract, and uses only that lane's qualified model fallback.
        Explicit legacy model aliases nano, super, or ultra select NVIDIA
        directly for compatibility. Supplying backend=codex-cli invokes Codex
        directly without fallback and is not an automatic production fallback.
        """

        try:
            return agent.review(
                path,
                instructions=instructions,
                backend=backend,
                model=model,
                review_type=review_type,
                source=source,
                commit_ref=commit_ref,
                base_ref=base_ref,
                head_ref=head_ref,
                deadline_seconds=deadline_seconds,
            )
        except Exception as exc:
            raise ToolError(f"AGENT_REVIEW_FAILED:{type(exc).__name__}") from exc

    server.mount(agent_server)


__all__ = ["register_agent_tools"]
