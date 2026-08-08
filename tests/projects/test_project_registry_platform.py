from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import FastMCP

from kis_mcp.projects import load_project_registry_settings
from kis_mcp.projects.platform import project_capability_contribution, register_project_tools


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPOSITORY_ROOT / "settings" / "projects.settings.json"


def test_project_tools_are_bounded_read_only_catalogue_operations() -> None:
    registry = load_project_registry_settings(REGISTRY_PATH, boundary="C:\\Projects")
    server = FastMCP("projects-test")
    register_project_tools(server, registry)

    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {"kis_list_projects", "kis_project_status"}

    listed = asyncio.run(server.call_tool("kis_list_projects", {})).structured_content
    assert listed is not None
    assert listed["default_project_id"] == "kis-mcp"
    assert [item["project_id"] for item in listed["projects"]] == ["gpt-os", "kis-mcp"]

    status = asyncio.run(
        server.call_tool("kis_project_status", {"project_id": "kis-mcp"})
    ).structured_content
    assert status is not None
    assert status["project"]["supabase"]["project_ref"] == "mmxuicfrdalymczdapjq"


def test_project_capability_contribution_is_direct_and_read_only() -> None:
    contribution = project_capability_contribution()

    assert contribution.contribution_id == "projects"
    assert contribution.category == "project-context"
    assert tuple(operation.name for operation in contribution.operations) == (
        "kis_list_projects",
        "kis_project_status",
    )
    assert all(effect.value == "read_only" for effect in contribution.effects)
    assert all(operation.exposure.mode.value == "direct" for operation in contribution.operations)
