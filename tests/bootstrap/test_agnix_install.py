from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / "settings" / "bootstrap" / "agnix.install.json"
SCRIPT = ROOT / "scripts" / "install-agnix.ps1"


def test_agnix_settings_are_independent_and_disabled_by_default() -> None:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))

    assert data["package"] == "agnix"
    assert data["version"] == "0.45.0"
    assert data["install_root"] == r"C:\Projects\.kis-mcp\tools\agnix\0.45.0"
    assert data["expected_commands"] == ["agnix"]
    assert data["kis_mcp_exposure"] == {"enabled": False, "namespace": "agnix"}


def test_agnix_installer_is_pinned_recoverable_and_truthful() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "version -ne '0.45.0'" in script
    assert "--save-exact" in script
    assert "Move-Item" in script
    assert "Remove-Item" not in script
    assert "@latest" not in script.lower()
    assert "mcp_status = 'not_in_npm_distribution'" in script
    assert "agnix.cmd" in script
