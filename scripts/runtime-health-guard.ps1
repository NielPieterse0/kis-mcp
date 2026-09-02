[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('kis-op','kis-dev')][string]$Instance,
    [Parameter(Mandatory)][string]$RunId,
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [ValidateRange(1,60)][int]$PollSeconds = 2,
    [ValidateRange(1,60)][int]$FailureGraceSeconds = 60,
    [ValidateRange(0,1000)][int]$MaxRecoveryAttempts = 0,
    [ValidateRange(1,300)][int]$RecoveryBackoffSeconds = 2,
    [ValidateRange(1,300)][int]$MaxRecoveryBackoffSeconds = 60
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepositoryRoot = [IO.Path]::GetFullPath($RepositoryRoot)
$Settings = Get-Content (Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json') -Raw | ConvertFrom-Json
$Internal = if ($Instance -eq 'kis-op') { 'operation' } else { 'development' }
$Record = $Settings.remote_mcp.instances.PSObject.Properties[$Internal].Value
$Endpoint = "http://$([string]$Settings.remote_mcp.host):$([int]$Record.port)$([string]$Settings.remote_mcp.path)"
$RuntimeRoot = Join-Path ([string]$Settings.paths.state_root) "tunnel-client\runtime\$Internal"
$CurrentPath = Join-Path $RuntimeRoot 'current.json'
function Read-OwnedCurrent {
    if (-not [IO.File]::Exists($CurrentPath)) { return $null }
    try { $Current = Get-Content $CurrentPath -Raw | ConvertFrom-Json } catch { return $null }
    $Lifecycle = $Current.PSObject.Properties['lifecycle']
    if ($null -eq $Lifecycle -or [string]$Lifecycle.Value -notin @('ready', 'stopped')) {
        return $null
    }
    $Expected = [ordered]@{
        run_id = $RunId
        app = $Instance
    }
    foreach ($Name in $Expected.Keys) {
        $Property = $Current.PSObject.Properties[$Name]
        if ($null -eq $Property -or [string]$Property.Value -cne [string]$Expected[$Name]) {
            return $null
        }
    }
    return $Current
}

function Test-OwnedHealth {
    param([Parameter(Mandatory)]$Current)
    foreach ($Name in @('launcher_pid','server_pid','server_listener_pid','tunnel_pid')) {
        $Property = $Current.PSObject.Properties[$Name]
        if ($null -eq $Property) { return $false }
        try { $Value = [int]$Property.Value } catch { return $false }
        if ($Value -le 0 -or $null -eq (Get-Process -Id $Value -ErrorAction SilentlyContinue)) { return $false }
    }
    try {
        $ServerListenerPid = [int]$Current.PSObject.Properties['server_listener_pid'].Value
        $EndpointUri = [Uri]$Endpoint
        $ServerListener = @(Get-NetTCPConnection -State Listen -LocalPort $EndpointUri.Port -ErrorAction SilentlyContinue |
            Where-Object { [int]$_.OwningProcess -eq $ServerListenerPid })
        if ($ServerListener.Count -eq 0) { return $false }
        $Payload = @{jsonrpc='2.0';id=1;method='initialize';params=@{protocolVersion='2025-06-18';capabilities=@{};clientInfo=@{name='kis-health-guard';version='1.0'}}} | ConvertTo-Json -Depth 8 -Compress
        $Response = Invoke-RestMethod -Uri $Endpoint -Method Post -Headers @{Accept='application/json, text/event-stream';'MCP-Protocol-Version'='2025-06-18'} -ContentType 'application/json' -Body $Payload -TimeoutSec 2
        if ($null -eq $Response.result.serverInfo) { return $false }
        $HealthFile = Join-Path $RuntimeRoot "provider-health-$([string]$Current.run_id).txt"
        if (-not [IO.File]::Exists($HealthFile)) { return $false }
        $Origin = [IO.File]::ReadAllText($HealthFile).Trim().TrimEnd('/')
        $Uri = [Uri]$Origin
        if ($Uri.Scheme -ne 'http' -or $Uri.Host -notin @('127.0.0.1','localhost') -or $Uri.Port -le 0) {
            return $false
        }
        $TunnelPid = [int]$Current.PSObject.Properties['tunnel_pid'].Value
        $Listener = @(Get-NetTCPConnection -State Listen -LocalPort $Uri.Port -ErrorAction SilentlyContinue |
            Where-Object { [int]$_.OwningProcess -eq $TunnelPid })
        if ($Listener.Count -eq 0) { return $false }
        $Health = Invoke-WebRequest -Uri "$Origin/readyz" -UseBasicParsing -TimeoutSec 2
        if ($Health.StatusCode -ne 200) { return $false }
    } catch { return $false }
    return $true
}

$GuardLockPath = Join-Path $RuntimeRoot "health-guard-$RunId.lock"
$GuardLock = $null
try {
    try {
        $GuardLock = [IO.File]::Open(
            $GuardLockPath,
            [IO.FileMode]::OpenOrCreate,
            [IO.FileAccess]::ReadWrite,
            [IO.FileShare]::None
        )
    }
    catch [IO.IOException] {
        return
    }

while ($true) {
    $Current = Read-OwnedCurrent
    if ($null -eq $Current) { return }
    if (Test-OwnedHealth -Current $Current) {
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    Start-Sleep -Seconds $FailureGraceSeconds
    $Current = Read-OwnedCurrent
    if ($null -eq $Current) { return }
    if (Test-OwnedHealth -Current $Current) { continue }

    $RecoveryScript = Join-Path $RepositoryRoot 'scripts\recover-chatgpt.ps1'
    $Attempt = 0
    $Backoff = $RecoveryBackoffSeconds
    while ($MaxRecoveryAttempts -eq 0 -or $Attempt -lt $MaxRecoveryAttempts) {
        $Attempt += 1
        try {
            & $RecoveryScript -Instance $Instance -RepositoryRoot $RepositoryRoot -ExpectedRunId $RunId | Write-Output
            return
        }
        catch {
            Write-Warning "KIS_MCP_HEALTH_RECOVERY_FAILED: instance=$Instance attempt=$Attempt error=$($_.Exception.Message)"
            if ($MaxRecoveryAttempts -gt 0 -and $Attempt -ge $MaxRecoveryAttempts) { throw }
            Start-Sleep -Seconds $Backoff
            $Backoff = [Math]::Min($MaxRecoveryBackoffSeconds, [Math]::Max($Backoff + 1, $Backoff * 2))
        }
    }
}
}
finally {
    if ($null -ne $GuardLock) { $GuardLock.Dispose() }
}