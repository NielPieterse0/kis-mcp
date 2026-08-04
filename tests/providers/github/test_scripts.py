from __future__ import annotations

from pathlib import Path


INSTALL = Path("scripts/install-github-mcp.ps1")
SMOKE = Path("scripts/smoke-github-mcp.ps1")


def test_install_script_is_hash_verified_and_never_downloads() -> None:
    source = INSTALL.read_text(encoding="utf-8")

    assert "Set-StrictMode -Version Latest" in source
    assert "SourceBinary" in source
    assert "ExpectedSha256" in source
    assert "Get-FileHash" in source
    assert r"C:\Projects\.kis-mcp\github-mcp" in source
    assert "Invoke-WebRequest" not in source
    assert "curl" not in source.casefold()
    assert "wget" not in source.casefold()


def test_smoke_script_never_prints_token_and_supports_conditional_live_check() -> None:
    source = SMOKE.read_text(encoding="utf-8")

    assert "Set-StrictMode -Version Latest" in source
    assert "RequireLive" in source
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in source
    assert "Write-Output $env:GITHUB_PERSONAL_ACCESS_TOKEN" not in source
    assert "scripts\\verify.ps1" not in source
    assert "tests/providers/github" in source
    assert "kis_mcp.providers.github.smoke" in source
    assert "--help" not in source
