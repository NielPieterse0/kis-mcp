from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY_ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def test_tunnel_setup_separates_profile_creation_from_live_validation() -> None:
    content = _script("setup-tunnel.ps1")

    assert "[switch]$ValidateLiveEndpoint" in content
    assert "if ($ValidateLiveEndpoint)" in content
    assert "KIS_MCP_ENDPOINT_NOT_READY" in content
    assert "KIS_MCP_TUNNEL_PROFILE_INVALID" in content
    assert content.index("if ($ValidateLiveEndpoint)") < content.index(" doctor `")
    assert "profile created for instance" in content
    assert "profile created and validated" not in content


def test_tunnel_setup_validates_credential_before_moving_active_profile() -> None:
    content = _script("setup-tunnel.ps1")

    profile_exists_guard = content.index(
        "if ($ProfileExists -and -not $BackupExistingProfile)"
    )
    credential_read = content.index("$Credential = Get-KisMcpWindowsCredential")
    profile_backup = content.index("[System.IO.File]::Move($ProfilePath, $BackupPath)")

    assert profile_exists_guard < credential_read < profile_backup


def test_chatgpt_startup_orders_server_readiness_before_tunnel() -> None:
    content = _script("start-chatgpt.ps1")

    server_start = content.index("$Server = Start-OwnedProcess")
    server_ready = content.index("Wait-McpReady -Uri")
    tunnel_start = content.index("$Tunnel = Start-OwnedProcess")

    assert server_start < server_ready < tunnel_start
    assert "KIS_MCP_ENDPOINT_NOT_READY" in content
    assert "KIS_MCP_HTTP_NOT_READY" not in content


def test_chatgpt_startup_supports_bounded_observation_cleanup() -> None:
    content = _script("start-chatgpt.ps1")

    assert "[int]$ObservationSeconds = 0" in content
    assert "KIS_MCP_OBSERVATION_SECONDS_INVALID" in content
    assert "if ($ObservationSeconds -gt 0)" in content
    assert "Start-Sleep -Seconds $ObservationSeconds" in content
    assert content.index("Start-Sleep -Seconds $ObservationSeconds") < content.rindex("finally {")


def test_tunnel_setup_captures_provider_cli_output() -> None:
    content = _script("setup-tunnel.ps1")

    assert "setup-$RunId.log" in content
    assert "$InitOutput = & $Remote.tunnel_client_path init" in content
    assert "$DoctorOutput = & $Remote.tunnel_client_path doctor" in content
    assert "2>&1" in content
    assert "[System.IO.File]::AppendAllLines" in content
    assert "setup_log=" in content


def test_chatgpt_startup_redirects_owned_process_output() -> None:
    content = _script("start-chatgpt.ps1")

    assert "RedirectStandardOutput = $true" in content
    assert "RedirectStandardError = $true" in content
    assert "ReadToEndAsync()" in content
    assert "Write-OwnedProcessLogs" in content
    assert "server-stdout-$RunId.log" in content
    assert "server-stderr-$RunId.log" in content
    assert "tunnel-stdout-$RunId.log" in content
    assert "tunnel-stderr-$RunId.log" in content
    assert "logs = [ordered]@{" in content


def test_chatgpt_startup_emits_only_gateway_owned_readiness_fields() -> None:
    content = _script("start-chatgpt.ps1")

    for field in (
        "health=ready",
        "endpoint=",
        "policy_fingerprint=",
        "tunnel_state=ready",
        "tunnel_profile=",
        "tunnel_id=",
        "startup_state=",
    ):
        assert field in content
    assert "Tunnel authentication ID:" not in content
    assert "Keep this window open" not in content
    assert "ConvertTo-Json" in content
    assert "startup-state-$RunId.json" in content
