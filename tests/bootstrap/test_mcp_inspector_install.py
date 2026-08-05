from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / "settings" / "bootstrap" / "mcp-inspector.install.json"
INSTALLER = ROOT / "scripts" / "install-mcp-inspector.ps1"
LAUNCHER = ROOT / "scripts" / "start-mcp-inspector.ps1"


def test_mcp_inspector_settings_pin_v2_and_managed_paths() -> None:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))

    assert data["schema_version"] == 1
    assert data["tool_id"] == "mcp-inspector"
    assert data["package"] == "@modelcontextprotocol/inspector"
    assert data["version"] == "2.0.0"
    assert data["minimum_node_version"] == "22.19.0"
    assert data["install_root"] == r"C:\Projects\.kis-mcp\tools\mcp-inspector\2.0.0"
    assert data["launcher_entry_point"].endswith(
        r"clients\launcher\build\index.js"
    )
    assert data["web_ports"] == {"operation": 6274, "development": 6275}
    assert data["kis_mcp_exposure"] == {
        "enabled": False,
        "namespace": "mcp-inspector",
    }

    for field in (
        "install_root",
        "managed_home",
        "npm_cache_root",
        "temp_root",
        "log_root",
        "quarantine_root",
    ):
        assert data[field].casefold().startswith("c:\\projects\\")
