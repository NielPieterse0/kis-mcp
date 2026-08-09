param(
    [string[]]$ScanPaths = @()
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$env:ProgramData = 'C:\ProgramData'
$env:ProgramFiles = 'C:\Program Files'
$env:SystemRoot = 'C:\Windows'
$env:WINDIR = 'C:\Windows'
$env:TEMP = 'C:\Projects\.kis-mcp\temp'
$env:TMP = 'C:\Projects\.kis-mcp\temp'

$status = Get-MpComputerStatus
if (-not $status.AntivirusEnabled) {
    throw 'WINDOWS_DEFENDER_ANTIVIRUS_DISABLED: AntivirusEnabled is false.'
}
if (-not $status.RealTimeProtectionEnabled) {
    throw 'WINDOWS_DEFENDER_REALTIME_DISABLED: RealTimeProtectionEnabled is false.'
}
if (-not $status.AntispywareEnabled) {
    throw 'WINDOWS_DEFENDER_ANTISPYWARE_DISABLED: AntispywareEnabled is false.'
}
if ($status.AntivirusSignatureLastUpdated -lt (Get-Date).AddDays(-7)) {
    throw 'WINDOWS_DEFENDER_SIGNATURE_STALE: Antivirus signatures are older than seven days.'
}

$scanCommand = Get-Command Start-MpScan -ErrorAction Stop
$scanResults = @()
foreach ($path in $ScanPaths) {
    $resolved = (Resolve-Path -LiteralPath $path -ErrorAction Stop).Path
    $startedAt = Get-Date
    Start-MpScan -ScanType CustomScan -ScanPath $resolved
    $detections = @(
        Get-MpThreatDetection -ErrorAction SilentlyContinue |
            Where-Object { $_.InitialDetectionTime -ge $startedAt.AddSeconds(-5) }
    )
    if ($detections.Count -gt 0) {
        throw "WINDOWS_DEFENDER_THREAT_DETECTED: Defender recorded $($detections.Count) new detection(s) while scanning $resolved."
    }
    $scanResults += [ordered]@{
        path = $resolved
        method = $scanCommand.Name
        detections = 0
    }
}

[ordered]@{
    antivirus_enabled = [bool]$status.AntivirusEnabled
    antispyware_enabled = [bool]$status.AntispywareEnabled
    real_time_protection_enabled = [bool]$status.RealTimeProtectionEnabled
    signatures_updated_at = $status.AntivirusSignatureLastUpdated.ToString('o')
    engine_version = [string]$status.AMEngineVersion
    product_version = [string]$status.AMProductVersion
    scan_command = $scanCommand.Name
    scans = $scanResults
} | ConvertTo-Json -Depth 5
