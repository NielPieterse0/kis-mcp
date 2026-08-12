[CmdletBinding()]
param(
    [string]$Instance = '',
    [int]$TimeoutSeconds = 60,
    [int]$AuthenticationTimeoutSeconds = 900,
    [int]$ObservationSeconds = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'tunnel-state.ps1')
. (Join-Path $PSScriptRoot 'windows-credential.ps1')
. (Join-Path $PSScriptRoot 'secret-vault.ps1')
. (Join-Path $PSScriptRoot 'provider-secrets.ps1')
. (Join-Path $PSScriptRoot 'startup-instance-lifecycle.ps1')

function Start-OwnedProcess {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [hashtable]$Environment = @{},
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

    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $Info
    if (-not $Process.Start()) {
        throw "KIS_MCP_PROCESS_START_FAILED: $Executable"
    }

    $OutputSource = "kis-mcp-process-$($Process.Id)-stdout-$([Guid]::NewGuid().ToString('N'))"
    $ErrorSource = "kis-mcp-process-$($Process.Id)-stderr-$([Guid]::NewGuid().ToString('N'))"
    $OutputJob = Register-ObjectEvent `
        -InputObject $Process `
        -EventName OutputDataReceived `
        -SourceIdentifier $OutputSource `
        -Action {
            if ($null -ne $EventArgs.Data) {
                Write-Output $EventArgs.Data
            }
        }
    $ErrorJob = Register-ObjectEvent `
        -InputObject $Process `
        -EventName ErrorDataReceived `
        -SourceIdentifier $ErrorSource `
        -Action {
            if ($null -ne $EventArgs.Data) {
                Write-Output $EventArgs.Data
            }
        }

    $Process | Add-Member -NotePropertyName KisStandardOutputPath -NotePropertyValue $StandardOutputPath
    $Process | Add-Member -NotePropertyName KisStandardErrorPath -NotePropertyValue $StandardErrorPath
    $Process | Add-Member -NotePropertyName KisStandardOutputJob -NotePropertyValue $OutputJob
    $Process | Add-Member -NotePropertyName KisStandardErrorJob -NotePropertyValue $ErrorJob
    $Process | Add-Member -NotePropertyName KisStandardOutputSource -NotePropertyValue $OutputSource
    $Process | Add-Member -NotePropertyName KisStandardErrorSource -NotePropertyValue $ErrorSource
    $Process.BeginOutputReadLine()
    $Process.BeginErrorReadLine()
    return $Process
}

function Receive-OwnedProcessStream {
    param(
        [System.Management.Automation.Job]$Job,
        [string]$Path,
        [switch]$Echo
    )

    if ($null -eq $Job) {
        return
    }
    $Lines = @(Receive-Job -Job $Job -ErrorAction SilentlyContinue)
    if ($Lines.Count -eq 0) {
        return
    }
    $TextLines = @($Lines | ForEach-Object { [string]$_ })
    [System.IO.File]::AppendAllLines(
        $Path,
        [string[]]$TextLines,
        [System.Text.UTF8Encoding]::new($false)
    )
    if ($Echo) {
        foreach ($Line in $TextLines) {
            Write-Host $Line
        }
    }
}

function Drain-OwnedProcessLogs {
    param(
        [System.Diagnostics.Process]$Process,
        [switch]$EchoStandardError
    )

    if ($null -eq $Process) {
        return
    }
    Receive-OwnedProcessStream `
        -Job $Process.KisStandardOutputJob `
        -Path $Process.KisStandardOutputPath
    Receive-OwnedProcessStream `
        -Job $Process.KisStandardErrorJob `
        -Path $Process.KisStandardErrorPath `
        -Echo:$EchoStandardError
}

function Stop-OwnedProcessLogging {
    param(
        [System.Diagnostics.Process]$Process,
        [switch]$EchoStandardError
    )

    if ($null -eq $Process) {
        return
    }
    Drain-OwnedProcessLogs -Process $Process -EchoStandardError:$EchoStandardError
    foreach ($Source in @($Process.KisStandardOutputSource, $Process.KisStandardErrorSource)) {
        Unregister-Event -SourceIdentifier $Source -ErrorAction SilentlyContinue
    }
    foreach ($Job in @($Process.KisStandardOutputJob, $Process.KisStandardErrorJob)) {
        Remove-Job -Job $Job -Force -ErrorAction SilentlyContinue
    }
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
        Drain-OwnedProcessLogs -Process $Process -EchoStandardError
        if ($Process.HasExited) {
            Drain-OwnedProcessLogs -Process $Process -EchoStandardError
            throw "KIS_MCP_HTTP_EXITED_BEFORE_READY: $($Process.ExitCode)"
        }
        try {
            $Response = Invoke-McpJsonRpc -Uri $Uri -Payload $Initialize
            if ($null -ne $Response.result.serverInfo) {
                Drain-OwnedProcessLogs -Process $Process -EchoStandardError
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
    Drain-OwnedProcessLogs -Process $Process -EchoStandardError
    throw "KIS_MCP_ENDPOINT_NOT_READY: $Uri"
}

$Remote = Get-KisMcpRemoteInstance -Instance $Instance -RequireConfigured
if ($TimeoutSeconds -lt 5 -or $TimeoutSeconds -gt 300) {
    throw 'KIS_MCP_TIMEOUT_INVALID: TimeoutSeconds must be between 5 and 300.'
}
if ($AuthenticationTimeoutSeconds -lt 30 -or $AuthenticationTimeoutSeconds -gt 3600) {
    throw 'KIS_MCP_AUTHENTICATION_TIMEOUT_INVALID: AuthenticationTimeoutSeconds must be between 30 and 3600.'
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
$AgentSettingsPath = Join-Path $RepositoryRoot 'settings\agents\code-review-agent.settings.json'
if (-not (Test-Path -LiteralPath $AgentSettingsPath -PathType Leaf)) {
    throw "KIS_MCP_AGENT_SETTINGS_MISSING: $AgentSettingsPath"
}
$AgentSettings = Get-Content -LiteralPath $AgentSettingsPath -Raw | ConvertFrom-Json
$NvidiaSecretReference = [string]$AgentSettings.nvidia.secret_ref
$NvidiaApiKeyEnvironment = [string]$AgentSettings.nvidia.api_key_env
if ($NvidiaSecretReference -ne 'secret://provider/nvidia-nim/api-key') {
    throw 'KIS_MCP_NVIDIA_SECRET_REFERENCE_INVALID'
}
if ($NvidiaApiKeyEnvironment -ne 'NVIDIA_API_KEY') {
    throw 'KIS_MCP_NVIDIA_API_KEY_ENVIRONMENT_INVALID'
}
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

$CredentialTarget = Get-KisMcpTunnelCredentialTarget -Reference $Remote.tunnel_secret_ref
$CredentialEnvironmentName = 'KIS_MCP_TUNNEL_CONTROL_PLANE_API_KEY'
$Credential = $null
$TunnelEnvironment = @{}
$Server = $null
$Tunnel = $null
$ServerListenerPid = $null
$CurrentStateWritten = $false
$CurrentStatePath = $null
$RuntimeUnlockCredentialTarget = Get-KisMcpRuntimeUnlockCredentialTarget
$RuntimeUnlockCredential = $null
$NvidiaUnlockPayload = @{}
$NvidiaApiKey = $null
$ProviderSecretEnvironment = @{}
try {
    try {
        $RuntimeUnlockCredential = Get-KisMcpWindowsCredential -Target $RuntimeUnlockCredentialTarget
    }
    catch {
        throw 'KIS_MCP_RUNTIME_UNLOCK_CREDENTIAL_MISSING: run scripts\configure-secret-runtime-unlock.ps1 once for the existing vault.'
    }
    $NvidiaUnlockPayload['unlock'] = $RuntimeUnlockCredential
    $RuntimeUnlockCredential = $null
    try {
        $null = Invoke-KisMcpSecretCommand `
            -CommandArguments @('verify-unlock') `
            -SecurePayload $NvidiaUnlockPayload
    }
    catch {
        throw 'KIS_MCP_RUNTIME_UNLOCK_CREDENTIAL_INVALID: run scripts\configure-secret-runtime-unlock.ps1 to refresh the verified runtime credential.'
    }
    $NvidiaApiKey = Resolve-KisMcpSecretInternal `
        -Reference $NvidiaSecretReference `
        -SecurePayload $NvidiaUnlockPayload
    if (-not $NvidiaApiKey) {
        throw 'KIS_MCP_NVIDIA_API_KEY_MISSING'
    }
    $ServerEnvironment[$NvidiaApiKeyEnvironment] = $NvidiaApiKey
    $ProviderSecretEnvironment = Resolve-KisMcpProviderSecretEnvironmentFromPayload `
        -RepositoryRoot $RepositoryRoot `
        -SecurePayload $NvidiaUnlockPayload
    foreach ($Name in @($ProviderSecretEnvironment.Keys)) {
        $ServerEnvironment[$Name] = [string]$ProviderSecretEnvironment[$Name]
    }
    $Server = Start-OwnedProcess `
        -Executable $Python `
        -Arguments @(
            '-m',
            'kis_mcp.remote_runtime',
            '--instance',
            $Remote.name
        ) `
        -WorkingDirectory $RepositoryRoot `
        -Environment $ServerEnvironment `
        -StandardOutputPath $ServerStdoutLog `
        -StandardErrorPath $ServerStderrLog
    $ServerEnvironment.Remove($NvidiaApiKeyEnvironment)
    if ($null -ne $Server.StartInfo) {
        $Server.StartInfo.Environment.Remove($NvidiaApiKeyEnvironment)
    }
    foreach ($Name in @($ProviderSecretEnvironment.Keys)) {
        $ServerEnvironment.Remove($Name)
        if ($null -ne $Server.StartInfo) {
            $Server.StartInfo.Environment.Remove($Name)
        }
    }
    Clear-KisMcpProviderSecretEnvironment -Environment $ProviderSecretEnvironment
    $NvidiaApiKey = $null
    $NvidiaUnlockPayload.Clear()

    $AuthenticationDeadline = [DateTime]::UtcNow.AddSeconds($AuthenticationTimeoutSeconds)
    Wait-McpReady -Uri $Remote.endpoint_url -Deadline $AuthenticationDeadline -Process $Server
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

    $Credential = Get-KisMcpWindowsCredential -Target $CredentialTarget
    $TunnelEnvironment[$CredentialEnvironmentName] = $Credential
    $Credential = $null
    $TunnelDeadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
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
    while ([DateTime]::UtcNow -lt $TunnelDeadline) {
        Drain-OwnedProcessLogs -Process $Server -EchoStandardError
        Drain-OwnedProcessLogs -Process $Tunnel
        if ($Tunnel.HasExited) {
            Drain-OwnedProcessLogs -Process $Tunnel
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

    while ([DateTime]::UtcNow -lt $TunnelDeadline) {
        Drain-OwnedProcessLogs -Process $Server -EchoStandardError
        Drain-OwnedProcessLogs -Process $Tunnel
        if ($Tunnel.HasExited) {
            Drain-OwnedProcessLogs -Process $Tunnel
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
    if ([DateTime]::UtcNow -ge $TunnelDeadline) {
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
        Drain-OwnedProcessLogs -Process $Server -EchoStandardError
        Drain-OwnedProcessLogs -Process $Tunnel
        Start-Sleep -Milliseconds 500
    }
    Drain-OwnedProcessLogs -Process $Server -EchoStandardError
    Drain-OwnedProcessLogs -Process $Tunnel
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
    Stop-OwnedProcessLogging -Process $Tunnel
    Stop-OwnedProcessLogging -Process $Server -EchoStandardError
    if ($ServerEnvironment.ContainsKey($NvidiaApiKeyEnvironment)) {
        $ServerEnvironment.Remove($NvidiaApiKeyEnvironment)
    }
    if ($null -ne $NvidiaUnlockPayload) {
        $NvidiaUnlockPayload.Clear()
    }
    Clear-KisMcpProviderSecretEnvironment -Environment $ProviderSecretEnvironment
    $RuntimeUnlockCredential = $null
    $RuntimeUnlockCredentialTarget = $null
    $NvidiaApiKey = $null
    $Credential = $null
    $CredentialTarget = $null
}
