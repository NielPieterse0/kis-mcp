from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from kis_mcp.govern.contracts import GovernanceEvidence
from kis_mcp.govern.service import GovernanceService
from kis_mcp.govern.settings import GovernanceSettings
from kis_mcp.govern.tools import register_governance_tools


class _Collector:
    def collect(self, project: str) -> GovernanceEvidence:
        return GovernanceEvidence(project=project, agents_text="", documents=())


def _service() -> GovernanceService:
    return GovernanceService(
        GovernanceSettings(
            enabled=True,
            max_authority_documents=10,
            max_file_bytes=10000,
            max_findings=10,
            min_duplicate_paragraph_chars=80,
            enabled_rules=("authority-order",),
        )
    )


def test_governance_surface_is_read_only_and_advisory() -> None:
    server = FastMCP("govern-test")
    register_governance_tools(server, service=_service(), collector=_Collector())
    tools = {item.name: item for item in asyncio.run(server.list_tools())}

    assert set(tools) == {
        "list_governance_capabilities",
        "inspect_repository_governance",
        "evaluate_governance_rules",
        "describe_governance_finding",
    }
    for tool in tools.values():
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.open_world_hint is False

    result = asyncio.run(tools["inspect_repository_governance"].run({"project": "demo"}))
    inspection = result.structured_content
    assert inspection is not None
    assert inspection["policy_effect"] == "advisory_only"
    assert inspection["findings"][0]["owning_plane"] == "govern"
