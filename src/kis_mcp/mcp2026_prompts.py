from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.transforms import Transform

_AUTHORITY = (
    "Work Management remains authoritative. Treat this MCP prompt as a user-invoked "
    "entry point only; use KIS operations and durable change state for every decision "
    "or mutation. Do not infer authority from this prompt."
)


class DeterministicDiscoveryTransform(Transform):
    """Keep MCP list identities stable without promising stale-safe positive caching."""

    async def list_tools(self, tools: Sequence[Any]) -> Sequence[Any]:
        return sorted(tools, key=lambda item: (str(item.name), str(item.version or "")))

    async def list_prompts(self, prompts: Sequence[Any]) -> Sequence[Any]:
        return sorted(prompts, key=lambda item: (str(item.name), str(item.version or "")))

    async def list_resources(self, resources: Sequence[Any]) -> Sequence[Any]:
        return sorted(resources, key=lambda item: str(item.uri))

    async def list_resource_templates(self, templates: Sequence[Any]) -> Sequence[Any]:
        return sorted(templates, key=lambda item: str(item.uri_template))


def register_mcp2026_workflow_prompts(server: FastMCP) -> None:
    """Register thin MCP workflow entry prompts without adding workflow authority."""

    @server.prompt(name="start-change", description="Start one governed KIS change.")
    def start_change(project_id: str, repository: str, issue_number: int) -> str:
        return (
            f"{_AUTHORITY}\n"
            f"Start issue #{issue_number} in project {project_id} ({repository}). "
            "Read live Work state, establish the execution claim, then use the repository's "
            "governed change workflow. Refuse to create a parallel workflow or authority."
        )

    @server.prompt(name="resume-change", description="Resume one governed KIS change.")
    def resume_change(project_id: str, change_id: str) -> str:
        return (
            f"{_AUTHORITY}\nResume change {change_id} in project {project_id}. "
            "Read the existing claim, scope, lifecycle evidence, and current worktree; continue "
            "only the next governed action and do not create a replacement change."
        )

    @server.prompt(name="take-next-work", description="Claim the next deterministic Ready item.")
    def take_next_work(project_id: str, execution_owner: str) -> str:
        return (
            f"{_AUTHORITY}\nFor project {project_id}, use project_management_take_next_work "
            f"for execution owner {execution_owner}. Accept only the returned Ready item and "
            "its established claim; do not substitute manual ranking or an unclaimed issue."
        )

    @server.prompt(name="explain-change", description="Explain current governed change state.")
    def explain_change(project_id: str, change_id: str) -> str:
        return (
            f"{_AUTHORITY}\nExplain change {change_id} in project {project_id} from its current "
            "scope, Work record, bounded change inspection, verification/review evidence, and "
            "lifecycle decision. This prompt is read-only and must not advance lifecycle state."
        )


__all__ = ["DeterministicDiscoveryTransform", "register_mcp2026_workflow_prompts"]
