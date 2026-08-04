$ErrorActionPreference = "Stop"

$active = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.ProcessId -ne $PID -and
            $_.CommandLine -and
            $_.CommandLine -match '(?i)(verify\.ps1|verify\.py|pytest)'
        }
)

if ($active.Count -gt 0) {
    $active |
        Sort-Object ProcessId |
        ForEach-Object {
            "shared_verification_process=$($_.ProcessId):$($_.Name)"
        }
    exit 2
}

"shared_verification_state=free"
exit 0
