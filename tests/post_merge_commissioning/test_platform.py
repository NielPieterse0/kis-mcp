from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from kis_mcp.capabilities.contracts import ExposureMode, OperationEffect
from kis_mcp.commissioning_runtime.capability import (
    post_merge_commissioning_capability_contribution,
)
from kis_mcp.commissioning_runtime.platform import register_commissioning_tools


class FakeService:
    def status(self) -> dict[str, object]:
        return {"schema_version": 1, "active": False, "targets": []}

    def receipt(self, receipt_id: str) -> dict[str, object]:
        return {"schema_version": 1, "receipt_id": receipt_id}


def test_read_only_diagnostic_tools_are_registered() -> None:
    server = FastMCP("commissioning-test")
    register_commissioning_tools(server, FakeService())  # type: ignore[arg-type]

    tools = {tool.name for tool in asyncio.run(server.list_tools())}
    assert tools == {
        "kis_post_merge_commissioning_status",
        "kis_post_merge_commissioning_receipt",
    }


    status = asyncio.run(server.call_tool("kis_post_merge_commissioning_status", {}))
    assert status.structured_content == {
        "schema_version": 1,
        "active": False,
        "targets": [],
    }
    receipt = asyncio.run(
        server.call_tool(
            "kis_post_merge_commissioning_receipt",
            {"receipt_id": "post-merge-commissioning:" + "a" * 64},
        )
    )
    assert receipt.structured_content["receipt_id"].startswith(
        "post-merge-commissioning:"
    )


def test_capability_surface_is_discoverable_and_read_only() -> None:
    contribution = post_merge_commissioning_capability_contribution()
    operations = {item.name: item for item in contribution.operations}

    assert contribution.contribution_id == "post-merge-commissioning-runtime"
    assert set(operations) == {
        "kis_post_merge_commissioning_status",
        "kis_post_merge_commissioning_receipt",
    }
    assert all(item.exposure.mode is ExposureMode.DISCOVERABLE for item in operations.values())
    assert all(item.effects == (OperationEffect.READ_ONLY,) for item in operations.values())
