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


def test_mcp_inspector_launcher_targets_only_configured_local_instances() -> None:
    script = LAUNCHER.read_text(encoding="utf-8")

    assert "ValidateSet('operation', 'development')" in script
    assert "settings\\kis-mcp.settings.json" in script
    assert "remote_mcp.instances" in script
    assert "MCP_INSPECTOR_INSTANCE_NOT_CONFIGURED" in script
    assert "MCP_INSPECTOR_HOST_INVALID" in script
    assert "$env:HOST = '127.0.0.1'" in script
    assert "$env:CLIENT_PORT" in script
    assert "$env:MCP_STORAGE_DIR" in script
    assert "$env:MCP_LOG_FILE" in script
    assert "$env:MCP_AUTO_OPEN_ENABLED" in script
    assert "--server-url" in script
    assert "--transport" in script
    assert "'http'" in script
    assert "& $Node.Source $LauncherPath --web" in script
    assert "npm install" not in script.casefold()
    assert "Remove-Item" not in script
    assert "Start-Process" not in script
