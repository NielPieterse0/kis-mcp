[CmdletBinding()]
param(
    [string]$Instance = '',
    [int]$TimeoutSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'tunnel-state.ps1')

function Assert-KisMcpInstanceName {
    param(
        [ValidateSet('operation', 'development')]
        [string]$Name
    )
    return $Name
}

function Start-OwnedProcess {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [hashtable]$Environment = @{}
    )

    $Info = [System.Diagnostics.ProcessStartInfo]::new()
    $Info.FileName = $Executable
    $Info.WorkingDirectory = $WorkingDirectory
    $Info.UseShellExecute = $false
    $Info.CreateNoWindow = $false
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
    return $Process
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
    throw "KIS_MCP_HTTP_NOT_READY: $Uri"
}

$Remote = Get-KisMcpRemoteInstance -Instance $Instance -RequireConfigured
$null = Assert-KisMcpInstanceName -Name $Remote.name
if ($TimeoutSeconds -lt 5 -or $TimeoutSeconds -gt 300) {
    throw 'KIS_MCP_TIMEOUT_INVALID: TimeoutSeconds must be between 5 and 300.'
}
if (-not (Test-Path -LiteralPath $Remote.tunnel_client_path -PathType Leaf)) {
    throw "KIS_MCP_TUNNEL_CLIENT_MISSING: $($Remote.tunnel_client_path)"
}
$KeyValue = [Environment]::GetEnvironmentVariable($Remote.control_plane_api_key_env)
if ([string]::IsNullOrWhiteSpace($KeyValue)) {
    throw "KIS_MCP_CONTROL_PLANE_API_KEY_MISSING: set $($Remote.control_plane_api_key_env)."
}
$ProfilePath = Join-Path $Remote.profile_root "$($Remote.profile_name).yaml"
if (-not (Test-Path -LiteralPath $ProfilePath -PathType Leaf)) {
    throw "KIS_MCP_TUNNEL_PROFILE_MISSING: run scripts\setup-tunnel.ps1 -Instance $($Remote.name)."
}

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $Remote.python_environment_root 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "KIS_MCP_PYTHON_MISSING: $Python"
}
$OtherInstance = if ($Remote.name -eq 'operation') { 'development' } else { 'operation' }
$OtherRemote = Get-KisMcpRemoteInstance -Instance $OtherInstance
$OtherListener = Get-NetTCPConnection `
    -LocalAddress $OtherRemote.host `
    -LocalPort $OtherRemote.port `
    -State Listen `
    -ErrorAction SilentlyContinue
if ($OtherListener) {
    throw "KIS_MCP_OTHER_INSTANCE_ACTIVE: stop '$OtherInstance' before starting '$($Remote.name)'."
}

$Listener = Get-NetTCPConnection `
    -LocalAddress $Remote.host `
    -LocalPort $Remote.port `
    -State Listen `
    -ErrorAction SilentlyContinue
if ($Listener) {
    throw "KIS_MCP_PORT_IN_USE: $($Remote.host):$($Remote.port)"
}

[System.IO.Directory]::CreateDirectory($Remote.runtime_root) | Out-Null
$RunId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$ProviderHealthFile = Join-Path $Remote.runtime_root "provider-health-$RunId.txt"
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

$Server = $null
$Tunnel = $null
try {
    $Server = Start-OwnedProcess `
        -Executable $Python `
        -Arguments @('-m', 'kis_mcp.remote_runtime', '--instance', $Remote.name) `
        -WorkingDirectory $RepositoryRoot `
        -Environment $ServerEnvironment

    $Deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    Wait-McpReady -Uri $Remote.endpoint_url -Deadline $Deadline -Process $Server

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
        -WorkingDirectory $RepositoryRoot

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

    Write-Host "kis-mcp '$($Remote.name)' is ready for ChatGPT."
    Write-Host "Tunnel profile: $($Remote.profile_name)"
    Write-Host "Tunnel ID: $($Remote.tunnel_id)"
    Write-Host "Control-plane scope ID: $($Remote.control_plane_scope_id)"
    Write-Host "Local MCP endpoint: $($Remote.endpoint_url)"
    Write-Host 'Keep this window open. Press Ctrl+C to stop both owned processes.'

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
        $Tunnel.Kill()
        $null = $Tunnel.WaitForExit(5000)
    }
    if ($null -ne $Server -and -not $Server.HasExited) {
        $Server.Kill()
        $null = $Server.WaitForExit(5000)
    }
}
