from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP

from kis_mcp.config import load_runtime_config
from kis_mcp.workflows.state_management import register_state_management_tools
from kis_mcp.workflows.state_management import tools as state_tools

ROOT = Path(__file__).resolve().parents[3]


def test_state_management_tools_expose_bounded_read_and_recoverable_cleanup() -> None:
    server = FastMCP("root")
    register_state_management_tools(server, load_runtime_config(ROOT))
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}

    assert "state_ownership_inventory" in tools
    assert "state_stale_cleanup" in tools
    inventory = tools["state_ownership_inventory"].annotations
    cleanup = tools["state_stale_cleanup"].annotations
    assert inventory is not None and inventory.read_only_hint is True
    assert cleanup is not None and cleanup.read_only_hint is False
    assert cleanup.destructive_hint is False
    assert cleanup.open_world_hint is False


def test_state_cleanup_forwards_preview_token(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        def cleanup(self, relative_path: str, **kwargs: object) -> dict[str, object]:
            captured["relative_path"] = relative_path
            captured.update(kwargs)
            return {"schema_version": 1, "mode": "apply", "action": "quarantined"}

    monkeypatch.setattr(state_tools, "build_state_diagnostics_service", lambda runtime: FakeService())
    server = FastMCP("root")
    register_state_management_tools(server, load_runtime_config(ROOT))

    async def run() -> None:
        async with Client(server) as client:
            await client.call_tool(
                "state_stale_cleanup",
                {
                    "relative_path": "projects\\retired\\sources\\old\\reconstructible\\cache",
                    "apply": True,
                    "idempotency_key": "cleanup-1",
                    "preview_token": "preview-1",
                },
            )

    asyncio.run(run())
    assert captured["preview_token"] == "preview-1"


def test_state_management_client_preserves_inventory_and_cleanup_contracts(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class Inventory:
        def to_json_dict(self) -> dict[str, object]:
            return {
                "schema_version": 1,
                "entries": [{
                    "relative_path": "projects\\kis-mcp\\sources\\old\\reconstructible\\cache",
                    "ownership_class": "reconstructible-cache",
                    "state_key": "cache",
                    "identities": {"project_id": "kis-mcp", "source_id": "old"},
                    "authoritative": False,
                    "reconstructible": True,
                    "stale": True,
                    "stale_reason": "source_not_current",
                    "safe_to_cleanup": True,
                    "provenance": "canonical-state-contract",
                    "age_seconds": 42,
                    "generation": None,
                }],
                "unclassified_roots": ["legacy"],
                "truncated": True,
            }

    class FakeService:
        def inventory(self, *, limit: int = 200):
            calls.append(("inventory", limit))
            return Inventory()

        def cleanup(self, relative_path: str, **kwargs: object) -> dict[str, object]:
            calls.append((relative_path, dict(kwargs)))
            mode = "apply" if kwargs.get("apply") else "preview"
            return {
                "schema_version": 1,
                "mode": mode,
                "action": "quarantined" if mode == "apply" else "would_quarantine",
                "quarantine_operation_id": "op-1" if mode == "apply" else None,
                "preview_token": "preview-1" if mode == "preview" else None,
            }

    monkeypatch.setattr(state_tools, "build_state_diagnostics_service", lambda runtime: FakeService())
    server = FastMCP("root")
    register_state_management_tools(server, load_runtime_config(ROOT))

    async def run() -> None:
        async with Client(server) as client:
            inventory = await client.call_tool("state_ownership_inventory", {"limit": 17})
            assert inventory.data["truncated"] is True
            assert inventory.data["unclassified_roots"] == ["legacy"]
            assert len(inventory.data["entries"]) == 1
            entry = inventory.data["entries"][0]
            assert entry["ownership_class"] == "reconstructible-cache"
            assert entry["relative_path"].endswith("reconstructible\\cache")
            assert entry["authoritative"] is False
            assert entry["stale"] is True
            assert entry["stale_reason"] == "source_not_current"
            assert entry["safe_to_cleanup"] is True
            assert entry["generation"] is None
            preview = await client.call_tool("state_stale_cleanup", {"relative_path": "state", "apply": False})
            assert preview.data["mode"] == "preview"
            assert preview.data["preview_token"] == "preview-1"
            applied = await client.call_tool(
                "state_stale_cleanup",
                {
                    "relative_path": "state",
                    "apply": True,
                    "idempotency_key": "cleanup-22",
                    "preview_token": "preview-1",
                },
            )
            assert applied.data["mode"] == "apply"
            assert applied.data["quarantine_operation_id"] == "op-1"
            assert applied.data["idempotency_key"] == "cleanup-22"

    asyncio.run(run())
    assert calls[0] == ("inventory", 17)
    assert calls[1][1]["apply"] is False
    assert calls[2][1]["idempotency_key"] == "cleanup-22"


def test_state_management_client_surfaces_bounded_tool_errors(monkeypatch) -> None:
    class FakeService:
        def inventory(self, *, limit: int = 200):
            raise ValueError("limit rejected")

        def cleanup(self, relative_path: str, **kwargs: object) -> dict[str, object]:
            raise ValueError("preview_token is required")

    monkeypatch.setattr(state_tools, "build_state_diagnostics_service", lambda runtime: FakeService())
    server = FastMCP("root")
    register_state_management_tools(server, load_runtime_config(ROOT))

    async def run() -> None:
        async with Client(server) as client:
            with pytest.raises(Exception, match="STATE_OWNERSHIP_INVENTORY_FAILED"):
                await client.call_tool("state_ownership_inventory", {"limit": 0})
            with pytest.raises(Exception, match="STATE_STALE_CLEANUP_FAILED"):
                await client.call_tool(
                    "state_stale_cleanup",
                    {"relative_path": "state", "apply": True, "idempotency_key": "cleanup-error"},
                )
            with pytest.raises(Exception, match="idempotency_key is required"):
                await client.call_tool("state_stale_cleanup", {"relative_path": "state", "apply": True})

    asyncio.run(run())
