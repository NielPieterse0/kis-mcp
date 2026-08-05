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


def test_mcp_inspector_installer_is_pinned_staged_and_recoverable() -> None:
    script = INSTALLER.read_text(encoding="utf-8")

    assert "version -ne '2.0.0'" in script
    assert "minimum_node_version" in script
    assert "--save-exact" in script
    assert "--ignore-scripts" in script
    assert "$StagingInstallRoot" in script
    assert "clients\\launcher\\build\\index.js" in script
    assert "& $Node.Source $StagingLauncher --cli --help" in script
    assert "MCP_INSPECTOR_SMOKE_FAILED" in script
    assert "MCP_INSPECTOR_ACTIVATION_FAILED" in script
    assert "failed-new-package" in script
    assert "previous-package" in script
    assert "ReparsePoint" in script
    assert "Move-Item" in script
    assert "Remove-Item" not in script
    assert "@latest" not in script.casefold()
    assert "kis_mcp_exposure.enabled" in script
    assert script.index("& $Npm.Source install") < script.index(
        "Move-Item -LiteralPath $InstallRoot"
    )
    assert script.index("MCP_INSPECTOR_SMOKE_FAILED") < script.index(
        "Move-Item -LiteralPath $InstallRoot"
    )
