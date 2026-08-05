from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / "settings" / "bootstrap" / "agentsys.install.json"
SCRIPT = ROOT / "scripts" / "install-agentsys.ps1"


def test_agentsys_settings_are_exact_and_default_deny() -> None:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))

    assert data["package"] == "agentsys"
    assert data["version"] == "6.0.1"
    assert data["hosts"] == ["claude", "opencode", "codex"]
    assert data["install_root"] == r"C:\Projects\.kis-mcp\tools\agentsys\6.0.1"
    assert data["managed_home"] == r"C:\Projects\.kis-mcp\agent-hosts\agentsys"
    policy = data["kis_mcp_command_policy"]
    assert policy["default_enabled"] is False
    assert policy["enabled_commands"] == []
    assert len(policy["available_commands"]) == 25
    assert {"next-task", "repo-intel", "ship"} <= set(policy["available_commands"])
    assert "agnix" not in policy["available_commands"]


def test_agentsys_installer_is_complete_but_bounded() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "@latest" not in script.lower()
    assert 'version -ne \'6.0.1\'' in script
    assert "--save-exact" in script
    assert "--tools opencode,codex" in script
    assert "'.claude\\plugins'" in script
    assert "$env:XDG_CONFIG_HOME" in script
    assert "$env:CODEX_HOME" in script
    assert "$env:CLAUDE_CONFIG_DIR" in script
    assert "$StagingInstallRoot" in script
    assert "$StagingManagedHome" in script
    assert "ReparsePoint" in script
    assert "AGENTSYS_PATH_REPARSE_POINT" in script
    assert "AGENTSYS_PROFILE_RELOCATION_FAILED" in script
    assert "AGENTSYS_COMMAND_CATALOGUE_MISMATCH" in script
    assert "AGENTSYS_ACTIVATION_FAILED" in script
    assert "failed-new-package" in script
    assert "Move-Item" in script
    assert "Copy-Item" in script
    assert "Remove-Item" not in script
    assert "rmSync" not in script
    assert script.index("& $Npm.Source install") < script.index("Move-Item -LiteralPath $InstallRoot")
    assert script.index("AGENTSYS_COMMAND_CATALOGUE_MISMATCH") < script.index(
        "Move-Item -LiteralPath $InstallRoot"
    )
