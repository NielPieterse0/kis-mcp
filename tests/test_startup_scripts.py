from __future__ import annotations

import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY_ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def _document(name: str) -> str:
    return (REPOSITORY_ROOT / name).read_text(encoding="utf-8")


def _run_startup_lifecycle(expression: str) -> subprocess.CompletedProcess[str]:
    script_path = (SCRIPTS / "startup-instance-lifecycle.ps1").as_posix()
    return subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-Command",
            f"$ErrorActionPreference='Stop'; . '{script_path}'; {expression}",
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_startup_lifecycle_atomic_json_replaces_existing_file(tmp_path: Path) -> None:
    state_path = (tmp_path / "current.json").as_posix().replace("'", "''")
    result = _run_startup_lifecycle(
        "$path='"
        + state_path
        + "'; "
        "Write-KisMcpAtomicJson -Path $path -Document ([ordered]@{value=1}); "
        "Write-KisMcpAtomicJson -Path $path -Document ([ordered]@{value=2}); "
        "$document=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json; "
        "Write-Output $document.value"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "2"


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
    credential_read = content.index("$Credential = Resolve-KisMcpSecretInternal")
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


def test_chatgpt_startup_finishes_non_secret_preflight_before_unlock() -> None:
    content = _script("start-chatgpt.ps1")

    preflight = content.index("$Preflight = Invoke-KisMcpSelectedInstancePreflight")
    unlock_payload = content.index("$VaultUnlockPayload = Get-KisMcpUnlockPayload")
    server_start = content.index("$Server = Start-OwnedProcess")

    assert preflight < unlock_payload < server_start


def test_chatgpt_startup_allows_peer_instance_to_remain_active() -> None:
    content = _script("start-chatgpt.ps1")

    assert "$OtherInstance" not in content
    assert "$OtherRemote" not in content
    assert "$OtherListener" not in content
    assert "KIS_MCP_OTHER_INSTANCE_ACTIVE" not in content
    assert content.count("-LocalPort $Remote.port") == 1


def test_chatgpt_startup_hardens_the_selected_app_port() -> None:
    content = _script("start-chatgpt.ps1")

    assert "$Remote.app_name" in content
    assert "Invoke-KisMcpSelectedInstancePreflight" in content
    assert "Assert-KisMcpSelectedEndpointOwner" in content
    assert "KIS_MCP_PORT_OWNED_BY_OTHER_PROCESS" in _script(
        "startup-instance-lifecycle.ps1"
    )
    assert "-LocalAddress $Remote.host" in content
    assert "-LocalPort $Remote.port" in content


def test_startup_lifecycle_matches_only_selected_server_instance() -> None:
    python = r"C:\Projects\.kis-mcp\python-env\Scripts\python.exe"
    operation = (
        f'\"{python}\" -m kis_mcp.secrets.launcher '
        "--runtime remote --instance operation"
    )
    result = _run_startup_lifecycle(
        "$p=[pscustomobject]@{ExecutablePath='"
        + python.replace("\\", "\\")
        + "';CommandLine='"
        + operation.replace("'", "''")
        + "'}; "
        "Write-Output (Test-KisMcpSelectedServerProcess -Process $p "
        "-PythonPath '"
        + python
        + "' -Instance 'operation'); "
        "Write-Output (Test-KisMcpSelectedServerProcess -Process $p "
        "-PythonPath '"
        + python
        + "' -Instance 'development')"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["True", "False"]


def test_startup_lifecycle_empty_process_set_has_no_roots() -> None:
    result = _run_startup_lifecycle(
        "Write-Output (@(Get-KisMcpRootProcessIds -Processes @()).Count)"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0"


def test_startup_lifecycle_root_selection_does_not_promote_children() -> None:
    result = _run_startup_lifecycle(
        "$p=@([pscustomobject]@{ProcessId=10;ParentProcessId=1},"
        "[pscustomobject]@{ProcessId=11;ParentProcessId=10},"
        "[pscustomobject]@{ProcessId=20;ParentProcessId=2}); "
        "Write-Output ((@(Get-KisMcpRootProcessIds -Processes $p) | Sort-Object) -join ',')"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "10,20"


def test_startup_lifecycle_matches_only_selected_tunnel_instance() -> None:
    tunnel = r"C:\Tools\openai-tunnel-client\tunnel-client.exe"
    command = (
        f'\"{tunnel}\" run --profile kis-mcp-operation '
        "--profile-dir C:\\Projects\\.kis-mcp\\tunnel-client\\profiles "
        "--mcp.server-url http://127.0.0.1:8010/mcp"
    )
    result = _run_startup_lifecycle(
        "$p=[pscustomobject]@{ExecutablePath='"
        + tunnel
        + "';CommandLine='"
        + command.replace("'", "''")
        + "'}; "
        "Write-Output (Test-KisMcpSelectedTunnelProcess -Process $p "
        "-TunnelPath '"
        + tunnel
        + "' -ProfileName 'kis-mcp-operation' "
        "-Endpoint 'http://127.0.0.1:8010/mcp'); "
        "Write-Output (Test-KisMcpSelectedTunnelProcess -Process $p "
        "-TunnelPath '"
        + tunnel
        + "' -ProfileName 'kis-mcp-development' "
        "-Endpoint 'http://127.0.0.1:8011/mcp')"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["True", "False"]


def test_chatgpt_startup_uses_authoritative_per_instance_current_state() -> None:
    content = _script("start-chatgpt.ps1")
    lifecycle = _script("startup-instance-lifecycle.ps1")

    assert "current.json" in lifecycle
    assert "Write-KisMcpCurrentInstanceState" in content
    assert "Set-KisMcpCurrentInstanceStopped" in content
    assert "server_listener_pid" in content
    assert content.index("Assert-KisMcpSelectedEndpointOwner") < content.index(
        "Write-KisMcpCurrentInstanceState"
    )


def test_selected_preflight_invalidates_previous_ready_state_before_reclaim() -> None:
    lifecycle = _script("startup-instance-lifecycle.ps1")

    marker = "Set-KisMcpCurrentInstanceRestarting -Remote $Remote"
    assert marker in lifecycle
    assert lifecycle.index(marker) < lifecycle.index("$Processes = Get-KisMcpProcessSnapshot")
    assert "lifecycle = 'restarting'" in lifecycle


def test_chatgpt_startup_records_failure_after_successful_preflight() -> None:
    content = _script("start-chatgpt.ps1")
    lifecycle = _script("startup-instance-lifecycle.ps1")

    assert "$VaultUnlockPayload = $null" in content
    assert "$CurrentStatePath = $null\ntry {\n    $VaultUnlockPayload = Get-KisMcpUnlockPayload" in content
    assert "Set-KisMcpCurrentInstanceStartupFailed -Remote $Remote -RunId $RunId" in content
    assert "if ($null -ne $VaultUnlockPayload)" in content
    assert "lifecycle = 'startup_failed'" in lifecycle


def test_chatgpt_startup_quarantines_noncanonical_repository_transients() -> None:
    content = _script("start-chatgpt.ps1")
    lifecycle = _script("startup-instance-lifecycle.ps1")

    assert "Invoke-KisMcpSelectedInstancePreflight" in content
    assert "Move-KisMcpRepositoryTransientsToQuarantine" in lifecycle
    assert "-Remote $Remote" in lifecycle
    assert "'.venv'" in lifecycle
    assert "'.pytest_cache'" in lifecycle
    assert "Move-Item" in lifecycle
    assert "quarantine" in lifecycle
    assert "Remove-Item" not in lifecycle


def test_tunnel_setup_finishes_non_secret_preflight_before_unlock() -> None:
    content = _script("setup-tunnel.ps1")

    profile_guard = content.index("if ($ProfileExists -and -not $BackupExistingProfile)")
    unlock_payload = content.index("$VaultUnlockPayload = Get-KisMcpUnlockPayload")
    credential_read = content.index("$Credential = Resolve-KisMcpSecretInternal")

    assert profile_guard < unlock_payload < credential_read


def test_chatgpt_startup_supports_bounded_observation_cleanup() -> None:
    content = _script("start-chatgpt.ps1")

    assert "[int]$ObservationSeconds = 0" in content
    assert "KIS_MCP_OBSERVATION_SECONDS_INVALID" in content
    assert "if ($ObservationSeconds -gt 0)" in content
    assert "Start-Sleep -Seconds $ObservationSeconds" in content
    assert content.index("Start-Sleep -Seconds $ObservationSeconds") < content.rindex("finally {")


def test_chatgpt_shutdown_terminates_owned_process_trees() -> None:
    content = _script("start-chatgpt.ps1")

    assert "$Tunnel.Kill($true)" in content
    assert "$Server.Kill($true)" in content
    assert "$Tunnel.Kill()" not in content
    assert "$Server.Kill()" not in content


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
        "app=",
        "instance=",
        "endpoint=",
        "policy_fingerprint=",
        "tunnel_state=ready",
        "tunnel_profile=",
        "tunnel_id=",
        "startup_state=",
    ):
        assert field in content
    assert "app = $Remote.app_name" in content
    assert "instance = $Remote.name" in content
    assert "Tunnel authentication ID:" not in content
    assert "Keep this window open" not in content
    assert "ConvertTo-Json" in content
    assert "startup-state-$RunId.json" in content


def test_operations_documents_one_launcher_for_kis_op_and_kis_dev() -> None:
    content = _document("docs/OPERATIONS.md")

    assert "`kis-op`" in content
    assert "`kis-dev`" in content
    assert "127.0.0.1:8010" in content
    assert "127.0.0.1:8011" in content
    assert "start-chatgpt.ps1 kis-op" in content
    assert "start-chatgpt.ps1 kis-dev" in content
    assert "run concurrently" in content
    assert "peer instance is neither inspected for cleanup nor stopped" in content
    assert "reclaims a selected-instance listener or orphan process tree" in content
    assert "current.json" in content
    assert "KIS_MCP_PORT_OWNED_BY_OTHER_PROCESS" in content
    assert "KIS_MCP_PORT_IN_USE" not in content
    assert "KIS_MCP_OTHER_INSTANCE_ACTIVE" not in content


def test_spec_documents_application_vault_for_tunnel_credentials() -> None:
    content = _document("SPEC.md")

    assert "application-managed encrypted vault" in content
    assert "`tunnel_secret_ref`" in content
    assert "tunnel_credential_target" not in content
    assert "per-user Generic Credentials in Windows Credential Manager" not in content
    assert "named Windows credential is missing" not in content
