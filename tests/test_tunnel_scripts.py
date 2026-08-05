from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY_ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def test_tunnel_configuration_uses_canonical_secret_references() -> None:
    settings = json.loads(
        (REPOSITORY_ROOT / "settings" / "kis-mcp.settings.json").read_text(
            encoding="utf-8"
        )
    )
    remote = settings["remote_mcp"]

    assert remote["tunnel_client_path"] == (
        r"C:\Tools\openai-tunnel-client\tunnel-client.exe"
    )
    assert set(remote["instances"]) == {"operation", "development"}
    expected_tunnel_ids = {
        "operation": "tunnel_6a6806687cf88191bf97c8c3cb0d1f61",
        "development": "tunnel_6a68065a7b688191ba706b86151241ff",
    }
    for name, instance in remote["instances"].items():
        assert instance["configured"] is True
        assert instance["tunnel_id"] == expected_tunnel_ids[name]
        assert instance["tunnel_secret_ref"] == (
            f"secret://tunnel/{name}/authentication-token"
        )
        assert "tunnel_credential_target" not in instance
        assert "tunnel_authentication_id" not in instance


def test_tunnel_state_helper_reads_non_secret_identifiers_and_reference() -> None:
    content = _script("tunnel-state.ps1")

    assert "settings\\kis-mcp.settings.json" in content
    assert "Get-KisMcpRemoteInstance" in content
    assert "operation" in content and "development" in content
    assert "RequireConfigured" in content
    assert "tunnel_secret_ref" in content
    assert "secret://" in content
    assert "tunnel_credential_target" not in content
    assert "tunnel_authentication_id" not in content
    assert "tunnel_client_path" in content


def test_legacy_windows_credential_helper_is_not_used_by_runtime_scripts() -> None:
    for name in (
        "set-tunnel-credential.ps1",
        "setup-tunnel.ps1",
        "start-chatgpt.ps1",
        "start.ps1",
        "tunnel-state.ps1",
    ):
        content = _script(name)
        assert "windows-credential.ps1" not in content
        assert "Set-KisMcpWindowsCredential" not in content
        assert "Get-KisMcpWindowsCredential" not in content
        assert "tunnel_credential_target" not in content


def test_set_credential_script_writes_vault_reference_through_secure_boundary() -> None:
    content = _script("set-tunnel-credential.ps1")

    assert "secret-vault.ps1" in content
    assert "Read-Host" in content
    assert "-AsSecureString" in content
    assert "Invoke-KisMcpSecretCommand" in content
    assert "@('set', '--reference', $Remote.tunnel_secret_ref)" in content
    assert "$Payload['value']" in content
    assert "--secret" not in content
    assert "--passphrase" not in content


def test_setup_script_resolves_vault_secret_without_persisting_plaintext() -> None:
    content = _script("setup-tunnel.ps1")

    assert "Get-KisMcpRemoteInstance" in content
    assert "Resolve-KisMcpSecretInternal" in content
    assert "Get-KisMcpUnlockPayload" in content
    assert "--profile-dir" in content
    assert "--tunnel-id" in content
    assert "--mcp-server-url" in content
    assert "--control-plane-api-key-ref" in content
    assert '"env:$CredentialEnvironmentName"' in content
    assert "$env:$CredentialEnvironmentName" not in content
    assert "[Environment]::SetEnvironmentVariable" in content
    assert "finally" in content
    assert "$Remote.tunnel_secret_ref" in content
    assert "tunnel_credential_target" not in content
    assert "tunnel_authentication_id" not in content
    assert "BackupExistingProfile" in content
    assert "doctor" in content
    assert "--explain" in content
    assert "sk-" not in content


def test_chatgpt_launcher_unlocks_once_for_server_and_tunnel() -> None:
    content = _script("start-chatgpt.ps1")

    assert "ValidateSet('operation', 'development')" in content
    assert "kis_mcp.secrets.launcher" in content
    assert "--runtime" in content and "remote" in content
    assert "--mcp.server-url" in content
    assert "--health.url-file" in content
    assert "readyz" in content
    assert "Kill()" in content
    assert "Resolve-KisMcpSecretInternal" in content
    assert "$Remote.tunnel_secret_ref" in content
    assert "$VaultUnlockPayload" in content
    assert "Start-KisMcpSecretAwareProcess" in content
    assert "$TunnelEnvironment" in content
    assert "tunnel_credential_target" not in content
    assert "tunnel_authentication_id" not in content
    assert "KIS_MCP_OTHER_INSTANCE_ACTIVE" in content


def test_smoke_script_checks_full_representative_tool_surface() -> None:
    content = _script("smoke-chatgpt.ps1")

    assert "initialize" in content
    assert "tools/list" in content
    assert "tools/call" in content
    for tool_name in (
        "kis_health",
        "inspect_project",
        "read_file",
        "write_file",
        "edit_block",
        "start_process",
    ):
        assert tool_name in content
    assert "give_feedback_to_desktop_commander" in content
    assert "KIS_MCP_SMOKE_NETWORK_ONLY_TOOL_EXPOSED" in content
    assert "KIS_MCP_SMOKE_DISCOVER_CALL_FAILED" in content
    assert "PSObject.Properties['error']" in content
    assert "kis_quarantine_path" in content
    assert "KIS_MCP_SMOKE_WRITE_CALL_FAILED" in content
    assert "KIS_MCP_SMOKE_READ_CALL_FAILED" in content
    assert "KIS_MCP_SMOKE_QUARANTINE_CALL_FAILED" in content
    assert "KIS_MCP_SMOKE_CLEANUP_QUARANTINE_FAILED" in content
