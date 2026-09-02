[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Instance,
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Foreground,
    [string]$ReadPath = '',
    [string]$ExpectedRunId = '',
    [ValidateRange(0, 300)][int]$WaitSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepositoryRoot = [IO.Path]::GetFullPath($RepositoryRoot)
$Alias = $Instance.Trim().ToLowerInvariant()
$Internal = switch ($Alias) {
    { $_ -in @('kis-op','operation','op') } { 'operation'; break }
    { $_ -in @('kis-dev','development','dev') } { 'development'; break }
    default { throw "KIS_MCP_RECOVERY_INSTANCE_INVALID: $Instance" }
}
$App = if ($Internal -eq 'operation') { 'kis-op' } else { 'kis-dev' }

function Write-RecoveryReceipt {
    param([string]$State,[string]$Detail = '',[int]$ProcessId = 0,[string]$RunId = '')
    [IO.Directory]::CreateDirectory($ReceiptRoot) | Out-Null
    $Document = [ordered]@{
        schema_version = 1; state = $State; instance = $Internal; app = $App
        endpoint = $Endpoint; pid = $ProcessId; run_id = $RunId; detail = $Detail
        recovery_surface = 'local-shell'; updated_utc = [DateTime]::UtcNow.ToString('o')
    }
    $Temporary = "$ReceiptPath.next-$([Guid]::NewGuid().ToString('N'))"
    [IO.File]::WriteAllText($Temporary, ($Document | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    if ([IO.File]::Exists($ReceiptPath)) {
        try { [IO.File]::Replace($Temporary, $ReceiptPath, "$ReceiptPath.previous") }
        catch { [IO.File]::Move($Temporary, $ReceiptPath, $true) }
    } else { [IO.File]::Move($Temporary, $ReceiptPath) }
    return $Document
}

function Resolve-RecoveryReadPath {
    param([string]$RelativePath)
    if ([string]::IsNullOrWhiteSpace($RelativePath) -or [IO.Path]::IsPathRooted($RelativePath)) {
        throw 'KIS_MCP_RECOVERY_READ_PATH_INVALID: path must be repository-relative.'
    }
    $Segments = @($RelativePath -split '[\\/]' | Where-Object { $_ })
    if ($Segments.Count -eq 0 -or @($Segments | Where-Object { $_ -in @('.', '..') }).Count -gt 0) {
        throw 'KIS_MCP_RECOVERY_READ_PATH_INVALID: traversal segments are not allowed.'
    }
    $Candidate = [IO.Path]::GetFullPath((Join-Path $RepositoryRoot $RelativePath))
    $Prefix = $RepositoryRoot.TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
    if (-not $Candidate.StartsWith($Prefix,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'KIS_MCP_RECOVERY_READ_PATH_INVALID: path escapes repository root.'
    }
    $Current = $RepositoryRoot
    foreach ($Segment in $Segments) {
        $Current = Join-Path $Current $Segment
        if (Test-Path -LiteralPath $Current) {
            $Item = Get-Item -LiteralPath $Current -Force
            if (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "KIS_MCP_RECOVERY_READ_REPARSE_POINT: $RelativePath"
            }
        }
    }
    return $Candidate
}

function Test-RecoveryReady {
    if (-not [IO.File]::Exists($CurrentPath)) { return $false }
    try { $Current = Get-Content -LiteralPath $CurrentPath -Raw | ConvertFrom-Json } catch { return $false }
    $ExpectedIdentity = [ordered]@{
        lifecycle = 'ready'
        instance = $Internal
        app = $App
        endpoint = $Endpoint
    }
    foreach ($Name in $ExpectedIdentity.Keys) {
        $Property = $Current.PSObject.Properties[$Name]
        if ($null -eq $Property -or [string]$Property.Value -cne [string]$ExpectedIdentity[$Name]) {
            return $false
        }
    }
    $RunProperty = $Current.PSObject.Properties['run_id']
    if ($null -eq $RunProperty -or [string]::IsNullOrWhiteSpace([string]$RunProperty.Value)) { return $false }
    foreach ($Name in @('launcher_pid','server_pid','server_listener_pid','tunnel_pid')) {
        $Property = $Current.PSObject.Properties[$Name]
        if ($null -eq $Property) { return $false }
        try { $ProcessId = [int]$Property.Value } catch { return $false }
        if ($ProcessId -le 0) { return $false }
        if ($null -eq (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return $false }
    }
    try {
        $ServerListenerPid = [int]$Current.PSObject.Properties['server_listener_pid'].Value
        $EndpointUri = [Uri]$Endpoint
        $ServerListener = @(Get-NetTCPConnection -State Listen -LocalPort $EndpointUri.Port -ErrorAction SilentlyContinue |
            Where-Object { [int]$_.OwningProcess -eq $ServerListenerPid })
        if ($ServerListener.Count -eq 0) { return $false }
        $Payload = @{jsonrpc='2.0';id=1;method='initialize';params=@{protocolVersion='2025-06-18';capabilities=@{};clientInfo=@{name='kis-recovery';version='1.0'}}} | ConvertTo-Json -Depth 8 -Compress
        $Response = Invoke-RestMethod -Uri $Endpoint -Method Post -Headers @{Accept='application/json, text/event-stream';'MCP-Protocol-Version'='2025-06-18'} -ContentType 'application/json' -Body $Payload -TimeoutSec 2
        if ($null -eq $Response.result.serverInfo) { return $false }
    } catch { return $false }
    $RunId = [string]$Current.run_id
    $HealthFile = Join-Path $RuntimeRoot "provider-health-$RunId.txt"
    if (-not [IO.File]::Exists($HealthFile)) { return $false }
    try {
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
    return $Current
}

if (-not [string]::IsNullOrWhiteSpace($ReadPath)) {
    if ($Foreground) { throw 'KIS_MCP_RECOVERY_MODE_INVALID: ReadPath cannot be combined with Foreground.' }
    $Candidate = Resolve-RecoveryReadPath -RelativePath $ReadPath
    if (-not [IO.File]::Exists($Candidate)) { throw "KIS_MCP_RECOVERY_READ_NOT_FOUND: $ReadPath" }
    $Info = [IO.FileInfo]::new($Candidate)
    if ($Info.Length -gt 1048576) { throw "KIS_MCP_RECOVERY_READ_TOO_LARGE: $ReadPath" }
    try { $Content = [Text.UTF8Encoding]::new($false,$true).GetString([IO.File]::ReadAllBytes($Candidate)) }
    catch [Text.DecoderFallbackException] { throw "KIS_MCP_RECOVERY_READ_NOT_UTF8: $ReadPath" }
    [ordered]@{schema_version=1;state='read';instance=$Internal;app=$App;recovery_surface='local-shell';path=($ReadPath -replace '\\','/');bytes=[int64]$Info.Length;content=$Content} | ConvertTo-Json -Depth 6 -Compress | Write-Output
    return
}

$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
if (-not [IO.File]::Exists($SettingsPath)) { throw "KIS_MCP_RECOVERY_SETTINGS_MISSING: $SettingsPath" }
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$Record = $Settings.remote_mcp.instances.PSObject.Properties[$Internal].Value
if ([string]$Record.app_name -cne $App) { throw "KIS_MCP_RECOVERY_APP_IDENTITY_INVALID: $Internal" }
$Endpoint = "http://$([string]$Settings.remote_mcp.host):$([int]$Record.port)$([string]$Settings.remote_mcp.path)"
$StateRoot = [IO.Path]::GetFullPath([string]$Settings.paths.state_root)
$RuntimeRoot = Join-Path $StateRoot "tunnel-client\runtime\$Internal"
$CurrentPath = Join-Path $RuntimeRoot 'current.json'
$ReceiptRoot = Join-Path $StateRoot "runtime\$App\state\recovery"
$ReceiptPath = Join-Path $ReceiptRoot 'latest.json'
$LockPath = Join-Path $ReceiptRoot 'recovery.lock'

[IO.Directory]::CreateDirectory($ReceiptRoot) | Out-Null
$Lock = $null
$Deadline = [DateTime]::UtcNow.AddSeconds([Math]::Max(10, $WaitSeconds + 10))
while ($null -eq $Lock) {
    try { $Lock = [IO.File]::Open($LockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) }
    catch [IO.IOException] {
        if ([DateTime]::UtcNow -ge $Deadline) { throw 'KIS_MCP_RECOVERY_LOCK_TIMEOUT' }
        Start-Sleep -Milliseconds 100
    }
}
try {
    if (-not [string]::IsNullOrWhiteSpace($ExpectedRunId) -and [IO.File]::Exists($CurrentPath)) {
        try { $ObservedCurrent = Get-Content -LiteralPath $CurrentPath -Raw | ConvertFrom-Json } catch { $ObservedCurrent = $null }
        if ($null -ne $ObservedCurrent) {
            $ObservedRun = $ObservedCurrent.PSObject.Properties['run_id']
            if ($null -ne $ObservedRun -and [string]$ObservedRun.Value -cne $ExpectedRunId) {
                $Receipt = Write-RecoveryReceipt -State 'superseded' -Detail 'triggering generation no longer current' -RunId ([string]$ObservedRun.Value)
                $Receipt | ConvertTo-Json -Depth 6 -Compress | Write-Output
                return
            }
        }
    }
    $Ready = Test-RecoveryReady
    if ($Ready) {
        $Receipt = Write-RecoveryReceipt -State 'healthy' -Detail 'existing runtime reused' -ProcessId ([int]$Ready.launcher_pid) -RunId ([string]$Ready.run_id)
        $Receipt | ConvertTo-Json -Depth 6 -Compress | Write-Output
        return
    }
    $StartScript = Join-Path $RepositoryRoot 'scripts\start-chatgpt.ps1'
    if (-not [IO.File]::Exists($StartScript)) { throw "KIS_MCP_RECOVERY_START_SCRIPT_MISSING: $StartScript" }
    if ($Foreground) {
        $null = Write-RecoveryReceipt -State 'launching' -Detail 'foreground launcher started' -ProcessId $PID
        $Lock.Dispose()
        $Lock = $null
        try {
            & $StartScript -Instance $App
        }
        finally {
            $Receipt = Write-RecoveryReceipt -State 'stopped' -Detail 'foreground launcher exited' -ProcessId $PID
            $Receipt | ConvertTo-Json -Depth 6 -Compress | Write-Output
        }
        return
    }
    $Pwsh = (Get-Command pwsh.exe -ErrorAction Stop).Source
    $CommandLine = '"{0}" -NoProfile -File "{1}" -Instance "{2}"' -f $Pwsh,$StartScript,$App
    $Created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$CommandLine}
    if ([int]$Created.ReturnValue -ne 0 -or [int]$Created.ProcessId -le 0) {
        throw "KIS_MCP_RECOVERY_DETACH_FAILED: return=$($Created.ReturnValue)"
    }
    $LauncherPid = [int]$Created.ProcessId
    $null = Write-RecoveryReceipt -State 'launching' -Detail 'recovery launcher started' -ProcessId $LauncherPid

    if ($WaitSeconds -eq 0) {
    (Write-RecoveryReceipt -State 'launched' -Detail 'readiness wait disabled' -ProcessId $LauncherPid) | ConvertTo-Json -Depth 6 -Compress | Write-Output
    return
}
$ReadyDeadline = [DateTime]::UtcNow.AddSeconds($WaitSeconds)
while ([DateTime]::UtcNow -lt $ReadyDeadline) {
    $Ready = Test-RecoveryReady
    if ($Ready) {
        $Receipt = Write-RecoveryReceipt `
            -State 'ready' `
            -Detail 'runtime and tunnel verified ready' `
            -ProcessId ([int]$Ready.launcher_pid) `
            -RunId ([string]$Ready.run_id)
        $Receipt | ConvertTo-Json -Depth 6 -Compress | Write-Output
        return
    }
    Start-Sleep -Milliseconds 500
}
$null = Write-RecoveryReceipt `
    -State 'failed' `
    -Detail "KIS_MCP_RECOVERY_NOT_READY: timeout=${WaitSeconds}s" `
    -ProcessId $LauncherPid
throw "KIS_MCP_RECOVERY_NOT_READY: $App did not reach local and tunnel readiness within $WaitSeconds seconds"

}
finally {
    if ($null -ne $Lock) { $Lock.Dispose() }
}
