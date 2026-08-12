from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ...config import RuntimeConfig
from ...discover.change_service import InspectChangeService
from ...discover.git_reader import GitReader
from ...discover.intelligence import ProjectIntelligenceService
from ...discover.read_authority import ReadAuthority
from ...discover.service import InspectProjectService
from ...projects.settings import load_project_registry_settings
from ..change_execution import (
    ChangeExecutionInvocationError,
    ChangeExecutionService,
    register_change_execution_tool,
)
from ..completion import (
    CompletionCoordinator,
    CompletionInvocationError,
    register_completion_tool,
)
from .execution import VerificationExecutionService
from .selection import VerificationSelectionService
from .tools import register_verification_selection_tool, register_verification_tool


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
    boundary = Path(runtime.project_boundary)
    projects = load_project_registry_settings(boundary=runtime.project_boundary)
    intelligence = ProjectIntelligenceService(
        boundary=boundary,
        settings=runtime.discover_settings,
    )
    inspector = InspectProjectService(
        boundary=boundary,
        settings=runtime.discover_settings,
        intelligence_service=intelligence,
    )
    analyzer = InspectChangeService(
        GitReader(
            authority=ReadAuthority(boundary, runtime.discover_settings),
            settings=runtime.discover_settings,
        ),
        intelligence_service=intelligence,
    )

    async def runner(tool_name: str, arguments: dict[str, Any]) -> Any:
        return await _run_with_middleware(server, tool_name, arguments)

    async def structured_invoker(
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            result = await _run_with_middleware(server, tool_name, arguments)
        except ToolError as exc:
            code, reason = _nested_error(exc)
            raise ChangeExecutionInvocationError(code, reason) from exc
        return _structured_payload(result)

    async def completion_invoker(
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            result = await _run_with_middleware(server, tool_name, arguments)
        except ToolError as exc:
            code, reason = _nested_error(exc)
            raise CompletionInvocationError(code, reason) from exc
        payload = getattr(result, "structured_content", None)
        if isinstance(payload, Mapping):
            return dict(payload)
        if isinstance(result, Mapping):
            return dict(result)
        raise CompletionInvocationError(
            "COMPLETION_NESTED_RESULT_INVALID",
            "Nested completion operation returned no structured object result.",
        )

    register_verification_selection_tool(
        server,
        VerificationSelectionService(analyzer=analyzer, inspector=inspector),
    )
    register_verification_tool(
        server,
        VerificationExecutionService(inspector=inspector, runner=runner),
    )
    register_change_execution_tool(
        server,
        ChangeExecutionService(structured_invoker),
    )
    register_completion_tool(
        server,
        CompletionCoordinator(
            completion_invoker,
            lambda project_id: projects.project(project_id).local_root,
        ),
    )


def _structured_payload(result: Any) -> dict[str, Any]:
    payload = getattr(result, "structured_content", None)
    if isinstance(payload, Mapping):
        return dict(payload)
    if isinstance(result, Mapping):
        return dict(result)
    raise ChangeExecutionInvocationError(
        "CHANGE_EXECUTION_NESTED_RESULT_INVALID",
        "Nested workflow operation returned no structured object result.",
    )


def _nested_error(exc: ToolError) -> tuple[str, str]:
    reason = str(exc)
    try:
        payload = json.loads(reason)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, Mapping) and isinstance(payload.get("code"), str):
        return str(payload["code"]), reason
    prefix = reason.split(":", 1)[0].strip()
    if prefix and prefix.replace("_", "").isalnum() and prefix.upper() == prefix:
        return prefix, reason
    return "CHANGE_EXECUTION_STEP_FAILED", reason


def _result_text(result: Any) -> str:
    return "\n".join(
        text
        for block in getattr(result, "content", ())
        if isinstance((text := getattr(block, "text", None)), str)
    ).strip()


__all__ = ["register_platform_verification"]
