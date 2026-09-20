[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('kis-op','kis-dev')][string]$Instance,
    [Parameter(Mandatory)][string]$RunId,
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [ValidateRange(1,60)][int]$PollSeconds = 2,
    [ValidateRange(1,300)][int]$FailureGraceSeconds = 120,
    [ValidateRange(0,1000)][int]$MaxRecoveryAttempts = 0,
    # Operator safety invariant: automated recovery attempts must never re-fire inside 120s by default.
    [ValidateRange(1,300)][int]$RecoveryBackoffSeconds = 60,
    [ValidateRange(1,300)][int]$MaxRecoveryBackoffSeconds = 60,
    [ValidateRange(10,600)][int]$ControlPlaneFreshnessSeconds = 90
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

function Test-OwnedLocalServerHealth {
    param([Parameter(Mandatory)]$Current)
    $ListenerProperty = $Current.PSObject.Properties['server_listener_pid']
    if ($null -eq $ListenerProperty) { return $false }
    try { $ServerListenerPid = [int]$ListenerProperty.Value } catch { return $false }
    if ($ServerListenerPid -le 0 -or $null -eq (Get-Process -Id $ServerListenerPid -ErrorAction SilentlyContinue)) { return $false }
    try {
        $Payload = @{
            jsonrpc = '2.0'
            id = 1
            method = 'server/discover'
            params = @{
                _meta = @{
                    'io.modelcontextprotocol/protocolVersion' = '2026-07-28'
                    'io.modelcontextprotocol/clientCapabilities' = @{}
                    'io.modelcontextprotocol/clientInfo' = @{name='kis-health-guard-local';version='1.0'}
                }
            }
        } | ConvertTo-Json -Depth 10 -Compress
        $Headers = @{
            Accept = 'application/json, text/event-stream'
            'MCP-Protocol-Version' = '2026-07-28'
            'mcp-method' = 'server/discover'
        }
        $Response = Invoke-RestMethod -Uri $Endpoint -Method Post -Headers $Headers -ContentType 'application/json' -Body $Payload -TimeoutSec 2
        if ('2026-07-28' -in @($Response.result.supportedVersions)) { return $true }
    } catch { }
    try {
        $LegacyPayload = @{jsonrpc='2.0';id=2;method='initialize';params=@{protocolVersion='2025-06-18';capabilities=@{};clientInfo=@{name='kis-health-guard-local-legacy';version='1.0'}}} | ConvertTo-Json -Depth 8 -Compress
        $Legacy = Invoke-RestMethod -Uri $Endpoint -Method Post -Headers @{Accept='application/json, text/event-stream';'MCP-Protocol-Version'='2025-06-18'} -ContentType 'application/json' -Body $LegacyPayload -TimeoutSec 2
        return $null -ne $Legacy.result.serverInfo
    } catch { return $false }
}

function Get-TunnelHealthSnapshot {
    param([Parameter(Mandatory)]$Current)
    $Snapshot = [ordered]@{
        process = $false
        ready = $false
        control_plane_fresh = $false
        last_successful_poll_utc = $null
        poll_age_seconds = $null
        remote_reachability = 'not_directly_observed'
    }
    $TunnelProperty = $Current.PSObject.Properties['tunnel_pid']
    if ($null -eq $TunnelProperty) { return [pscustomobject]$Snapshot }
    try { $TunnelPid = [int]$TunnelProperty.Value } catch { return [pscustomobject]$Snapshot }
    if ($TunnelPid -le 0 -or $null -eq (Get-Process -Id $TunnelPid -ErrorAction SilentlyContinue)) {
        return [pscustomobject]$Snapshot
    }
    $Snapshot.process = $true
    $HealthFile = Join-Path $RuntimeRoot "provider-health-$([string]$Current.run_id).txt"
    if (-not [IO.File]::Exists($HealthFile)) { return [pscustomobject]$Snapshot }
    try {
        $Origin = [IO.File]::ReadAllText($HealthFile).Trim().TrimEnd('/')
        $Uri = [Uri]$Origin
        if ($Uri.Scheme -ne 'http' -or $Uri.Host -notin @('127.0.0.1','localhost') -or $Uri.Port -le 0) {
            return [pscustomobject]$Snapshot
        }
        $Listener = @(Get-NetTCPConnection -State Listen -LocalPort $Uri.Port -ErrorAction SilentlyContinue |
            Where-Object { [int]$_.OwningProcess -eq $TunnelPid })
        if ($Listener.Count -eq 0) { return [pscustomobject]$Snapshot }
        $Ready = Invoke-WebRequest -Uri "$Origin/readyz" -UseBasicParsing -TimeoutSec 2
        $Snapshot.ready = $Ready.StatusCode -eq 200
        $Metrics = [string](Invoke-WebRequest -Uri "$Origin/metrics" -UseBasicParsing -TimeoutSec 2).Content
        $Match = [regex]::Match(
            $Metrics,
            '(?m)^commands_poll_last_successful_timestamp_seconds(?:\{[^}]*\})?\s+([0-9.eE+\-]+)\s*$'
        )
        if ($Match.Success) {
            $Timestamp = [double]::Parse($Match.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture)
            $Now = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0
            $Age = [Math]::Max(0.0, $Now - $Timestamp)
            $Snapshot.poll_age_seconds = [Math]::Round($Age, 3)
            $Snapshot.last_successful_poll_utc = [DateTimeOffset]::FromUnixTimeMilliseconds([int64]($Timestamp * 1000)).UtcDateTime.ToString('o')
            $Snapshot.control_plane_fresh = $Age -le $ControlPlaneFreshnessSeconds
        }
    } catch { }
    return [pscustomobject]$Snapshot
}

function Write-HealthEvidence {
    param([Parameter(Mandatory)]$Current,[bool]$LocalServerHealthy,[Parameter(Mandatory)]$Tunnel)
    $Document = [ordered]@{
        schema_version = 1
        run_id = [string]$Current.run_id
        app = $Instance
        observed_utc = [DateTime]::UtcNow.ToString('o')
        local_server = if ($LocalServerHealthy) { 'healthy' } else { 'unhealthy' }
        tunnel_process = if ($Tunnel.process) { 'running' } else { 'not_running' }
        tunnel_local_ready = if ($Tunnel.ready) { 'ready' } else { 'not_ready' }
        tunnel_control_plane = if ($Tunnel.control_plane_fresh) { 'fresh' } else { 'stale_or_unobserved' }
        control_plane_last_successful_poll_utc = $Tunnel.last_successful_poll_utc
        control_plane_poll_age_seconds = $Tunnel.poll_age_seconds
        remote_reachability = $Tunnel.remote_reachability
    }
    $Path = Join-Path $RuntimeRoot "health-state-$RunId.json"
    $Temporary = "$Path.next-$([Guid]::NewGuid().ToString('N'))"
    [IO.File]::WriteAllText($Temporary, ($Document | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($Temporary, $Path, $true)
}

function Test-OwnedHealth {
    param([Parameter(Mandatory)]$Current)
    $Local = Test-OwnedLocalServerHealth -Current $Current
    $Tunnel = Get-TunnelHealthSnapshot -Current $Current
    Write-HealthEvidence -Current $Current -LocalServerHealthy $Local -Tunnel $Tunnel
    return $Local -and $Tunnel.process -and $Tunnel.ready -and $Tunnel.control_plane_fresh
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

    $LocalHealthy = Test-OwnedLocalServerHealth -Current $Current
    Start-Sleep -Seconds $FailureGraceSeconds
    $Current = Read-OwnedCurrent
    if ($null -eq $Current) { return }
    if (Test-OwnedHealth -Current $Current) { continue }

    $RecoveryScript = Join-Path $RepositoryRoot 'scripts\recover-chatgpt.ps1'
    $LocalHealthyAfterGrace = Test-OwnedLocalServerHealth -Current $Current
    $TunnelOnly = $LocalHealthy -and $LocalHealthyAfterGrace
    $Attempt = 0
    $Backoff = $RecoveryBackoffSeconds
    while ($MaxRecoveryAttempts -eq 0 -or $Attempt -lt $MaxRecoveryAttempts) {
        $Attempt += 1
        try {
            if ($TunnelOnly) {
                & $RecoveryScript -Instance $Instance -RepositoryRoot $RepositoryRoot -ExpectedRunId $RunId -TunnelOnly | Write-Output
                break
            }
            & $RecoveryScript -Instance $Instance -RepositoryRoot $RepositoryRoot -ExpectedRunId $RunId | Write-Output
            return
        }
        catch {
            $Mode = if ($TunnelOnly) { 'tunnel_only' } else { 'full_runtime' }
            Write-Warning "KIS_MCP_HEALTH_RECOVERY_FAILED: instance=$Instance mode=$Mode attempt=$Attempt error=$($_.Exception.Message)"
            if ($MaxRecoveryAttempts -gt 0 -and $Attempt -ge $MaxRecoveryAttempts) { throw }
            Start-Sleep -Seconds $Backoff
            $Backoff = [Math]::Min($MaxRecoveryBackoffSeconds, [Math]::Max($Backoff + 1, $Backoff * 2))
        }
    }
    Start-Sleep -Seconds $PollSeconds
}
}
finally {
    if ($null -ne $GuardLock) { $GuardLock.Dispose() }
}