from __future__ import annotations

import asyncio

from fastmcp import Client, Context, FastMCP
from fastmcp_tasks.client import _send_get, call_tool_task

from kis_mcp.mcp2026 import LONG_RUNNING_TASK_CONFIG, install_mcp2026_tasks
from kis_mcp.workflows.completion.contracts import CompletionResult
from kis_mcp.workflows.completion.tools import register_completion_tool
from kis_mcp.workflows.verification.contracts import VerificationResult
from kis_mcp.workflows.verification.tools import register_verification_tool


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


def test_run_verification_executes_synchronously_even_when_client_supports_tasks() -> None:
    class VerificationStub:
        async def run(self, **kwargs):
            return VerificationResult(
                verification_id=kwargs["verification_id"],
                title="Pytest",
                category="test",
                source_path="tests/test_sample.py",
                profile="python",
                arguments=("-m", "pytest", "-q"),
                command_identity="a" * 64,
                status="passed",
                exit_code=0,
                duration_ms=1,
                evidence="ok",
                failure_classification="none",
                truncated=False,
            )

    server = FastMCP("mcp2026-verification-sync")
    install_mcp2026_tasks(server)
    register_verification_tool(server, VerificationStub())

    async def run() -> None:
        async with Client(server) as client:
            result = await client.call_tool(
                "run_verification",
                {"project": r"C:\Projects\fixture", "verification_id": "python-pytest"},
            )
            assert result.structured_content["status"] == "passed"

    asyncio.run(run())


def test_completion_task_survives_disconnect_without_duplicate_execution() -> None:
    class CompletionStub:
        def __init__(self) -> None:
            self.calls = 0

        async def prepare(self, **kwargs):
            self.calls += 1
            await asyncio.sleep(0.1)
            return CompletionResult(
                project_id=kwargs["project_id"],
                source_commit_sha=kwargs["commit"],
                published_head_sha="d" * 40,
                branch=kwargs["branch"],
                execution={"contract": "change-execution-result-v2", "status": "passed"},
                publication={"state": "published", "source_commit_sha": kwargs["commit"], "commit_sha": "d" * 40},
                pull_request={"state": "open", "pull_number": 9, "head_sha": "d" * 40},
                operation_id="prp-" + "f" * 64,
                operation_state="applied",
                elapsed_ms=1,
                stage_timings_ms={"verification": 1, "publication": 0, "pull_request": 0},
            )

    server = FastMCP("mcp2026-completion-reconnect")
    install_mcp2026_tasks(server)
    service = CompletionStub()
    register_completion_tool(server, service)
    completion = asyncio.run(server.get_tool("prepare_reviewable_pull_request"))
    assert completion.task_config.mode == "required"
    arguments = {
        "project_id": "kis-mcp",
        "commit": "a" * 40,
        "source_base": "e" * 40,
        "branch": "change/628-task-durable-completion-502",
        "expected_remote_branch": None,
        "expected_remote_default": "b" * 40,
        "title": "Durable completion",
        "body": "Ready for review.",
        "approved": True,
    }

    async def run() -> None:
        async with server._lifespan_manager():
            async with Client(server) as first_client:
                handle = await call_tool_task(
                    first_client,
                    "prepare_reviewable_pull_request",
                    arguments,
                )
                task_id = handle.task_id
                assert handle.create_result.result_type == "task"
                assert handle.create_result.ttl_ms is not None
                assert handle.create_result.ttl_ms > 0
                durable = await _send_get(first_client.session, task_id)
                assert durable.task_id == task_id
                assert durable.status in {"working", "completed"}

            async with Client(server) as reconnected_client:
                state = await _send_get(reconnected_client.session, task_id)
                for _ in range(50):
                    if state.status in {"completed", "failed", "cancelled"}:
                        break
                    await asyncio.sleep(0.02)
                    state = await _send_get(reconnected_client.session, task_id)

                assert state.status == "completed"
                assert state.result is not None
                assert state.result.get("structuredContent", {}).get("status") == "reviewable"

        assert service.calls == 1

        async with _CoreOnlyClient(server) as sync_client:
            result = await sync_client.call_tool(
                "prepare_reviewable_pull_request_sync",
                arguments,
            )
            assert result.structured_content["status"] == "reviewable"
        assert service.calls == 2

    asyncio.run(run())


def test_selected_long_running_tools_register_as_optional_tasks() -> None:
    from kis_mcp.commissioning_runtime.platform import register_commissioning_tools
    from kis_mcp.workflows.code_review.tools import register_agent_tools
    from kis_mcp.workflows.completion.tools import register_completion_tool

    class Stub:
        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

    server = FastMCP("mcp2026-long-running-tools")
    register_verification_tool(server, Stub())
    register_completion_tool(server, Stub())
    register_commissioning_tools(server, Stub(), Stub())
    register_agent_tools(server, Stub())

    async def run() -> None:
        verification = await server.get_tool("run_verification")
        assert verification.task_config.mode == "forbidden"
        assert verification.task_config.supports_tasks() is False

        completion = await server.get_tool("prepare_reviewable_pull_request")
        assert completion.task_config.mode == "required"
        assert completion.task_config.poll_interval == LONG_RUNNING_TASK_CONFIG.poll_interval

        completion_sync = await server.get_tool("prepare_reviewable_pull_request_sync")
        assert completion_sync.task_config.mode == "forbidden"
        assert completion_sync.task_config.supports_tasks() is False

        for name in (
            "kis_post_merge_commissioning_run",
            "review_change_with_agent",
        ):
            tool = await server.get_tool(name)
            assert tool.task_config.mode == "optional"
            assert tool.task_config.poll_interval == LONG_RUNNING_TASK_CONFIG.poll_interval

    asyncio.run(run())
