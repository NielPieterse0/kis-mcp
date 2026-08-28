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
    assert data["source"] == {
        "repository": "agent-sh/agnix",
        "release_tag": "v0.45.0",
        "asset": "agnix-x86_64-unknown-linux-gnu.tar.gz",
        "checksum_asset": "agnix-x86_64-unknown-linux-gnu.tar.gz.sha256",
    }
    assert data["expected_commands"] == ["agnix"]
    assert data["kis_mcp_exposure"] == {"enabled": False, "namespace": "agnix"}
    assert data["validation"]["runtime_kind"] == "wsl"
    assert data["validation"]["wsl_distribution"] == "Ubuntu"
    assert data["validation"]["binary_relative_path"] == r"bin\agnix"
    assert data["validation"]["targets"] == ["generic", "claude-code", "cursor", "codex", "kiro"]
    assert data["validation"]["max_files"] == 10000


def test_agnix_installer_is_pinned_recoverable_and_truthful() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "version -ne '0.45.0'" in script
    assert "$StagingInstallRoot" in script
    assert "ReparsePoint" in script
    assert "AGNIX_PATH_REPARSE_POINT" in script
    assert "AGNIX_ACTIVATION_FAILED" in script
    assert "failed-new-package" in script
    assert "Invoke-WebRequest" in script
    assert "Get-FileHash" in script
    assert "AGNIX_CHECKSUM_MISMATCH" in script
    assert "asset -ne 'agnix-x86_64-unknown-linux-gnu.tar.gz'" in script
    assert "checksum_asset -ne 'agnix-x86_64-unknown-linux-gnu.tar.gz.sha256'" in script
    assert "failed-stage" in script
    assert "AGNIX_FAILED_STAGE_QUARANTINE_FAILED" in script
    assert "IsNullOrWhiteSpace([string]$StagingInstallRoot)" in script
    assert "wsl.exe" in script
    assert "--distribution" in script
    assert "--exec" in script
    assert "Move-Item" in script
    assert "Remove-Item" not in script
    assert "@latest" not in script.lower()
    assert "npm" not in script.lower()
    assert "node.exe" not in script.lower()
    assert "source_url" in script
    assert "asset_sha256" in script
    assert script.index("AGNIX_SMOKE_FAILED") < script.index("Move-Item -LiteralPath $InstallRoot")
