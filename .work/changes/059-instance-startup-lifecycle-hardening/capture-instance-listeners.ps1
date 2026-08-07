Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

foreach ($Port in @(8010, 8011)) {
    $Listeners = @(
        Get-NetTCPConnection `
            -LocalAddress '127.0.0.1' `
            -LocalPort $Port `
            -State Listen `
            -ErrorAction SilentlyContinue
    )
    if ($Listeners.Count -eq 0) {
        [pscustomobject]@{
            port = $Port
            pid = $null
            created = $null
            name = 'NONE'
            command_line = 'NONE'
        } | ConvertTo-Json -Compress
        continue
    }
    foreach ($Listener in $Listeners) {
        $Process = Get-CimInstance Win32_Process `
            -Filter "ProcessId=$([int]$Listener.OwningProcess)"
        [pscustomobject]@{
            port = $Port
            pid = [int]$Listener.OwningProcess
            created = [string]$Process.CreationDate
            name = [string]$Process.Name
            command_line = [string]$Process.CommandLine
        } | ConvertTo-Json -Compress
    }
}
