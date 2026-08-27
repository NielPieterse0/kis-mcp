from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastmcp import FastMCP
from kis_mcp.capabilities.contracts import ExposureMode, OperationEffect
from kis_mcp.commissioning_runtime.capability import (
    post_merge_commissioning_capability_contribution,
)
from kis_mcp.commissioning_runtime.platform import (
    compose_post_merge_commissioning_runtime,
    register_commissioning_tools,
)


class FakeService:
    def status(self) -> dict[str, object]:
        return {"schema_version": 1, "active": False, "targets": []}

    def receipt(self, receipt_id: str) -> dict[str, object]:
        return {"schema_version": 1, "receipt_id": receipt_id}


class FakeRunner:
    async def run(self, repository: str, commissioning_issue: int, *, execution_owner: str, retry: bool = False) -> dict[str, object]:
        return {"repository": repository, "issue": commissioning_issue, "owner": execution_owner, "retry": retry}

    def execution(self, commissioning_key: str) -> dict[str, object]:
        return {"commissioning_key": commissioning_key, "result": "passed"}


def test_commissioning_tools_are_registered() -> None:
    server = FastMCP("commissioning-test")
    register_commissioning_tools(server, FakeService(), FakeRunner())  # type: ignore[arg-type]

    tools = {tool.name for tool in asyncio.run(server.list_tools())}
    assert tools == {
        "kis_post_merge_commissioning_status",
        "kis_post_merge_commissioning_receipt",
        "kis_post_merge_commissioning_run",
        "kis_post_merge_commissioning_execution",
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


def test_capability_surface_marks_runner_external_and_approval_required() -> None:
    contribution = post_merge_commissioning_capability_contribution()
    operations = {item.name: item for item in contribution.operations}

    assert contribution.contribution_id == "post-merge-commissioning-runtime"
    assert set(operations) == {
        "kis_post_merge_commissioning_status",
        "kis_post_merge_commissioning_receipt",
        "kis_post_merge_commissioning_run",
        "kis_post_merge_commissioning_execution",
    }
    assert all(item.exposure.mode is ExposureMode.DISCOVERABLE for item in operations.values())
    assert operations["kis_post_merge_commissioning_status"].effects == (OperationEffect.READ_ONLY,)
    assert operations["kis_post_merge_commissioning_receipt"].effects == (OperationEffect.READ_ONLY,)
    assert operations["kis_post_merge_commissioning_execution"].effects == (OperationEffect.READ_ONLY,)
    assert operations["kis_post_merge_commissioning_run"].effects == (OperationEffect.EXTERNAL,)
    assert operations["kis_post_merge_commissioning_run"].approval_required is True


def test_commissioning_state_isolated_by_runtime_identity(tmp_path: Path) -> None:
    op = compose_post_merge_commissioning_runtime(
        FastMCP("commissioning-op"),
        SimpleNamespace(state_root=tmp_path),  # type: ignore[arg-type]
        environment={"KIS_MCP_RUNTIME_INSTANCE": "kis-op"},
    )
    dev = compose_post_merge_commissioning_runtime(
        FastMCP("commissioning-dev"),
        SimpleNamespace(state_root=tmp_path),  # type: ignore[arg-type]
        environment={"KIS_MCP_RUNTIME_INSTANCE": "kis-dev"},
    )

    assert op.store.root == (
        tmp_path / "runtime" / "kis-op" / "state" / "post-merge-commissioning"
    )
    assert dev.store.root == (
        tmp_path / "runtime" / "kis-dev" / "state" / "post-merge-commissioning"
    )
    assert op.store.root != dev.store.root


def test_commissioning_legacy_root_is_not_reused(tmp_path: Path) -> None:
    legacy = tmp_path / "post-merge-commissioning" / "legacy.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"legacy":true}', encoding="utf-8")

    service = compose_post_merge_commissioning_runtime(
        FastMCP("commissioning-legacy"),
        SimpleNamespace(state_root=tmp_path),  # type: ignore[arg-type]
        environment={"KIS_MCP_RUNTIME_INSTANCE": "kis-op"},
    )

    assert legacy.exists()
    assert service.store.root != legacy.parent
    assert service.store.root == (
        tmp_path / "runtime" / "kis-op" / "state" / "post-merge-commissioning"
    )
