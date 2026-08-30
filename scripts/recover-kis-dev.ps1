[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Foreground
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = [IO.Path]::GetFullPath($RepositoryRoot)
$StartScript = Join-Path $RepositoryRoot 'scripts\start-chatgpt.ps1'
if (-not [IO.File]::Exists($StartScript)) {
    throw "KIS_DEV_RECOVERY_START_SCRIPT_MISSING: $StartScript"
}

if ($Foreground) {
    & $StartScript -Instance 'kis-dev'
    return
}

$Pwsh = (Get-Command pwsh.exe -ErrorAction Stop).Source
$CommandLine = '"{0}" -NoProfile -File "{1}" -Instance "kis-dev"' -f $Pwsh, $StartScript
$Created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $CommandLine
}
if ([int]$Created.ReturnValue -ne 0 -or [int]$Created.ProcessId -le 0) {
    throw "KIS_DEV_RECOVERY_DETACH_FAILED: return=$($Created.ReturnValue)"
}

[ordered]@{
    schema_version = 1
    state = 'launched'
    instance = 'kis-dev'
    pid = [int]$Created.ProcessId
    recovery_surface = 'local-shell'
} | ConvertTo-Json -Compress | Write-Output