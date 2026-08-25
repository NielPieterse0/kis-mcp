from __future__ import annotations

import asyncio
from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.desktop_commander import DesktopCommanderEffectResolver
from kis_mcp.middleware import BoundaryObservabilityMiddleware, ThreeRuleMiddleware
from kis_mcp.policy import ThreeRulePolicy
from kis_mcp.quarantine import QuarantineError
from kis_mcp.runtime_observability import RuntimeObservability

PROJECT_BOUNDARY = r"C:\Projects"
QUARANTINE_ROOT = r"C:\Projects\.kis-mcp\quarantine"
PROVIDER_STATE = r"C:\Projects\.kis-mcp\desktop-commander\config.json"


def _middleware(calls: list[object]) -> ThreeRuleMiddleware:
    def quarantine_paths(paths: Sequence[str]) -> list[dict[str, Any]]:
        normalized = list(paths)
        calls.append(("quarantine", normalized))
        return [{"original_path": path} for path in normalized]

    return ThreeRuleMiddleware(
        resolver=DesktopCommanderEffectResolver(
            project_boundary=PROJECT_BOUNDARY,
            provider_state_file=PROVIDER_STATE,
        ),
        policy=ThreeRulePolicy(
            project_boundary=PROJECT_BOUNDARY,
            quarantine_root=QUARANTINE_ROOT,
        ),
        quarantine_paths=quarantine_paths,
    )


def test_direct_delete_is_rewritten_to_quarantine_result() -> None:
    server = FastMCP("middleware-test")
    calls: list[object] = []

    @server.tool
    def delete_file(path: str) -> str:
        calls.append(("delete", path))
        return "permanently deleted"

    server.add_middleware(_middleware(calls))

    async def run() -> None:
        async with Client(server) as client:
            result = await client.call_tool(
                "delete_file",
                {"path": r"C:\Projects\kis-mcp\obsolete.txt"},
            )
            assert "quarantined" in result.content[0].text

    asyncio.run(run())
    assert calls == [
        ("quarantine", [r"C:\Projects\kis-mcp\obsolete.txt"]),
    ]


def test_quarantine_failure_returns_hr003_error() -> None:
    server = FastMCP("middleware-failure-test")

    @server.tool
    def delete_file(path: str) -> str:
        return path

    def fail_quarantine(_paths: Sequence[str]) -> list[dict[str, Any]]:
        raise QuarantineError("simulated move failure")

    server.add_middleware(
        ThreeRuleMiddleware(
            resolver=DesktopCommanderEffectResolver(
                project_boundary=PROJECT_BOUNDARY,
                provider_state_file=PROVIDER_STATE,
            ),
            policy=ThreeRulePolicy(
                project_boundary=PROJECT_BOUNDARY,
                quarantine_root=QUARANTINE_ROOT,
            ),
            quarantine_paths=fail_quarantine,
        )
    )

    async def run() -> None:
        async with Client(server) as client:
            with pytest.raises(Exception, match="HR-003_QUARANTINE_FAILED"):
                await client.call_tool(
                    "delete_file",
                    {"path": r"C:\Projects\kis-mcp\obsolete.txt"},
                )

    asyncio.run(run())


def test_network_only_tools_are_hidden() -> None:
    server = FastMCP("middleware-list-test")
    calls: list[object] = []

    @server.tool
    def give_feedback_to_desktop_commander(message: str) -> str:
        calls.append(("feedback", message))
        return message

    @server.tool
    def ordinary_local_tool() -> str:
        return "ok"

    server.add_middleware(_middleware(calls))

    async def run() -> set[str]:
        async with Client(server) as client:
            tools = await client.list_tools()
            with pytest.raises(Exception, match="UNSUPPORTED_PROVIDER_TOOL"):
                await client.call_tool(
                    "give_feedback_to_desktop_commander",
                    {"message": "test"},
                )
            return {tool.name for tool in tools}

    names = asyncio.run(run())
    assert names == {"ordinary_local_tool"}
    assert calls == []


def test_provider_url_mode_is_not_exposed_or_callable() -> None:
    server = FastMCP("middleware-url-mode-test")
    calls: list[object] = []

    @server.tool
    def read_file(path: str, isUrl: bool = False) -> str:
        calls.append((path, isUrl))
        return path

    server.add_middleware(_middleware(calls))

    async def run() -> None:
        async with Client(server) as client:
            tools = await client.list_tools()
            read_tool = next(tool for tool in tools if tool.name == "read_file")
            assert "isUrl" not in read_tool.input_schema.get("properties", {})
            with pytest.raises(Exception, match="UNSUPPORTED_PROVIDER_MODE"):
                await client.call_tool(
                    "read_file",
                    {"path": "https://example.com/data", "isUrl": True},
                )

    asyncio.run(run())
    assert calls == []


def test_unresolved_git_clean_delete_is_blocked_only_under_hr003() -> None:
    server = FastMCP("middleware-git-clean-test")
    calls: list[object] = []

    @server.tool
    def start_process(command: str, cwd: str) -> str:
        calls.append((command, cwd))
        return "executed"

    server.add_middleware(_middleware(calls))

    async def run() -> None:
        async with Client(server) as client:
            with pytest.raises(Exception, match="HR-003_QUARANTINE_REQUIRED"):
                await client.call_tool(
                    "start_process",
                    {"command": "git clean -fd", "cwd": r"C:\Projects\kis-mcp"},
                )

    asyncio.run(run())
    assert calls == []


@pytest.mark.parametrize(
    "command",
    [
        r'cmd /c "echo data > %USERPROFILE%\Desktop\out.txt"',
        r'cmd /c "echo data > %USERPROFILE:~0,3%\prefix.txt"',
        r'cmd /c "echo data > %ProgramFiles(x86)%\out.txt"',
        r'cmd /V:ON /c "echo data > !USERPROFILE!\delayed.txt"',
        r'cmd /V:ON /c "echo data > !ProgramFiles(x86)!\delayed.txt"',
        r'cmd /V:ON /c "echo data > !FOO-BAR!\delayed.txt"',
        r'pwsh -Command "Set-Content -Path $env:USERPROFILE\out.txt -Value data"',
        r'pwsh -Command "Set-Content -Path $HOME\profile.txt -Value data"',
        r'pwsh -Command "Set-Content -Path $ENV:USERPROFILE\mixed.txt -Value data"',
        r'pwsh -Command "Remove-Item ${env:USERPROFILE}\old.txt"',
        r'cmd /c "move C:\Projects\kis-mcp\a.txt %USERPROFILE%\Desktop\b.txt"',
        r'pwsh -Command "New-Item $(Join-Path $env:USERPROFILE out.txt)"',
    ],
)
def test_unresolved_shell_mutation_is_structurally_blocked_before_forwarding(
    command: str,
) -> None:
    server = FastMCP("middleware-unresolved-mutation-test")
    calls: list[object] = []

    @server.tool
    def start_process(command: str, cwd: str) -> str:
        calls.append((command, cwd))
        return "executed"

    server.add_middleware(_middleware(calls))

    async def run() -> None:
        async with Client(server) as client:
            with pytest.raises(Exception, match="INVALID_INVOCATION_PATH") as error:
                await client.call_tool(
                    "start_process",
                    {"command": command, "cwd": r"C:\Projects\kis-mcp"},
                )
            assert "HR-001" not in str(error.value)
            assert "HR-003" not in str(error.value)

    asyncio.run(run())
    assert calls == []


@pytest.mark.parametrize(
    ("target", "redirection"),
    [
        ("''" + "$env:USERPROFILE" + r"'\out.txt'", False),
        ("'prefix'" + "$env:USERPROFILE" + "'suffix'", False),
        ("''" + "$env:USERPROFILE" + r"'\out.txt'", True),
        ("'prefix'" + "$env:USERPROFILE" + "'suffix'", True),
    ],
)
def test_powershell_mixed_quote_mutation_is_blocked_before_forwarding(
    target: str,
    redirection: bool,
) -> None:
    server = FastMCP("middleware-powershell-mixed-quote-test")
    calls: list[object] = []

    @server.tool
    def start_process(command: str, cwd: str) -> str:
        calls.append((command, cwd))
        return "executed"

    server.add_middleware(_middleware(calls))
    payload = (
        "echo data > " + target
        if redirection
        else "Set-Content -Path " + target + " -Value data"
    )
    command = 'pwsh -Command "' + payload + '"'

    async def run() -> None:
        async with Client(server) as client:
            with pytest.raises(Exception, match="INVALID_INVOCATION_PATH") as error:
                await client.call_tool(
                    "start_process",
                    {"command": command, "cwd": r"C:\Projects\kis-mcp"},
                )
            assert "HR-001" not in str(error.value)
            assert "HR-003" not in str(error.value)

    asyncio.run(run())
    assert calls == []


@pytest.mark.parametrize(
    "command",
    [
        r'cmd /c "echo data > C:\Projects\kis-mcp\100%.txt"',
        r'cmd /V:OFF /c "echo data > C:\Projects\kis-mcp\!literal!.txt"',
        r'''pwsh -Command "Set-Content -LiteralPath 'C:\Projects\kis-mcp\${literal}.txt' -Value data"''',
        r'''pwsh -Command "Set-Content -LiteralPath 'C:\Projects\kis-mcp\$(literal).txt' -Value data"''',
    ],
)
def test_literal_shell_markers_are_forwarded_when_statically_bounded(command: str) -> None:
    server = FastMCP("middleware-literal-marker-test")
    calls: list[object] = []

    @server.tool
    def start_process(command: str, cwd: str) -> str:
        calls.append((command, cwd))
        return "executed"

    server.add_middleware(_middleware(calls))

    async def run() -> None:
        async with Client(server) as client:
            result = await client.call_tool(
                "start_process",
                {"command": command, "cwd": r"C:\Projects\kis-mcp"},
            )
            assert "executed" in result.content[0].text

    asyncio.run(run())
    assert calls == [(command, r"C:\Projects\kis-mcp")]


def test_provider_restriction_fields_are_gateway_managed() -> None:
    server = FastMCP("middleware-provider-config-test")
    calls: list[object] = []

    @server.tool
    def set_config_value(key: str, value: Any) -> str:
        calls.append((key, value))
        return "updated"

    server.add_middleware(_middleware(calls))

    async def run() -> None:
        async with Client(server) as client:
            tools = await client.list_tools()
            config_tool = next(tool for tool in tools if tool.name == "set_config_value")
            excluded = config_tool.input_schema["properties"]["key"]["not"]["enum"]
            assert excluded == ["allowedDirectories", "blockedCommands"]

            with pytest.raises(Exception, match="PROVIDER_CONFIGURATION_INVARIANT"):
                await client.call_tool(
                    "set_config_value",
                    {"key": "blockedCommands", "value": ["sudo"]},
                )

            result = await client.call_tool(
                "set_config_value",
                {"key": "fileReadLineLimit", "value": 500},
            )
            assert "updated" in result.content[0].text

    asyncio.run(run())
    assert calls == [("fileReadLineLimit", 500)]


def test_middleware_records_redacted_allowed_and_blocked_calls() -> None:
    server = FastMCP("middleware-observability-test")
    registry = RuntimeObservability(max_recent_calls=10, max_policy_decisions=10)
    resolver = DesktopCommanderEffectResolver(
        project_boundary=PROJECT_BOUNDARY,
        provider_state_file=PROVIDER_STATE,
        observability=registry,
    )

    @server.tool
    def read_file(path: str) -> str:
        return f"result body for {path}"

    @server.tool
    def execute_command(command: str) -> str:
        return command

    server.add_middleware(
        ThreeRuleMiddleware(
            resolver=resolver,
            policy=ThreeRulePolicy(
                project_boundary=PROJECT_BOUNDARY,
                quarantine_root=QUARANTINE_ROOT,
            ),
            quarantine_paths=lambda _paths: [],
            observability=registry,
        )
    )

    async def run() -> None:
        async with Client(server) as client:
            await client.call_tool(
                "read_file",
                {"path": r"C:\Projects\secret-name.txt"},
            )
            with pytest.raises(Exception, match="HR-002"):
                await client.call_tool(
                    "execute_command",
                    {"command": "curl https://example.com/private-token"},
                )

    asyncio.run(run())
    snapshot = registry.snapshot()

    assert [(item.tool_name, item.argument_keys, item.decision, item.outcome) for item in snapshot.recent_calls] == [
        ("execute_command", ("command",), "block", "rejected"),
        ("read_file", ("path",), "allow", "success"),
    ]
    rendered = str(snapshot.to_dict())
    assert "secret-name" not in rendered
    assert "private-token" not in rendered
    assert "result body" not in rendered


def test_boundary_middleware_records_discover_list_and_call_without_payloads() -> None:
    server = FastMCP("boundary-observability-test")
    registry = RuntimeObservability(max_boundary_requests=10)

    @server.tool
    def echo(secret: str) -> str:
        return secret

    server.add_middleware(BoundaryObservabilityMiddleware(registry))

    async def run() -> None:
        async with Client(server) as client:
            await client.list_tools()
            await client.call_tool("echo", {"secret": "do-not-retain"})

    asyncio.run(run())
    records = registry.snapshot().recent_boundary_requests
    assert any(item.method == "server/discover" for item in records)
    assert any(item.method == "tools/list" for item in records)
    assert any(
        item.method == "tools/call" and item.tool_name == "echo"
        for item in records
    )
    assert "do-not-retain" not in str(registry.snapshot().to_dict())


def test_boundary_middleware_records_failing_tool_without_error_payload() -> None:
    server = FastMCP("boundary-failure-test")
    registry = RuntimeObservability(max_boundary_requests=10)

    @server.tool
    def explode(secret: str) -> str:
        raise RuntimeError(f"sensitive failure: {secret}")

    server.add_middleware(BoundaryObservabilityMiddleware(registry))

    async def run() -> None:
        async with Client(server) as client:
            with pytest.raises(ToolError):
                await client.call_tool("explode", {"secret": "do-not-retain-error"})

    asyncio.run(run())
    record = next(
        item
        for item in registry.snapshot().recent_boundary_requests
        if item.method == "tools/call" and item.tool_name == "explode"
    )
    assert record.outcome == "error"
    assert record.error_type == "RuntimeError"
    assert "do-not-retain-error" not in str(registry.snapshot().to_dict())


def test_boundary_middleware_records_policy_rejection_outside_policy_middleware() -> None:
    server = FastMCP("boundary-policy-rejection-test")
    registry = RuntimeObservability(max_boundary_requests=10)
    resolver = DesktopCommanderEffectResolver(
        project_boundary=PROJECT_BOUNDARY,
        provider_state_file=PROVIDER_STATE,
        observability=registry,
    )

    @server.tool
    def execute_command(command: str) -> str:
        return command

    server.add_middleware(BoundaryObservabilityMiddleware(registry))
    server.add_middleware(
        ThreeRuleMiddleware(
            resolver=resolver,
            policy=ThreeRulePolicy(
                project_boundary=PROJECT_BOUNDARY,
                quarantine_root=QUARANTINE_ROOT,
            ),
            quarantine_paths=lambda _paths: [],
            observability=registry,
        )
    )

    async def run() -> None:
        async with Client(server) as client:
            with pytest.raises(Exception, match="HR-002"):
                await client.call_tool(
                    "execute_command",
                    {"command": "curl https://example.com/private-boundary-token"},
                )

    asyncio.run(run())
    record = next(
        item
        for item in registry.snapshot().recent_boundary_requests
        if item.method == "tools/call" and item.tool_name == "execute_command"
    )
    assert record.outcome == "rejected"
    assert record.error_type == "ToolError"
    assert "private-boundary-token" not in str(registry.snapshot().to_dict())


def test_boundary_middleware_records_malformed_tool_call_as_rejected() -> None:
    server = FastMCP("boundary-malformed-test")
    registry = RuntimeObservability(max_boundary_requests=10)

    @server.tool
    def echo(required_value: str) -> str:
        return required_value

    server.add_middleware(BoundaryObservabilityMiddleware(registry))

    async def run() -> None:
        async with Client(server) as client:
            with pytest.raises(ToolError):
                await client.call_tool("echo", {})

    asyncio.run(run())
    record = next(
        item
        for item in registry.snapshot().recent_boundary_requests
        if item.method == "tools/call" and item.tool_name == "echo"
    )
    assert record.outcome == "rejected"
    assert record.error_type == "ValidationError"


def test_boundary_middleware_records_cancellation_and_restores_context() -> None:
    registry = RuntimeObservability(max_boundary_requests=10)
    middleware = BoundaryObservabilityMiddleware(registry)
    context = SimpleNamespace(
        method="tools/call",
        message=SimpleNamespace(name="slow_tool"),
    )

    async def cancel(_context: object) -> None:
        raise asyncio.CancelledError("do-not-retain-cancellation")

    async def run() -> None:
        with pytest.raises(asyncio.CancelledError):
            await middleware.on_message(context, cancel)

    asyncio.run(run())
    record = registry.snapshot().recent_boundary_requests[0]
    assert record.outcome == "cancelled"
    assert record.error_type == "CancelledError"
    assert record.tool_name == "slow_tool"
    assert "do-not-retain-cancellation" not in str(registry.snapshot().to_dict())
