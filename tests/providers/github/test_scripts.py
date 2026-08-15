from __future__ import annotations

from pathlib import Path


INSTALL = Path("scripts/install-github-mcp.ps1")
AUTH = Path("scripts/auth-github-mcp.ps1")
SMOKE = Path("scripts/smoke-github-mcp.ps1")
LIVE_SMOKE = Path("scripts/run-provider-live-smoke.py")


def test_install_script_downloads_only_the_pinned_immutable_release() -> None:
    source = INSTALL.read_text(encoding="utf-8")

    assert "Set-StrictMode -Version Latest" in source
    assert "github-mcp.provider.json" in source
    assert "api.github.com/repos/github/github-mcp-server/releases/tags" in source
    assert "api.github.com/repos/github/github-mcp-server/git/ref/tags" in source
    assert "immutable" in source
    assert "source_revision" in source
    assert "browser_download_url" in source
    assert "digest" in source
    assert "sha256:" in source
    assert "Invoke-WebRequest" in source
    assert "Get-FileHash" in source
    assert "Expand-Archive" in source
    assert "github-mcp-server.exe" in source
    assert r"C:\Projects\.kis-mcp\github-mcp" in source
    assert "backup.exe" in source
    assert "Remove-Item" not in source


def test_auth_script_starts_kis_op_without_printing_or_forwarding_pat() -> None:
    source = AUTH.read_text(encoding="utf-8")

    assert "Set-StrictMode -Version Latest" in source
    assert "github-mcp.provider.json" in source
    assert "projects.settings.json" in source
    assert "kis-repository.settings.json" not in source
    assert "pat_env" in source
    assert "GITHUB_OAUTH_PAT_CONFLICT" in source
    assert "start-chatgpt.ps1" in source
    assert "-Instance operation" in source
    assert "owned by the kis-op runtime" in source
    assert "Stopping or restarting kis-op requires one new" in source
    assert "kis_mcp.providers.github.commission" not in source
    assert "Write-Output $env:GITHUB_PERSONAL_ACCESS_TOKEN" not in source
    assert "GITHUB_PERSONAL_ACCESS_TOKEN=" not in source


def test_smoke_script_supports_offline_tests_and_explicit_shared_runtime_live_check() -> None:
    source = SMOKE.read_text(encoding="utf-8")

    assert "Set-StrictMode -Version Latest" in source
    assert "RequireLive" in source
    assert "auth_mode" in source
    assert "pat_env" in source
    assert "GITHUB_OAUTH_PAT_CONFLICT" in source
    assert "tests/providers/github" in source
    assert "tests/providers/test_client_runtime.py" in source
    assert "tests/providers/test_platform_composition.py" in source
    assert "tests/repositories" in source
    assert "projects.settings.json" in source
    assert "kis-repository.settings.json" not in source
    assert "scripts/run-provider-live-smoke.py github" in source
    assert "client_lifetime" in source
    assert "authentication_bootstrap" in source
    assert "live_mounted" in source
    assert "live_repository_scope" in source
    assert "Write-Output $env:GITHUB_PERSONAL_ACCESS_TOKEN" not in source
    assert "--help" not in source


def test_shared_live_smoke_keeps_github_dispatch() -> None:
    source = LIVE_SMOKE.read_text(encoding="utf-8")

    assert "_github_shared_runtime_smoke" in source
    assert '"github": _github_shared_runtime_smoke' in source
    assert '"search_capabilities"' in source
    assert '"execute_external_action"' in source
    assert 'parser.add_argument("provider", nargs="?"' in source
