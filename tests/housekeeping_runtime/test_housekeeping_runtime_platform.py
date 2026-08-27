from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastmcp import FastMCP
from kis_mcp.housekeeping_runtime.platform import (
    compose_housekeeping_runtime,
    register_housekeeping_tools,
)


class FakeService:
    def status(self) -> dict[str, object]:
        return {"schema_version": 1, "active": True, "targets": []}

    def receipt(self, receipt_id: str) -> dict[str, object]:
        return {"schema_version": 1, "receipt_id": receipt_id}

    async def apply_receipt(self, receipt_id: str) -> dict[str, object]:
        return {
            "complete": True,
            "receipt_id": receipt_id,
            "idempotency_key": "housekeeping:test:key",
        }


def test_housekeeping_status_and_apply_tools_are_registered() -> None:
    server = FastMCP("housekeeping-test")
    register_housekeeping_tools(server, FakeService())  # type: ignore[arg-type]

    tools = {tool.name for tool in asyncio.run(server.list_tools())}
    assert {
        "kis_housekeeping_status",
        "kis_housekeeping_receipt",
        "kis_housekeeping_apply_receipt",
    }.issubset(tools)

    status = asyncio.run(server.call_tool("kis_housekeeping_status", {}))
    assert status.structured_content == {
        "schema_version": 1,
        "active": True,
        "targets": [],
    }

    receipt = asyncio.run(
        server.call_tool("kis_housekeeping_receipt", {"receipt_id": "x:y"})
    )
    assert receipt.structured_content["receipt_id"] == "x:y"

    applied = asyncio.run(
        server.call_tool("kis_housekeeping_apply_receipt", {"receipt_id": "x:y"})
    )
    assert applied.structured_content["complete"] is True
    assert applied.structured_content["idempotency_key"] == "housekeeping:test:key"


def test_housekeeping_state_isolated_by_runtime_identity(tmp_path: Path) -> None:
    op = compose_housekeeping_runtime(
        FastMCP("housekeeping-op"),
        SimpleNamespace(state_root=tmp_path),  # type: ignore[arg-type]
        environment={"KIS_MCP_RUNTIME_INSTANCE": "kis-op"},
    )
    dev = compose_housekeeping_runtime(
        FastMCP("housekeeping-dev"),
        SimpleNamespace(state_root=tmp_path),  # type: ignore[arg-type]
        environment={"KIS_MCP_RUNTIME_INSTANCE": "kis-dev"},
    )

    assert op.store.root == tmp_path / "runtime" / "kis-op" / "state" / "housekeeping"
    assert dev.store.root == tmp_path / "runtime" / "kis-dev" / "state" / "housekeeping"
    assert op.store.root != dev.store.root


def test_housekeeping_legacy_root_is_not_reused(tmp_path: Path) -> None:
    legacy = tmp_path / "housekeeping" / "legacy.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"legacy":true}', encoding="utf-8")

    service = compose_housekeeping_runtime(
        FastMCP("housekeeping-legacy"),
        SimpleNamespace(state_root=tmp_path),  # type: ignore[arg-type]
        environment={"KIS_MCP_RUNTIME_INSTANCE": "kis-op"},
    )

    assert legacy.exists()
    assert service.store.root != legacy.parent
    assert service.store.root == tmp_path / "runtime" / "kis-op" / "state" / "housekeeping"
