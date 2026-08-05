from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastmcp import Client

from kis_mcp.control_center.app import (
    CONTROL_CENTER_RESOURCE_URI,
    build_control_center_server,
)
from kis_mcp.control_center.contracts import ControlCenterSnapshot
from kis_mcp.control_center.settings import ControlCenterSettings


class _SnapshotService:
    def __init__(self, snapshot: ControlCenterSnapshot) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def collect(self) -> ControlCenterSnapshot:
        self.calls += 1
        return self.snapshot


def _settings(tmp_path: Path) -> ControlCenterSettings:
    return ControlCenterSettings(
        schema_version=1,
        project_path=tmp_path,
        runtime_settings_path=tmp_path / "runtime.json",
        policy_path=tmp_path / "policy.json",
        provider_settings_path=tmp_path / "providers.json",
        quarantine_root=tmp_path / "quarantine",
        verification_command=("pwsh", "-File", "scripts/verify.ps1"),
        max_provider_entries=20,
        max_quarantine_records=20,
        git_timeout_seconds=3,
        max_json_bytes=1_000_000,
    )


def test_app_exposes_one_model_entry_tool_and_one_ui_resource(
    tmp_path: Path,
    sample_snapshot: ControlCenterSnapshot,
) -> None:
    service = _SnapshotService(sample_snapshot)
    server = build_control_center_server(
        settings=_settings(tmp_path), snapshot_service=service
    )

    async def run() -> None:
        async with Client(server) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()

        assert [tool.name for tool in tools] == ["open_kis_control_center"]
        assert tools[0].meta is not None
        assert tools[0].meta["ui"]["resourceUri"] == CONTROL_CENTER_RESOURCE_URI
        assert tools[0].meta["ui"]["visibility"] == ["model"]
        assert [str(resource.uri) for resource in resources] == [
            CONTROL_CENTER_RESOURCE_URI
        ]
        assert resources[0].mimeType == "text/html;profile=mcp-app"

    asyncio.run(run())


def test_app_returns_structured_fallback_and_fresh_html_resource(
    tmp_path: Path,
    sample_snapshot: ControlCenterSnapshot,
) -> None:
    service = _SnapshotService(sample_snapshot)
    server = build_control_center_server(
        settings=_settings(tmp_path), snapshot_service=service
    )

    async def run() -> tuple[Any, list[Any]]:
        async with Client(server) as client:
            result = await client.call_tool("open_kis_control_center", {})
            resource = await client.read_resource(CONTROL_CENTER_RESOURCE_URI)
        return result, resource

    result, resource = asyncio.run(run())

    assert result.structured_content["schema_version"] == 1
    assert result.structured_content["project"]["git"]["branch"].startswith("main")
    assert len(resource) == 1
    assert resource[0].mimeType == "text/html;profile=mcp-app"
    assert "KIS Control Center" in resource[0].text
    assert service.calls == 2
