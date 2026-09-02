from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY_ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def _document(name: str) -> str:
    return (REPOSITORY_ROOT / name).read_text(encoding="utf-8")


def _run_startup_lifecycle(
    expression: str, *, shell: str = "pwsh"
) -> subprocess.CompletedProcess[str]:
    script_path = (SCRIPTS / "startup-instance-lifecycle.ps1").as_posix()
    return subprocess.run(
        [
            shell,
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


def test_startup_lifecycle_atomic_json_supports_windows_powershell(tmp_path: Path) -> None:
    state_path = (tmp_path / "current.json").as_posix().replace("'", "''")
    result = _run_startup_lifecycle(
        "$path='"
        + state_path
        + "'; Write-KisMcpAtomicJson -Path $path -Document ([ordered]@{value=1}); "
        "Write-KisMcpAtomicJson -Path $path -Document ([ordered]@{value=2}); "
        "$document=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json; "
        "Write-Output $document.value",
        shell="powershell.exe",
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
    credential_read = content.index("$Credential = Get-KisMcpWindowsCredential")
    profile_backup = content.index("[System.IO.File]::Move($ProfilePath, $BackupPath)")

    assert profile_exists_guard < credential_read < profile_backup
    assert "Get-KisMcpUnlockPayload" not in content
    assert "Resolve-KisMcpSecretInternal" not in content


def test_chatgpt_startup_orders_server_readiness_before_tunnel() -> None:
    content = _script("start-chatgpt.ps1")

    server_start = content.index("$Server = Start-OwnedProcess")
    server_ready = content.index("Wait-McpReady -Uri")
    tunnel_start = content.index("$Tunnel = Start-OwnedProcess")

    assert server_start < server_ready < tunnel_start
    assert "KIS_MCP_ENDPOINT_NOT_READY" in content
    assert "KIS_MCP_HTTP_NOT_READY" not in content


def test_chatgpt_startup_separates_supervised_authentication_from_tunnel_deadline() -> None:
    content = _script("start-chatgpt.ps1")

    assert "[int]$AuthenticationTimeoutSeconds = 900" in content
    assert "KIS_MCP_AUTHENTICATION_TIMEOUT_INVALID" in content
    auth_deadline = content.index("$AuthenticationDeadline =")
    server_ready = content.index(
        "Wait-McpReady -Uri $Remote.endpoint_url -Deadline $AuthenticationDeadline"
    )
    tunnel_deadline = content.index("$TunnelDeadline =")

    assert auth_deadline < server_ready < tunnel_deadline
    assert "AddSeconds($AuthenticationTimeoutSeconds)" in content
    assert "AddSeconds($TimeoutSeconds)" in content[tunnel_deadline:]
    assert "while ([DateTime]::UtcNow -lt $TunnelDeadline)" in content
    assert "if ([DateTime]::UtcNow -ge $TunnelDeadline)" in content


def test_chatgpt_startup_resolves_nvidia_secret_only_for_selected_server_child() -> None:
    content = _script("start-chatgpt.ps1")

    preflight = content.index("$Preflight = Invoke-KisMcpSelectedInstancePreflight")
    runtime_credential_read = content.index("Get-KisMcpWindowsCredential")
    secret_read = content.index("$NvidiaApiKey = Resolve-KisMcpSecretInternal")
    server_environment = content.index("$ServerEnvironment[$NvidiaApiKeyEnvironment] = $NvidiaApiKey")
    server_start = content.index("$Server = Start-OwnedProcess")
    secret_clear = content.index("$ServerEnvironment.Remove($NvidiaApiKeyEnvironment)")

    assert ". (Join-Path $PSScriptRoot 'secret-vault.ps1')" in content
    assert ". (Join-Path $PSScriptRoot 'windows-credential.ps1')" in content
    assert "$AgentSettings.nvidia.secret_ref" in content
    assert "$AgentSettings.nvidia.api_key_env" in content
    assert "Get-KisMcpUnlockPayload" not in content
    assert "Get-KisMcpRuntimeUnlockCredentialTarget" in content
    assert "Get-KisMcpWindowsCredential" in content
    assert "@('verify-unlock')" in content
    assert "Resolve-KisMcpSecretInternal" in content
    verify_unlock = content.index("@('verify-unlock')")
    assert runtime_credential_read < verify_unlock < secret_read
    assert preflight < secret_read < server_environment < server_start < secret_clear
    assert "kis_mcp.secrets.launcher" not in content
    assert "Start-KisMcpSecretAwareProcess" not in content
    assert "kis_mcp.remote_runtime" in content
    assert "$OtherInstance" not in content


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
    operation = f'\"{python}\" -m kis_mcp.remote_runtime --instance operation'
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


def test_startup_lifecycle_identifies_selected_instance_independent_of_python_path() -> None:
    stale_python = r"C:\\Users\\operator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe"
    command = f'"{stale_python}" -m kis_mcp.remote_runtime --instance development'
    result = _run_startup_lifecycle(
        "$p=[pscustomobject]@{ExecutablePath='"
        + stale_python
        + "';CommandLine='"
        + command.replace("'", "''")
        + "'}; "
        "Write-Output (Test-KisMcpSelectedServerIdentity -Process $p -Instance 'development'); "
        "Write-Output (Test-KisMcpSelectedServerIdentity -Process $p -Instance 'operation')"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["True", "False"]


def test_startup_lifecycle_accepts_canonical_launcher_when_windows_resolves_base_python() -> None:
    python = r"C:\Projects\.kis-mcp\python-env\Scripts\python.exe"
    base_python = r"C:\Users\operator\AppData\Roaming\uv\python\cpython-3.13\python.exe"
    command = f'"{python}" -m kis_mcp.remote_runtime --instance operation'
    result = _run_startup_lifecycle(
        "$p=[pscustomobject]@{ExecutablePath='"
        + base_python
        + "';CommandLine='"
        + command.replace("'", "''")
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


def test_endpoint_owner_accepts_listener_descendant_of_canonical_python_launcher() -> None:
    python = r"C:\\Projects\\.kis-mcp\\python-env\\Scripts\\python.exe"
    base_python = r"C:\\Users\\operator\\AppData\\Roaming\\uv\\python\\cpython-3.13\\python.exe"
    command = f'\\"{python}\\" -m kis_mcp.remote_runtime --instance operation'
    result = _run_startup_lifecycle(
        "$script:TestProcesses=@("
        "[pscustomobject]@{ProcessId=100;ParentProcessId=1;Name='python.exe';ExecutablePath='"
        + python
        + "';CommandLine='"
        + command.replace("'", "''")
        + "'},"
        "[pscustomobject]@{ProcessId=101;ParentProcessId=100;Name='python.exe';ExecutablePath='"
        + base_python
        + "';CommandLine='"
        + command.replace("'", "''")
        + "'}); "
        "function Get-KisMcpProcessSnapshot { return @($script:TestProcesses) }; "
        "$remote=[pscustomobject]@{endpoint_url='http://127.0.0.1:8010/mcp';app_name='kis-op';name='operation'}; "
        "$listener=[pscustomobject]@{OwningProcess=101}; "
        "Write-Output (Assert-KisMcpSelectedEndpointOwner -Remote $remote -PythonPath '"
        + python
        + "' -ServerProcessId 100 -Listener $listener)"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "101"


def test_endpoint_owner_rejects_listener_outside_selected_server_tree() -> None:
    python = r"C:\\Projects\\.kis-mcp\\python-env\\Scripts\\python.exe"
    command = f'\\"{python}\\" -m kis_mcp.remote_runtime --instance operation'
    result = _run_startup_lifecycle(
        "$script:TestProcesses=@("
        "[pscustomobject]@{ProcessId=100;ParentProcessId=1;Name='python.exe';ExecutablePath='"
        + python
        + "';CommandLine='"
        + command.replace("'", "''")
        + "'},"
        "[pscustomobject]@{ProcessId=201;ParentProcessId=2;Name='python.exe';ExecutablePath='C:\\Python\\python.exe';CommandLine='python -m unrelated'}); "
        "function Get-KisMcpProcessSnapshot { return @($script:TestProcesses) }; "
        "$remote=[pscustomobject]@{endpoint_url='http://127.0.0.1:8010/mcp';app_name='kis-op';name='operation'}; "
        "$listener=[pscustomobject]@{OwningProcess=201}; "
        "Write-Output (Assert-KisMcpSelectedEndpointOwner -Remote $remote -PythonPath '"
        + python
        + "' -ServerProcessId 100 -Listener $listener)"
    )

    assert result.returncode == 1
    assert "KIS_MCP_ENDPOINT_OWNER_STALE" in result.stderr


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


def test_stopped_finalizer_ignores_restart_handoff_without_run_id(tmp_path: Path) -> None:
    runtime_root = tmp_path.as_posix().replace("'", "''")
    result = _run_startup_lifecycle(
        "$root='"
        + runtime_root
        + "'; [System.IO.Directory]::CreateDirectory($root) | Out-Null; "
        "$path=Join-Path $root 'current.json'; "
        "Write-KisMcpAtomicJson -Path $path -Document ([ordered]@{schema_version=1;lifecycle='restarting';instance='operation'}); "
        "$remote=[pscustomobject]@{runtime_root=$root}; "
        "Set-KisMcpCurrentInstanceStopped -Remote $remote -RunId 'old-run'; "
        "$document=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json; "
        "Write-Output $document.lifecycle"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "restarting"


def test_stopped_finalizer_updates_only_matching_run_id(tmp_path: Path) -> None:
    runtime_root = tmp_path.as_posix().replace("'", "''")
    result = _run_startup_lifecycle(
        "$root='"
        + runtime_root
        + "'; [System.IO.Directory]::CreateDirectory($root) | Out-Null; "
        "$path=Join-Path $root 'current.json'; $remote=[pscustomobject]@{runtime_root=$root}; "
        "Write-KisMcpAtomicJson -Path $path -Document ([ordered]@{schema_version=1;lifecycle='ready';run_id='old-run'}); "
        "Set-KisMcpCurrentInstanceStopped -Remote $remote -RunId 'old-run'; "
        "$matched=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json; Write-Output $matched.lifecycle; "
        "Write-KisMcpAtomicJson -Path $path -Document ([ordered]@{schema_version=1;lifecycle='ready';run_id='new-run'}); "
        "Set-KisMcpCurrentInstanceStopped -Remote $remote -RunId 'old-run'; "
        "$mismatched=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json; Write-Output $mismatched.lifecycle"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["stopped", "ready"]


def test_selected_preflight_invalidates_previous_ready_state_before_reclaim() -> None:
    lifecycle = _script("startup-instance-lifecycle.ps1")

    marker = "Set-KisMcpCurrentInstanceRestarting -Remote $Remote"
    assert marker in lifecycle
    assert lifecycle.index(marker) < lifecycle.index("$Processes = Get-KisMcpProcessSnapshot")
    assert "lifecycle = 'restarting'" in lifecycle


def test_chatgpt_startup_records_failure_after_successful_preflight() -> None:
    content = _script("start-chatgpt.ps1")
    lifecycle = _script("startup-instance-lifecycle.ps1")

    current_state = content.index("$CurrentStatePath = $null")
    assert current_state < content.index("try {", current_state)
    assert "Set-KisMcpCurrentInstanceStartupFailed -Remote $Remote -RunId $RunId" in content
    assert content.index("$Preflight = Invoke-KisMcpSelectedInstancePreflight") < content.index(
        "$NvidiaApiKey = Resolve-KisMcpSecretInternal"
    )
    assert "lifecycle = 'startup_failed'" in lifecycle


def test_repository_ignores_plaintext_env_directories() -> None:
    ignored = _document(".gitignore").splitlines()

    assert ".env/" in ignored


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


def test_tunnel_setup_reads_windows_credential_without_vault_unlock() -> None:
    content = _script("setup-tunnel.ps1")

    profile_guard = content.index("if ($ProfileExists -and -not $BackupExistingProfile)")
    credential_read = content.index("$Credential = Get-KisMcpWindowsCredential")

    assert profile_guard < credential_read
    assert "Get-KisMcpUnlockPayload" not in content
    assert "Resolve-KisMcpSecretInternal" not in content


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


def test_kis_dev_recovery_surface_is_hard_bound_to_development_instance() -> None:
    wrapper = _script("recover-kis-dev.ps1")
    general = _script("recover-chatgpt.ps1")

    assert "Instance = 'kis-dev'" in wrapper
    assert "recover-chatgpt.ps1" in wrapper
    assert "active_instance" not in wrapper
    assert "KIS_MCP_RECOVERY_INSTANCE_INVALID" in general


def test_kis_dev_recovery_surface_supports_foreground_and_detached_launch() -> None:
    wrapper = _script("recover-kis-dev.ps1")
    general = _script("recover-chatgpt.ps1")

    assert "[switch]$Foreground" in wrapper
    assert "Invoke-CimMethod -ClassName Win32_Process -MethodName Create" in general
    assert "KIS_MCP_RECOVERY_DETACH_FAILED" in general
    assert "recovery_surface = 'local-shell'" in general


def test_kis_dev_recovery_surface_reads_repository_file_without_runtime() -> None:
    script = SCRIPTS / "recover-kis-dev.ps1"
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(script),
            "-ReadPath",
            "AGENTS.md",
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["state"] == "read"
    assert payload["recovery_surface"] == "local-shell"
    assert payload["path"] == "AGENTS.md"
    assert "# kis-mcp" in payload["content"]


def test_kis_dev_recovery_surface_rejects_repository_escape() -> None:
    script = SCRIPTS / "recover-kis-dev.ps1"
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(script), "-ReadPath", "..\\AGENTS.md"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "KIS_MCP_RECOVERY_READ_PATH_INVALID" in result.stderr


def test_kis_dev_recovery_read_does_not_require_runtime_launcher(tmp_path: Path) -> None:
    (tmp_path / "diagnostic.txt").write_text("independent-read\n", encoding="utf-8")
    script = SCRIPTS / "recover-kis-dev.ps1"
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(script),
            "-RepositoryRoot",
            str(tmp_path),
            "-ReadPath",
            "diagnostic.txt",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert not (tmp_path / "scripts" / "start-chatgpt.ps1").exists()
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["content"].replace("\r\n", "\n") == "independent-read\n"


def test_kis_dev_recovery_read_rejects_invalid_utf8(tmp_path: Path) -> None:
    (tmp_path / "binary.dat").write_bytes(b"\xff\xfe\xfd")
    script = SCRIPTS / "recover-kis-dev.ps1"
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(script),
            "-RepositoryRoot",
            str(tmp_path),
            "-ReadPath",
            "binary.dat",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "KIS_MCP_RECOVERY_READ_NOT_UTF8" in result.stderr


def test_kis_dev_recovery_read_rejects_oversized_file(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_bytes(b"x" * (1048576 + 1))
    script = SCRIPTS / "recover-kis-dev.ps1"
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(script),
            "-RepositoryRoot",
            str(tmp_path),
            "-ReadPath",
            "large.txt",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "KIS_MCP_RECOVERY_READ_TOO_LARGE" in result.stderr


def test_recovery_docs_distinguish_oauth_discovery_from_mcp_operation_failure() -> None:
    content = _document("docs/operations/recovery-troubleshooting.md")

    assert "OAuth discovery 404" in content
    assert "mcp-tool.fetch" in content
    assert "invalid_mcp_response" in content
    assert "404, 429, or 5xx" in content
    assert "must remain an error" in content
    assert "-ReadPath" in content


def test_tunnel_setup_captures_provider_cli_output() -> None:
    content = _script("setup-tunnel.ps1")

    assert "setup-$RunId.log" in content
    assert "$InitOutput = & $Remote.tunnel_client_path init" in content
    assert "$DoctorOutput = & $Remote.tunnel_client_path doctor" in content
    assert "2>&1" in content
    assert "[System.IO.File]::AppendAllLines" in content
    assert "setup_log=" in content


def test_chatgpt_startup_drains_owned_process_output_live_and_retains_logs() -> None:
    content = _script("start-chatgpt.ps1")

    assert "RedirectStandardOutput = $true" in content
    assert "RedirectStandardError = $true" in content
    assert "Register-ObjectEvent" in content
    assert "BeginOutputReadLine()" in content
    assert "BeginErrorReadLine()" in content
    assert "Drain-OwnedProcessLogs" in content
    assert "-EchoStandardError" in content
    assert "ReadToEndAsync()" not in content
    assert "server-stdout-$RunId.log" in content
    assert "server-stderr-$RunId.log" in content
    assert "tunnel-stdout-$RunId.log" in content
    assert "tunnel-stderr-$RunId.log" in content
    assert "logs = [ordered]@{" in content


def test_chatgpt_startup_uses_runtime_canonical_policy_fingerprint() -> None:
    content = _script("start-chatgpt.ps1")

    assert "Get-FileHash -LiteralPath $PolicyPath" not in content
    assert "$PolicyFingerprint = [string](& $Python -c" in content
    assert "json.dumps(policy,sort_keys=True,separators=(',',':'))" in content


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
