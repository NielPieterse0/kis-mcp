from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY_ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def _run_tunnel_state(expression: str) -> subprocess.CompletedProcess[str]:
    script_path = (SCRIPTS / "tunnel-state.ps1").as_posix()
    return subprocess.run(
        ["pwsh", "-NoProfile", "-Command", f". '{script_path}'; {expression}"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_windows_credential(expression: str) -> subprocess.CompletedProcess[str]:
    script_path = (SCRIPTS / "windows-credential.ps1").as_posix()
    return subprocess.run(
        ["pwsh", "-NoProfile", "-Command", f". '{script_path}'; {expression}"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


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
    expected_app_names = {
        "operation": "kis-op",
        "development": "kis-dev",
    }
    expected_ports = {
        "operation": 8010,
        "development": 8011,
    }
    for name, instance in remote["instances"].items():
        assert instance["configured"] is True
        assert instance["app_name"] == expected_app_names[name]
        assert instance["port"] == expected_ports[name]
        assert instance["tunnel_id"] == expected_tunnel_ids[name]
        assert instance["tunnel_secret_ref"] == (
            f"secret://tunnel/{name}/authentication-token"
        )
        assert "tunnel_credential_target" not in instance
        assert "tunnel_authentication_id" not in instance


def test_windows_credential_target_is_derived_from_canonical_reference() -> None:
    valid = _run_windows_credential(
        "Write-Output (Get-KisMcpTunnelCredentialTarget "
        "-Reference 'secret://tunnel/development/authentication-token')"
    )
    invalid = _run_windows_credential(
        "Get-KisMcpTunnelCredentialTarget -Reference 'secret://providers/example/key'"
    )

    assert valid.returncode == 0, valid.stderr
    assert valid.stdout.strip() == "kis-mcp/tunnel/development"
    assert invalid.returncode != 0
    assert "KIS_MCP_TUNNEL_SECRET_REFERENCE_INVALID" in invalid.stderr


@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        ("kis-op", "operation"),
        ("op", "operation"),
        ("operation", "operation"),
        ("kis-dev", "development"),
        ("dev", "development"),
        ("development", "development"),
    ],
)
def test_tunnel_state_resolves_app_and_instance_aliases(
    selector: str,
    expected: str,
) -> None:
    result = _run_tunnel_state(
        f"Write-Output (Resolve-KisMcpInstanceName -Instance '{selector}')"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (
            "$Settings.remote_mcp.instances.operation.app_name = 'kis-dev'",
            "KIS_MCP_APP_IDENTITY_INVALID",
        ),
        (
            "$Settings.remote_mcp.instances.operation.port = 8012",
            "KIS_MCP_INSTANCE_PORT_INVALID",
        ),
        (
            "$Settings.remote_mcp.instances.development.port = 8010",
            "KIS_MCP_INSTANCE_PORT_DUPLICATE",
        ),
    ],
)
def test_tunnel_state_rejects_invalid_app_port_mappings(
    mutation: str,
    expected_error: str,
) -> None:
    settings_path = (
        REPOSITORY_ROOT / "settings" / "kis-mcp.settings.json"
    ).as_posix()
    result = _run_tunnel_state(
        "$Settings = Get-Content -LiteralPath "
        f"'{settings_path}' -Raw | ConvertFrom-Json; "
        f"{mutation}; "
        "Assert-KisMcpRemoteConfiguration -Remote $Settings.remote_mcp"
    )

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert expected_error in combined


def test_tunnel_state_helper_reads_non_secret_identifiers_and_reference() -> None:
    content = _script("tunnel-state.ps1")

    assert "settings\\kis-mcp.settings.json" in content
    assert "Resolve-KisMcpInstanceName" in content
    assert "Assert-KisMcpRemoteConfiguration" in content
    assert "Get-KisMcpRemoteInstance" in content
    assert "operation" in content and "development" in content
    assert "kis-op" in content and "kis-dev" in content
    assert "RequireConfigured" in content
    assert "app_name" in content
    assert "tunnel_secret_ref" in content
    assert "secret://" in content
    assert "tunnel_credential_target" not in content
    assert "tunnel_authentication_id" not in content
    assert "tunnel_client_path" in content


def test_runtime_startup_does_not_unlock_application_vault() -> None:
    chatgpt = _script("start-chatgpt.ps1")
    stdio = _script("start.ps1")

    for content in (chatgpt, stdio):
        assert "secret-vault.ps1" not in content
        assert "Get-KisMcpUnlockPayload" not in content
        assert "kis_mcp.secrets.launcher" not in content
        assert "Start-KisMcpSecretAwareProcess" not in content
        assert "Unlock kis-mcp secrets" not in content
    assert "kis_mcp.remote_runtime" in chatgpt
    assert "kis_mcp.server" in stdio


def test_set_credential_script_stores_windows_credential_once() -> None:
    content = _script("set-tunnel-credential.ps1")

    assert "windows-credential.ps1" in content
    assert "Get-KisMcpTunnelCredentialTarget" in content
    assert "Read-Host" in content
    assert "-AsSecureString" in content
    assert "Set-KisMcpWindowsCredential" in content
    assert "$Remote.tunnel_secret_ref" in content
    assert "secret-vault.ps1" not in content
    assert "Invoke-KisMcpSecretCommand" not in content


def test_setup_script_reads_windows_credential_without_persisting_plaintext() -> None:
    content = _script("setup-tunnel.ps1")

    assert "windows-credential.ps1" in content
    assert "Get-KisMcpRemoteInstance" in content
    assert "Get-KisMcpTunnelCredentialTarget" in content
    assert "Get-KisMcpWindowsCredential" in content
    assert "Get-KisMcpUnlockPayload" not in content
    assert "Resolve-KisMcpSecretInternal" not in content
    assert "--profile-dir" in content
    assert "--tunnel-id" in content
    assert "--mcp-server-url" in content
    assert "--control-plane-api-key-ref" in content
    assert '"env:$CredentialEnvironmentName"' in content
    assert "$env:$CredentialEnvironmentName" not in content
    assert "[Environment]::SetEnvironmentVariable" in content
    assert "finally" in content
    assert "$Remote.tunnel_secret_ref" in content
    assert "BackupExistingProfile" in content
    assert "doctor" in content
    assert "--explain" in content
    assert "sk-" not in content


def test_chatgpt_launcher_uses_windows_credential_only_for_tunnel() -> None:
    content = _script("start-chatgpt.ps1")

    assert "windows-credential.ps1" in content
    assert "kis_mcp.remote_runtime" in content
    assert "--mcp.server-url" in content
    assert "--health.url-file" in content
    assert "readyz" in content
    assert "$Tunnel.Kill($true)" in content
    assert "$Server.Kill($true)" in content
    assert "Kill()" not in content
    assert "Get-KisMcpTunnelCredentialTarget" in content
    assert "Get-KisMcpWindowsCredential" in content
    assert "$TunnelEnvironment" in content
    assert "Get-KisMcpUnlockPayload" not in content
    assert "kis_mcp.secrets.launcher" not in content
    assert "KIS_MCP_OTHER_INSTANCE_ACTIVE" not in content


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
