from __future__ import annotations

import asyncio

from fastmcp import Client, Context, FastMCP
from fastmcp_tasks.client import _send_get, call_tool_task

from kis_mcp.mcp2026 import LONG_RUNNING_TASK_CONFIG, install_mcp2026_tasks


class _CoreOnlyClient(Client):
    """FastMCP test client with automatic internal extensions disabled."""

    _auto_internal_extensions = False


def test_optional_task_falls_back_to_synchronous_core_protocol() -> None:
    server = FastMCP("mcp2026-sync-fallback")
    install_mcp2026_tasks(server)

    @server.tool(task=LONG_RUNNING_TASK_CONFIG)
    async def execution_mode(ctx: Context) -> dict[str, object]:
        return {"background": ctx.is_background_task, "task_id": ctx.task_id}

    async def run() -> None:
        async with _CoreOnlyClient(server) as client:
            result = await client.call_tool("execution_mode", {})
            assert result.structured_content == {"background": False, "task_id": None}

    asyncio.run(run())


def test_task_handle_survives_client_disconnect_and_result_is_retrievable() -> None:
    server = FastMCP("mcp2026-reconnect")
    install_mcp2026_tasks(server)

    @server.tool(task=LONG_RUNNING_TASK_CONFIG)
    async def delayed_result(ctx: Context) -> dict[str, object]:
        await asyncio.sleep(0.15)
        return {"task_id": ctx.task_id, "background": ctx.is_background_task}

    async def run() -> None:
        # Keep the server lifespan alive while dropping the creating transport.
        # FastMCP's in-memory Client otherwise owns a nested server lifespan,
        # which would model server shutdown rather than connection loss.
        async with server._lifespan_manager():
            async with Client(server) as first_client:
                handle = await call_tool_task(first_client, "delayed_result", {})
                task_id = handle.task_id
                assert handle.create_result.result_type == "task"
                assert handle.create_result.ttl_ms is not None
                assert handle.create_result.ttl_ms > 300_000

            async with Client(server) as reconnected_client:
                state = await _send_get(reconnected_client.session, task_id)
                for _ in range(50):
                    if state.status in {"completed", "failed", "cancelled"}:
                        break
                    await asyncio.sleep(0.02)
                    state = await _send_get(reconnected_client.session, task_id)

                assert state.status == "completed"
                assert state.result_type == "complete"
                assert state.task_id == task_id
                assert state.result is not None
                assert state.result.get("structuredContent") == {
                    "task_id": task_id,
                    "background": True,
                }

    asyncio.run(run())


def test_selected_long_running_tools_register_as_optional_tasks() -> None:
    from kis_mcp.commissioning_runtime.platform import register_commissioning_tools
    from kis_mcp.workflows.code_review.tools import register_agent_tools
    from kis_mcp.workflows.completion.tools import register_completion_tool
    from kis_mcp.workflows.verification.tools import register_verification_tool

    class Stub:
        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

    server = FastMCP("mcp2026-long-running-tools")
    register_verification_tool(server, Stub())
    register_completion_tool(server, Stub())
    register_commissioning_tools(server, Stub(), Stub())
    register_agent_tools(server, Stub())

    async def run() -> None:
        for name in (
            "run_verification",
            "prepare_reviewable_pull_request",
            "kis_post_merge_commissioning_run",
            "review_change_with_agent",
        ):
            tool = await server.get_tool(name)
            assert tool.task_config.mode == "optional"
            assert tool.task_config.poll_interval == LONG_RUNNING_TASK_CONFIG.poll_interval

    asyncio.run(run())
