from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts" / "start-agentsys-host.ps1"


def test_launcher_supports_exact_managed_hosts() -> None:
    script = LAUNCHER.read_text(encoding="utf-8")

    assert "[ValidateSet('claude', 'opencode', 'codex')]" in script
    assert "$env:HOME = $ManagedHome" in script
    assert "$env:USERPROFILE = $ManagedHome" in script
    assert "$env:XDG_CONFIG_HOME" in script
    assert "$env:OPENCODE_CONFIG_DIR" in script
    assert "$env:CODEX_HOME" in script
    assert "$env:CLAUDE_CONFIG_DIR" in script
    assert "settings\\bootstrap\\agnix.install.json" in script
    assert "node_modules\\.bin" in script
    assert "$env:PATH" in script
    assert "ReparsePoint" in script
    assert "AGENTSYS_MANAGED_PATH_REPARSE_POINT" in script
    assert "AGENTSYS_HOST_COMMAND_UNAVAILABLE" in script
    assert "Remove-Item" not in script
