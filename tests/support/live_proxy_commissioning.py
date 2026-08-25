from __future__ import annotations

import asyncio
import json
import os
import string
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

STATE_ROOT = Path(r"C:\Projects\.kis-mcp")


def choose_unmounted_drive(
    *,
    exists: Callable[[str], bool] = os.path.exists,
) -> str:
    for letter in reversed(string.ascii_uppercase[3:]):
        root = f"{letter}:\\"
        if not exists(root):
            return root
    raise RuntimeError("No unmounted drive letter is available for the HR-001 probe")


def build_gateway_environment(
    repository_root: Path,
    *,
    base_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    environment = dict(os.environ if base_environment is None else base_environment)
    environment.update(
        {
            "UV_PROJECT_ENVIRONMENT": str(STATE_ROOT / "python-env"),
            "UV_CACHE_DIR": str(STATE_ROOT / "uv-cache"),
            "PYTHONPYCACHEPREFIX": str(STATE_ROOT / "python-cache"),
            "TEMP": str(STATE_ROOT / "temp"),
            "TMP": str(STATE_ROOT / "temp"),
            "PYTHONPATH": str(repository_root / "src"),
            "NO_UPDATE_NOTIFIER": "1",
        }
    )
    return environment


def result_text(result: Any) -> str:
    return "\n".join(
        text
        for block in getattr(result, "content", [])
        if isinstance((text := getattr(block, "text", None)), str)
    )


def validate_provider_state_bytes(content: bytes) -> None:
    try:
        state = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssertionError(
            "PROVIDER_STATE_INTEGRITY: Desktop Commander config.json is not valid JSON"
        ) from exc

    if not isinstance(state, dict):
        raise AssertionError(
            "PROVIDER_STATE_INTEGRITY: Desktop Commander config.json must contain an object"
        )
    if state.get("blockedCommands") != []:
        raise AssertionError(
            "PROVIDER_STATE_INTEGRITY: blockedCommands must remain empty"
        )
    if state.get("allowedDirectories") != []:
        raise AssertionError(
            "PROVIDER_STATE_INTEGRITY: allowedDirectories must remain empty"
        )
    telemetry = state.get("telemetryEnabled")
    if telemetry is not False and str(telemetry).strip().casefold() != "false":
        raise AssertionError(
            "PROVIDER_STATE_INTEGRITY: telemetryEnabled must remain false"
        )


def _result_mapping(result: Any) -> dict[str, Any]:
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data

    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        if isinstance(structured.get("result"), dict):
            return dict(structured["result"])
        return dict(structured)

    text = result_text(result).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Expected a mapping result, received: {text}") from exc
    if not isinstance(parsed, dict):
        raise AssertionError(f"Expected a mapping result, received: {parsed!r}")
    return parsed


def _restore_provider_state(
    state_path: Path,
    snapshot: bytes,
    *,
    run_id: str,
) -> None:
    restore_path = state_path.with_name(f"config.restore-{run_id}.tmp")
    restore_path.write_bytes(snapshot)
    os.replace(restore_path, state_path)


async def _run_live_commissioning(repository_root: Path) -> dict[str, bool]:
    run_id = uuid4().hex
    commissioning_root = STATE_ROOT / "temp" / "commissioning" / run_id
    log_path = STATE_ROOT / "logs" / f"live-proxy-commissioning-{run_id}.log"
    python_executable = STATE_ROOT / "python-env" / "Scripts" / "python.exe"
    provider_state_path = STATE_ROOT / ".claude-server-commander" / "config.json"

    if not python_executable.is_file():
        raise AssertionError(f"Locked Python interpreter is missing: {python_executable}")

    try:
        provider_state_snapshot = provider_state_path.read_bytes()
    except OSError as exc:
        raise AssertionError(
            f"PROVIDER_STATE_INTEGRITY: cannot read {provider_state_path}"
        ) from exc
    validate_provider_state_bytes(provider_state_snapshot)

    commissioning_root.mkdir(parents=True, exist_ok=False)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    read_target = commissioning_root / "read-target.txt"
    write_target = commissioning_root / "write-target.txt"
    quarantine_target = commissioning_root / "quarantine-target.txt"
    read_target.write_text("kis-mcp-live-read", encoding="utf-8")
    quarantine_target.write_text("kis-mcp-live-quarantine", encoding="utf-8")

    environment = build_gateway_environment(repository_root)
    transport = StdioTransport(
        command=str(python_executable),
        args=["-m", "kis_mcp"],
        cwd=str(repository_root),
        env=environment,
        keep_alive=False,
        log_file=log_path,
    )
    report = {
        "health": False,
        "surface": False,
        "read": False,
        "write": False,
        "hr001": False,
        "quarantine": False,
        "restore": False,
        "process": False,
        "provider_state": False,
    }

    try:
        async with Client(transport, timeout=60, init_timeout=60) as client:
            health_result = await client.call_tool("kis_health", {})
            health = _result_mapping(health_result)
            assert health.get("ready") is True, health
            assert health.get("desktop_commander_installed") is True, health
            report["health"] = True

            tools = await client.list_tools()
            tools_by_name = {tool.name: tool for tool in tools}
            required = {
                "kis_health",
                "kis_quarantine_path",
                "kis_restore_quarantine",
                "read_file",
                "write_file",
                "start_process",
            }
            assert required <= set(tools_by_name), sorted(tools_by_name)
            assert "give_feedback_to_desktop_commander" not in tools_by_name
            direct_delete_tools = {
                "delete_file",
                "delete_directory",
                "remove_file",
                "remove_directory",
            }
            assert direct_delete_tools.isdisjoint(tools_by_name)
            read_properties = tools_by_name["read_file"].input_schema.get(
                "properties", {}
            )
            assert "isUrl" not in read_properties
            report["surface"] = True

            read_result = await client.call_tool("read_file", {"path": str(read_target)})
            assert "kis-mcp-live-read" in result_text(read_result)
            report["read"] = True

            write_result = await client.call_tool(
                "write_file",
                {"path": str(write_target), "content": "kis-mcp-live-write"},
            )
            assert not getattr(write_result, "is_error", False), result_text(write_result)
            assert write_target.read_text(encoding="utf-8") == "kis-mcp-live-write"
            report["write"] = True

            outside_target = f"{choose_unmounted_drive()}kis-mcp-live-block.txt"
            try:
                blocked_result = await client.call_tool(
                    "write_file",
                    {"path": outside_target, "content": "must-not-forward"},
                )
            except Exception as exc:
                block_text = str(exc)
            else:
                block_text = result_text(blocked_result)
                assert getattr(blocked_result, "is_error", False), block_text
            assert "HR-001_WRITE_OUTSIDE_PROJECTS" in block_text, block_text
            report["hr001"] = True

            quarantine_result = await client.call_tool(
                "kis_quarantine_path",
                {"path": str(quarantine_target)},
            )
            quarantine_record = _result_mapping(quarantine_result)
            operation_id = str(quarantine_record["operation_id"])
            assert not quarantine_target.exists()
            report["quarantine"] = True

            restore_result = await client.call_tool(
                "kis_restore_quarantine",
                {"operation_id": operation_id},
            )
            assert not getattr(restore_result, "is_error", False), result_text(
                restore_result
            )
            assert (
                quarantine_target.read_text(encoding="utf-8")
                == "kis-mcp-live-quarantine"
            )
            report["restore"] = True

            process_result = await client.call_tool(
                "start_process",
                {"command": "echo kis-mcp-live-process", "timeout_ms": 5000},
            )
            process_text = result_text(process_result)
            assert not getattr(process_result, "is_error", False), process_text
            assert "kis-mcp-live-process" in process_text, process_text
            report["process"] = True

            cleanup_result = await client.call_tool(
                "kis_quarantine_path",
                {"path": str(commissioning_root)},
            )
            assert not getattr(cleanup_result, "is_error", False), result_text(
                cleanup_result
            )
    finally:
        try:
            current_provider_state = provider_state_path.read_bytes()
            validate_provider_state_bytes(current_provider_state)
        except (OSError, AssertionError) as integrity_error:
            try:
                _restore_provider_state(
                    provider_state_path,
                    provider_state_snapshot,
                    run_id=run_id,
                )
                validate_provider_state_bytes(provider_state_path.read_bytes())
            except (OSError, AssertionError) as restore_error:
                raise AssertionError(
                    "PROVIDER_STATE_INTEGRITY: live commissioning corrupted "
                    f"{provider_state_path}; automatic restoration also failed: "
                    f"{restore_error}"
                ) from integrity_error
            raise AssertionError(
                "PROVIDER_STATE_INTEGRITY: live commissioning corrupted "
                f"{provider_state_path}; the pre-run snapshot was restored"
            ) from integrity_error

    report["provider_state"] = True
    return report


def run_live_commissioning(repository_root: Path) -> dict[str, bool]:
    return asyncio.run(_run_live_commissioning(repository_root.resolve()))
