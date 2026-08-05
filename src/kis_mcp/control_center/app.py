from __future__ import annotations

from typing import Protocol

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP, UI_MIME_TYPE

from .contracts import ControlCenterSnapshot
from .render import render_control_center
from .settings import ControlCenterSettings, load_control_center_settings
from .snapshot import ControlCenterSnapshotService

CONTROL_CENTER_RESOURCE_URI = "ui://kis-mcp/control-center.html"


class SnapshotService(Protocol):
    def collect(self) -> ControlCenterSnapshot: ...


def build_control_center_server(
    settings: ControlCenterSettings | None = None,
    *,
    snapshot_service: SnapshotService | None = None,
) -> FastMCP:
    """Build the standalone read-only KIS Control Center MCP App server."""

    resolved_settings = settings or load_control_center_settings()
    service = snapshot_service or ControlCenterSnapshotService(resolved_settings)
    server = FastMCP(
        "kis-mcp-control-center",
        instructions=(
            "Open a read-only local operational dashboard. Use the ordinary kis-mcp "
            "gateway for any filesystem, provider, verification, or quarantine action."
        ),
    )
    resource_app = AppConfig(
        csp=ResourceCSP(
            connect_domains=[],
            resource_domains=[],
            frame_domains=[],
            base_uri_domains=[],
        ),
        prefers_border=True,
    )

    @server.resource(
        CONTROL_CENTER_RESOURCE_URI,
        name="KIS Control Center",
        description="Self-contained read-only KIS operational status dashboard.",
        mime_type=UI_MIME_TYPE,
        app=resource_app,
    )
    def control_center_resource() -> str:
        return render_control_center(service.collect())

    @server.tool(
        name="open_kis_control_center",
        title="Open KIS Control Center",
        description=(
            "Open the read-only KIS Control Center and return the same current local "
            "status as structured fallback content."
        ),
        app=AppConfig(
            resource_uri=CONTROL_CENTER_RESOURCE_URI,
            visibility=["model"],
            prefers_border=True,
        ),
    )
    def open_kis_control_center() -> dict[str, object]:
        return service.collect().to_dict()

    return server


def main() -> None:
    build_control_center_server().run(transport="stdio")


__all__ = [
    "CONTROL_CENTER_RESOURCE_URI",
    "SnapshotService",
    "build_control_center_server",
    "main",
]
