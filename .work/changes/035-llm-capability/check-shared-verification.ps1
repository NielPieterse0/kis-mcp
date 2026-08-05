$ErrorActionPreference = 'Stop'
$CurrentPid = $PID
$Matches = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.ProcessId -ne $CurrentPid -and
            $_.CommandLine -and
            $_.CommandLine -match '(?i)(scripts[\\/]verify\.ps1|scripts[\\/]verify\.py)'
        } |
        Select-Object ProcessId, Name, CommandLine
)
$Matches | ConvertTo-Json -Depth 3
if ($Matches.Count -gt 0) {
    exit 2
}
exit 0
