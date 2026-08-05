from __future__ import annotations

import json
from typing import Any, Protocol

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .change_analysis import (
    AnalyzeChangeRequest,
    AnalyzeChangeResponse,
    GitHubChangeContext,
    SuppliedChange,
)
from .change_inspection_contracts import InspectChangeRequest, InspectChangeResponse
from .impact_contracts import ImpactBudget
from .context_contracts import (
    CodeContextBudget,
    GetCodeContextRequest,
    GetCodeContextResponse,
)
from .contracts import InspectProjectRequest, InspectProjectResponse
from .errors import DiscoverError


_READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


class InspectProjectPort(Protocol):
    def inspect(self, request: InspectProjectRequest) -> InspectProjectResponse: ...

    def get_code_context(
        self,
        request: GetCodeContextRequest,
    ) -> GetCodeContextResponse: ...


class InspectChangePort(Protocol):
    def inspect(self, request: InspectChangeRequest) -> InspectChangeResponse: ...


class AnalyzeChangePort(Protocol):
    def analyze(self, request: AnalyzeChangeRequest) -> AnalyzeChangeResponse: ...


def register_discover_tools(server: FastMCP, service: InspectProjectPort) -> None:
    """Register the bounded read-only Discover project and context surface."""

    @server.tool(
        name="inspect_project",
        annotations=_READ_ONLY_ANNOTATIONS,
    )
    def inspect_project(
        path: str,
        limits: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Inspect one local project using bounded deterministic evidence discovery."""

        try:
            request = InspectProjectRequest(path=path, limits=limits)
            return service.inspect(request).to_json_dict()
        except DiscoverError as exc:
            raise _discover_tool_error(exc) from exc
        except ValueError as exc:
            raise _request_tool_error(
                code="DISCOVER_PROJECT_REQUEST_INVALID",
                message="The inspect_project request is invalid.",
                reason=str(exc),
                field="request",
                corrective_actions=(
                    r"Provide a non-empty local project path beneath C:\Projects.",
                    "Use only supported positive limit fields.",
                ),
            )

    @server.tool(
        name="get_code_context",
        annotations=_READ_ONLY_ANNOTATIONS,
    )
    def get_code_context(
        project: str,
        task: str,
        max_chars: int,
        max_files: int,
        max_symbols: int,
        max_relationships: int,
    ) -> dict[str, Any]:
        """Assemble the smallest bounded local code context for one explicit task."""

        try:
            request = GetCodeContextRequest(
                project=project,
                task=task,
                budget=CodeContextBudget(
                    max_chars=max_chars,
                    max_files=max_files,
                    max_symbols=max_symbols,
                    max_relationships=max_relationships,
                ),
            )
            return service.get_code_context(request).to_json_dict()
        except DiscoverError as exc:
            raise _discover_tool_error(exc) from exc
        except ValueError as exc:
            raise _request_tool_error(
                code="DISCOVER_CONTEXT_REQUEST_INVALID",
                message="The get_code_context request is invalid.",
                reason=str(exc),
                field="request",
                corrective_actions=(
                    r"Provide a non-empty local project path beneath C:\Projects.",
                    "Provide a non-empty task and positive explicit budget values.",
                ),
            )


def register_change_tools(server: FastMCP, service: InspectChangePort) -> None:
    """Register the bounded read-only change inspection surface."""

    @server.tool(
        name="inspect_change",
        annotations=_READ_ONLY_ANNOTATIONS,
    )
    def inspect_change(
        path: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
    ) -> dict[str, Any]:
        """Inspect a bounded working tree, staged set, commit, range, or branch target."""

        try:
            request = InspectChangeRequest(
                path=path,
                source=source,
                commit_ref=commit_ref,
                base_ref=base_ref,
                head_ref=head_ref,
            )
            return service.inspect(request).to_json_dict()
        except DiscoverError as exc:
            raise _discover_tool_error(exc) from exc
        except ValueError as exc:
            raise _request_tool_error(
                code="DISCOVER_CHANGE_REQUEST_INVALID",
                message="The inspect_change request is invalid.",
                reason=str(exc),
                field=_change_request_field(str(exc)),
                corrective_actions=(
                    r"Provide a non-empty local project path beneath C:\Projects.",
                    "Use a supported source with the required safe Git refs.",
                ),
            )

    if callable(getattr(service, "analyze", None)):
        register_analyze_change_tool(server, service)  # type: ignore[arg-type]


def register_analyze_change_tool(server: FastMCP, service: AnalyzeChangePort) -> None:
    """Register the unified bounded local change-analysis workflow."""

    @server.tool(name="analyze_change", annotations=_READ_ONLY_ANNOTATIONS)
    def analyze_change(
        project: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        task_terms: list[str] | None = None,
        supplied_changes: list[dict[str, Any]] | None = None,
        github_context: dict[str, Any] | None = None,
        max_symbols: int = 100,
        max_dependants: int = 100,
        max_tests: int = 100,
        max_verifications: int = 50,
    ) -> dict[str, Any]:
        """Normalize one local or supplied change and return evidence-backed impact guidance."""

        try:
            supplied = tuple(SuppliedChange(**item) for item in (supplied_changes or ()))
            github = None
            if github_context is not None:
                payload = dict(github_context)
                payload["changes"] = tuple(
                    SuppliedChange(**item) for item in payload.get("changes", ())
                )
                github = GitHubChangeContext(**payload)
            request = AnalyzeChangeRequest(
                project=project,
                source=source,
                commit_ref=commit_ref,
                base_ref=base_ref,
                head_ref=head_ref,
                task_terms=tuple(task_terms or ()),
                supplied_changes=supplied,
                github_context=github,
                budget=ImpactBudget(
                    max_symbols=max_symbols,
                    max_dependants=max_dependants,
                    max_tests=max_tests,
                    max_verifications=max_verifications,
                ),
            )
            return service.analyze(request).to_json_dict()
        except DiscoverError as exc:
            raise _discover_tool_error(exc) from exc
        except (TypeError, ValueError) as exc:
            raise _request_tool_error(
                code="DISCOVER_ANALYZE_CHANGE_REQUEST_INVALID",
                message="The analyze_change request is invalid.",
                reason=str(exc),
                field="request",
                corrective_actions=(
                    r"Provide a local project beneath C:\Projects and a supported change source.",
                    "Use safe local Git refs or bounded supplied/GitHub metadata with positive budgets.",
                ),
            )


def _discover_tool_error(exc: DiscoverError) -> ToolError:
    return ToolError(
        json.dumps(
            exc.to_json_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def _request_tool_error(
    *,
    code: str,
    message: str,
    reason: str,
    field: str,
    corrective_actions: tuple[str, ...],
) -> ToolError:
    payload = {
        "code": code,
        "message": message,
        "reason": reason,
        "field": field,
        "corrective_actions": list(corrective_actions),
        "retryable": False,
    }
    return ToolError(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _change_request_field(reason: str) -> str:
    normalized = reason.casefold()
    if "path" in normalized:
        return "path"
    if "source is unsupported" in normalized:
        return "source"
    if "requires" in normalized or "accepts only" in normalized or "does not accept" in normalized:
        return "request"
    for field in ("commit_ref", "base_ref", "head_ref"):
        if field in normalized:
            return field
    return "request"


__all__ = [
    "AnalyzeChangePort",
    "InspectChangePort",
    "InspectProjectPort",
    "register_analyze_change_tool",
    "register_change_tools",
    "register_discover_tools",
]
