[CmdletBinding()]
param(
    [string]$Instance = '',
    [int]$TimeoutSeconds = 60,
    [int]$ObservationSeconds = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'tunnel-state.ps1')
. (Join-Path $PSScriptRoot 'secret-vault.ps1')
. (Join-Path $PSScriptRoot 'startup-instance-lifecycle.ps1')

function Start-OwnedProcess {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [hashtable]$Environment = @{},
        [hashtable]$SecretPayload = $null,
        [string]$StandardOutputPath,
        [string]$StandardErrorPath
    )

    foreach ($Path in @($StandardOutputPath, $StandardErrorPath)) {
        $Parent = Split-Path -Parent $Path
        [System.IO.Directory]::CreateDirectory($Parent) | Out-Null
        [System.IO.File]::WriteAllText($Path, '', [System.Text.UTF8Encoding]::new($false))
    }

    $Info = [System.Diagnostics.ProcessStartInfo]::new()
    $Info.FileName = $Executable
    $Info.WorkingDirectory = $WorkingDirectory
    $Info.UseShellExecute = $false
    $Info.CreateNoWindow = $true
    $Info.RedirectStandardOutput = $true
    $Info.RedirectStandardError = $true
    foreach ($Argument in $Arguments) {
        $Info.ArgumentList.Add($Argument)
    }
    foreach ($Name in $Environment.Keys) {
        $Info.Environment[$Name] = [string]$Environment[$Name]
    }

    if ($null -ne $SecretPayload) {
        $Process = Start-KisMcpSecretAwareProcess `
            -StartInfo $Info `
            -SecurePayload $SecretPayload
    }
    else {
        $Process = [System.Diagnostics.Process]::new()
        $Process.StartInfo = $Info
        if (-not $Process.Start()) {
            throw "KIS_MCP_PROCESS_START_FAILED: $Executable"
        }
    }
    $Process | Add-Member -NotePropertyName KisStandardOutputPath -NotePropertyValue $StandardOutputPath
    $Process | Add-Member -NotePropertyName KisStandardErrorPath -NotePropertyValue $StandardErrorPath
    $Process | Add-Member -NotePropertyName KisStandardOutputTask -NotePropertyValue $Process.StandardOutput.ReadToEndAsync()
    $Process | Add-Member -NotePropertyName KisStandardErrorTask -NotePropertyValue $Process.StandardError.ReadToEndAsync()
    return $Process
}

function Write-OwnedProcessLogs {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process) {
        return
    }
    $StandardOutput = $Process.KisStandardOutputTask.GetAwaiter().GetResult()
    $StandardError = $Process.KisStandardErrorTask.GetAwaiter().GetResult()
    [System.IO.File]::WriteAllText(
        $Process.KisStandardOutputPath,
        $StandardOutput,
        [System.Text.UTF8Encoding]::new($false)
    )
    [System.IO.File]::WriteAllText(
        $Process.KisStandardErrorPath,
        $StandardError,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Invoke-McpJsonRpc {
    param(
        [string]$Uri,
        [hashtable]$Payload,
        [int]$RequestTimeoutSeconds = 3
    )

    $Headers = @{
        Accept = 'application/json, text/event-stream'
        'MCP-Protocol-Version' = '2025-06-18'
    }
    $Body = $Payload | ConvertTo-Json -Depth 20 -Compress
    return Invoke-RestMethod `
        -Uri $Uri `
        -Method Post `
        -Headers $Headers `
        -ContentType 'application/json' `
        -Body $Body `
        -TimeoutSec $RequestTimeoutSeconds
}

function Wait-McpReady {
    param(
        [string]$Uri,
        [datetime]$Deadline,
        [System.Diagnostics.Process]$Process
    )

    $Initialize = @{
        jsonrpc = '2.0'
        id = 1
        method = 'initialize'
        params = @{
            protocolVersion = '2025-06-18'
            capabilities = @{}
            clientInfo = @{ name = 'kis-mcp-launcher'; version = '1.0' }
        }
    }
    while ([DateTime]::UtcNow -lt $Deadline) {
        if ($Process.HasExited) {
            throw "KIS_MCP_HTTP_EXITED_BEFORE_READY: $($Process.ExitCode)"
        }
        try {
            $Response = Invoke-McpJsonRpc -Uri $Uri -Payload $Initialize
            if ($null -ne $Response.result.serverInfo) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
    throw "KIS_MCP_ENDPOINT_NOT_READY: $Uri"
}

$Remote = Get-KisMcpRemoteInstance -Instance $Instance -RequireConfigured
if ($TimeoutSeconds -lt 5 -or $TimeoutSeconds -gt 300) {
    throw 'KIS_MCP_TIMEOUT_INVALID: TimeoutSeconds must be between 5 and 300.'
}
if ($ObservationSeconds -lt 0 -or $ObservationSeconds -gt 300) {
    throw 'KIS_MCP_OBSERVATION_SECONDS_INVALID: ObservationSeconds must be between 0 and 300.'
}
if (-not (Test-Path -LiteralPath $Remote.tunnel_client_path -PathType Leaf)) {
    throw "KIS_MCP_TUNNEL_CLIENT_MISSING: $($Remote.tunnel_client_path)"
}
$ProfilePath = Join-Path $Remote.profile_root "$($Remote.profile_name).yaml"
if (-not (Test-Path -LiteralPath $ProfilePath -PathType Leaf)) {
    throw "KIS_MCP_TUNNEL_PROFILE_MISSING: run scripts\setup-tunnel.ps1 -Instance $($Remote.name)."
}

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PolicyPath = Join-Path $RepositoryRoot 'policy\kis-mcp.policy.json'
if (-not (Test-Path -LiteralPath $PolicyPath -PathType Leaf)) {
    throw "KIS_MCP_POLICY_MISSING: $PolicyPath"
}
$PolicyFingerprint = (Get-FileHash -LiteralPath $PolicyPath -Algorithm SHA256).Hash.ToLowerInvariant()
$Python = Join-Path $Remote.python_environment_root 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "KIS_MCP_PYTHON_MISSING: $Python"
}
$Preflight = Invoke-KisMcpSelectedInstancePreflight `
    -Remote $Remote `
    -PythonPath $Python `
    -RepositoryRoot $RepositoryRoot

[System.IO.Directory]::CreateDirectory($Remote.runtime_root) | Out-Null
$RunId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$ProviderHealthFile = Join-Path $Remote.runtime_root "provider-health-$RunId.txt"
$ServerStdoutLog = Join-Path $Remote.runtime_root "server-stdout-$RunId.log"
$ServerStderrLog = Join-Path $Remote.runtime_root "server-stderr-$RunId.log"
$TunnelStdoutLog = Join-Path $Remote.runtime_root "tunnel-stdout-$RunId.log"
$TunnelStderrLog = Join-Path $Remote.runtime_root "tunnel-stderr-$RunId.log"
$StateRoot = $Remote.state_root
$ServerEnvironment = @{
    PYTHONPATH = (Join-Path $RepositoryRoot 'src')
    UV_PROJECT_ENVIRONMENT = $Remote.python_environment_root
    UV_CACHE_DIR = (Join-Path $StateRoot 'uv-cache')
    PYTHONPYCACHEPREFIX = (Join-Path $StateRoot 'python-cache')
    TEMP = (Join-Path $StateRoot 'temp')
    TMP = (Join-Path $StateRoot 'temp')
    NO_UPDATE_NOTIFIER = '1'
}

$VaultUnlockPayload = $null
$CredentialEnvironmentName = 'KIS_MCP_TUNNEL_CONTROL_PLANE_API_KEY'
$Credential = $null
$TunnelEnvironment = @{}
$Server = $null
$Tunnel = $null
$ServerListenerPid = $null
$CurrentStateWritten = $false
$CurrentStatePath = $null
try {
    $VaultUnlockPayload = Get-KisMcpUnlockPayload
    $Server = Start-OwnedProcess `
        -Executable $Python `
        -Arguments @(
            '-m',
            'kis_mcp.secrets.launcher',
            '--runtime',
            'remote',
            '--instance',
            $Remote.name
        ) `
        -WorkingDirectory $RepositoryRoot `
        -Environment $ServerEnvironment `
        -SecretPayload $VaultUnlockPayload `
        -StandardOutputPath $ServerStdoutLog `
        -StandardErrorPath $ServerStderrLog

    $Deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    Wait-McpReady -Uri $Remote.endpoint_url -Deadline $Deadline -Process $Server
    $Listener = Get-NetTCPConnection `
        -LocalAddress $Remote.host `
        -LocalPort $Remote.port `
        -State Listen `
        -ErrorAction SilentlyContinue
    $ServerListenerPid = Assert-KisMcpSelectedEndpointOwner `
        -Remote $Remote `
        -PythonPath $Python `
        -ServerProcessId $Server.Id `
        -Listener $Listener

    $Credential = Resolve-KisMcpSecretInternal `
        -Reference $Remote.tunnel_secret_ref `
        -SecurePayload $VaultUnlockPayload
    $TunnelEnvironment[$CredentialEnvironmentName] = $Credential
    $Credential = $null
    try {
        $Tunnel = Start-OwnedProcess `
            -Executable $Remote.tunnel_client_path `
            -Arguments @(
                'run',
                '--profile', $Remote.profile_name,
                '--profile-dir', $Remote.profile_root,
                '--mcp.server-url', $Remote.endpoint_url,
                '--health.listen-addr', '127.0.0.1:0',
                '--health.url-file', $ProviderHealthFile
            ) `
            -WorkingDirectory $RepositoryRoot `
            -Environment $TunnelEnvironment `
            -StandardOutputPath $TunnelStdoutLog `
            -StandardErrorPath $TunnelStderrLog
    }
    finally {
        $TunnelEnvironment[$CredentialEnvironmentName] = ''
        $TunnelEnvironment.Clear()
        $Credential = $null
    }

    $ProviderHealth = $null
    while ([DateTime]::UtcNow -lt $Deadline) {
        if ($Tunnel.HasExited) {
            throw "KIS_MCP_TUNNEL_EXITED_BEFORE_READY: $($Tunnel.ExitCode)"
        }
        if (Test-Path -LiteralPath $ProviderHealthFile -PathType Leaf) {
            $Origin = [System.IO.File]::ReadAllText($ProviderHealthFile).Trim()
            try {
                $Uri = [Uri]$Origin
            }
            catch {
                throw 'KIS_MCP_TUNNEL_HEALTH_ORIGIN_INVALID'
            }
            if (
                $Uri.Scheme -ne 'http' -or
                $Uri.Host -notin @('127.0.0.1', 'localhost') -or
                $Uri.Port -le 0 -or
                $Uri.UserInfo -or
                $Uri.AbsolutePath -ne '/' -or
                $Uri.Query -or
                $Uri.Fragment
            ) {
                throw 'KIS_MCP_TUNNEL_HEALTH_ORIGIN_NOT_LOOPBACK'
            }
            $ProviderHealth = $Origin.TrimEnd('/') + '/readyz'
            break
        }
        Start-Sleep -Milliseconds 200
    }
    if (-not $ProviderHealth) {
        throw 'KIS_MCP_TUNNEL_HEALTH_ORIGIN_MISSING'
    }

    while ([DateTime]::UtcNow -lt $Deadline) {
        if ($Tunnel.HasExited) {
            throw "KIS_MCP_TUNNEL_EXITED_BEFORE_READY: $($Tunnel.ExitCode)"
        }
        try {
            $Result = Invoke-WebRequest -Uri $ProviderHealth -UseBasicParsing -TimeoutSec 2
            if ($Result.StatusCode -eq 200) {
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if ([DateTime]::UtcNow -ge $Deadline) {
        throw "KIS_MCP_TUNNEL_NOT_READY: $ProviderHealth"
    }

    $StartupStatePath = Join-Path $Remote.runtime_root "startup-state-$RunId.json"
    $StartupState = [ordered]@{
        schema_version = 1
        health = 'ready'
        app = $Remote.app_name
        instance = $Remote.name
        endpoint = $Remote.endpoint_url
        policy_fingerprint = $PolicyFingerprint
        processes = [ordered]@{
            launcher_pid = $PID
            server_pid = $Server.Id
            server_listener_pid = $ServerListenerPid
            tunnel_pid = $Tunnel.Id
            python_executable = $Python
            repository_root = $RepositoryRoot
        }
        preflight = [ordered]@{
            reclaimed_server_processes = $Preflight.reclaimed_server_processes
            reclaimed_tunnel_processes = $Preflight.reclaimed_tunnel_processes
            quarantined_transients = $Preflight.quarantined_transients
        }
        tunnel = [ordered]@{
            state = 'ready'
            profile = $Remote.profile_name
            id = $Remote.tunnel_id
        }
        logs = [ordered]@{
            server_stdout = $ServerStdoutLog
            server_stderr = $ServerStderrLog
            tunnel_stdout = $TunnelStdoutLog
            tunnel_stderr = $TunnelStderrLog
        }
    }
    [System.IO.File]::WriteAllText(
        $StartupStatePath,
        ($StartupState | ConvertTo-Json -Depth 8),
        [System.Text.UTF8Encoding]::new($false)
    )
    $CurrentStatePath = Write-KisMcpCurrentInstanceState `
        -Remote $Remote `
        -RunId $RunId `
        -LauncherPid $PID `
        -ServerPid $Server.Id `
        -ServerListenerPid $ServerListenerPid `
        -TunnelPid $Tunnel.Id `
        -PythonPath $Python `
        -RepositoryRoot $RepositoryRoot `
        -StartupStatePath $StartupStatePath
    $CurrentStateWritten = $true

    Write-Host 'health=ready'
    Write-Host "app=$($Remote.app_name)"
    Write-Host "instance=$($Remote.name)"
    Write-Host "endpoint=$($Remote.endpoint_url)"
    Write-Host "policy_fingerprint=$PolicyFingerprint"
    Write-Host 'tunnel_state=ready'
    Write-Host "tunnel_profile=$($Remote.profile_name)"
    Write-Host "tunnel_id=$($Remote.tunnel_id)"
    Write-Host "startup_state=$StartupStatePath"
    Write-Host "current_state=$CurrentStatePath"
    Write-Host "reclaimed_server_processes=$($Preflight.reclaimed_server_processes)"
    Write-Host "reclaimed_tunnel_processes=$($Preflight.reclaimed_tunnel_processes)"
    Write-Host "quarantined_transients=$($Preflight.quarantined_transients)"

    if ($ObservationSeconds -gt 0) {
        Start-Sleep -Seconds $ObservationSeconds
        return
    }

    while (-not $Server.HasExited -and -not $Tunnel.HasExited) {
        Start-Sleep -Milliseconds 500
    }
    if ($Server.HasExited) {
        throw "KIS_MCP_HTTP_EXITED: $($Server.ExitCode)"
    }
    throw "KIS_MCP_TUNNEL_EXITED: $($Tunnel.ExitCode)"
}
finally {
    if ($null -ne $Tunnel -and -not $Tunnel.HasExited) {
        $Tunnel.Kill($true)
        $null = $Tunnel.WaitForExit(5000)
    }
    if ($null -ne $Server -and -not $Server.HasExited) {
        $Server.Kill($true)
        $null = $Server.WaitForExit(5000)
    }
    if ($CurrentStateWritten) {
        Set-KisMcpCurrentInstanceStopped -Remote $Remote -RunId $RunId
    }
    else {
        Set-KisMcpCurrentInstanceStartupFailed -Remote $Remote -RunId $RunId
    }
    Write-OwnedProcessLogs -Process $Tunnel
    Write-OwnedProcessLogs -Process $Server
    if ($null -ne $VaultUnlockPayload) {
        foreach ($Name in @($VaultUnlockPayload.Keys)) {
            $VaultUnlockPayload[$Name] = $null
        }
        $VaultUnlockPayload.Clear()
    }
}
