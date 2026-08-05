from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

import pytest
from fastmcp import Client, FastMCP

from kis_mcp.desktop_commander import DesktopCommanderEffectResolver
from kis_mcp.middleware import ThreeRuleMiddleware
from kis_mcp.policy import ThreeRulePolicy
from kis_mcp.process_state import ProcessStateRegistry
from kis_mcp.runtime_observability import RuntimeObservability


PROJECT_BOUNDARY = r"C:\Projects"


def _middleware(resolver: DesktopCommanderEffectResolver) -> ThreeRuleMiddleware:
    def quarantine_paths(_paths: Sequence[str]) -> list[dict[str, Any]]:
        raise AssertionError("quarantine not expected")

    return ThreeRuleMiddleware(
        resolver=resolver,
        policy=ThreeRulePolicy(
            project_boundary=PROJECT_BOUNDARY,
            quarantine_root=r"C:\Projects\.kis-mcp\quarantine",
        ),
        quarantine_paths=quarantine_paths,
    )


def test_successful_interactive_process_calls_reuse_effective_working_directory() -> None:
    server = FastMCP("process-state-test")
    calls: list[tuple[object, ...]] = []
    resolver = DesktopCommanderEffectResolver(
        project_boundary=PROJECT_BOUNDARY,
        provider_state_file=r"C:\Projects\.kis-mcp\desktop-commander.json",
    )

    @server.tool
    def start_process(command: str, cwd: str) -> str:
        calls.append(("start", command, cwd))
        return "Process started with PID 42"

    @server.tool
    def interact_with_process(pid: int, input: str) -> str:
        calls.append(("interact", pid, input))
        return "input accepted"

    server.add_middleware(_middleware(resolver))

    async def run() -> None:
        async with Client(server) as client:
            await client.call_tool(
                "start_process",
                {"command": "pwsh", "cwd": r"C:\Projects\kis-mcp"},
            )
            await client.call_tool(
                "interact_with_process",
                {"pid": 42, "input": r"Set-Location C:\Windows\Temp"},
            )
            with pytest.raises(Exception, match="HR-001"):
                await client.call_tool(
                    "interact_with_process",
                    {"pid": 42, "input": r"Set-Content .\outside.txt data"},
                )

    asyncio.run(run())
    assert calls == [
        ("start", "pwsh", r"C:\Projects\kis-mcp"),
        ("interact", 42, r"Set-Location C:\Windows\Temp"),
    ]


@pytest.mark.parametrize(
    "startup_command",
    [
        r"cmd /k cd C:\Projects-old",
        r'powershell -NoExit -Command "Set-Location C:\Projects-old"',
    ],
)
def test_persistent_startup_shell_retains_its_final_working_directory(
    startup_command: str,
) -> None:
    server = FastMCP("process-startup-state-test")
    calls: list[tuple[object, ...]] = []
    resolver = DesktopCommanderEffectResolver(
        project_boundary=PROJECT_BOUNDARY,
        provider_state_file=r"C:\Projects\.kis-mcp\desktop-commander.json",
    )

    @server.tool
    def start_process(command: str) -> str:
        calls.append(("start", command))
        return "Process started with PID 51"

    @server.tool
    def interact_with_process(pid: int, input: str) -> str:
        calls.append(("interact", pid, input))
        return "input accepted"

    server.add_middleware(_middleware(resolver))

    async def run() -> None:
        async with Client(server) as client:
            await client.call_tool(
                "start_process",
                {"command": startup_command},
            )
            with pytest.raises(Exception, match="HR-001"):
                await client.call_tool(
                    "interact_with_process",
                    {"pid": 51, "input": "echo data > output.txt"},
                )

    asyncio.run(run())
    assert calls == [("start", startup_command)]


def test_pushd_popd_and_process_termination_update_or_clear_state() -> None:
    server = FastMCP("process-stack-test")
    calls: list[tuple[object, ...]] = []
    resolver = DesktopCommanderEffectResolver(
        project_boundary=PROJECT_BOUNDARY,
        provider_state_file=r"C:\Projects\.kis-mcp\desktop-commander.json",
    )

    @server.tool
    def start_process(command: str, cwd: str) -> str:
        calls.append(("start", command, cwd))
        return "PID: 77"

    @server.tool
    def interact_with_process(pid: int, input: str) -> str:
        calls.append(("interact", pid, input))
        return "ok"

    @server.tool
    def kill_process(pid: int) -> str:
        calls.append(("kill", pid))
        return "terminated"

    server.add_middleware(_middleware(resolver))

    async def run() -> None:
        async with Client(server) as client:
            await client.call_tool(
                "start_process",
                {"command": "cmd", "cwd": r"C:\Projects\kis-mcp"},
            )
            await client.call_tool(
                "interact_with_process",
                {"pid": 77, "input": r"pushd C:\Windows\Temp"},
            )
            await client.call_tool(
                "interact_with_process",
                {"pid": 77, "input": "popd"},
            )
            allowed = await client.call_tool(
                "interact_with_process",
                {"pid": 77, "input": r"Set-Content .\inside.txt data"},
            )
            assert "ok" in allowed.content[0].text
            await client.call_tool("kill_process", {"pid": 77})
            reset = await client.call_tool(
                "interact_with_process",
                {"pid": 77, "input": r"Set-Content .\default.txt data"},
            )
            assert "ok" in reset.content[0].text

    asyncio.run(run())
    assert calls[-2:] == [("kill", 77), ("interact", 77, r"Set-Content .\default.txt data")]


def test_process_state_publishes_redacted_active_process_lifecycle() -> None:
    observability = RuntimeObservability(max_recent_calls=5, max_policy_decisions=5)
    registry = ProcessStateRegistry(observability=observability)

    registry.observe_success(
        "start_process",
        {"command": "pwsh", "cwd": r"C:\Projects\secret-project"},
        "Process started with PID 99",
        project_boundary=PROJECT_BOUNDARY,
    )
    registry.observe_success(
        "interact_with_process",
        {"pid": 99, "input": "private command value"},
        "private result body",
        project_boundary=PROJECT_BOUNDARY,
    )

    active = observability.snapshot().active_processes
    assert [(item.pid, item.cwd, item.shell, item.interaction_count) for item in active] == [
        (99, r"C:\Projects\secret-project", "powershell", 1)
    ]
    assert "private command value" not in str(observability.snapshot().to_dict())
    assert "private result body" not in str(observability.snapshot().to_dict())

    registry.observe_success(
        "kill_process",
        {"pid": 99},
        "terminated",
        project_boundary=PROJECT_BOUNDARY,
    )
    assert observability.snapshot().active_processes == ()
