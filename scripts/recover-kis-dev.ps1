[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Foreground,
    [string]$ReadPath = ''
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = [IO.Path]::GetFullPath($RepositoryRoot)

function Resolve-KisDevRecoveryReadPath {
    param([Parameter(Mandatory)][string]$RelativePath)

    if ([string]::IsNullOrWhiteSpace($RelativePath) -or [IO.Path]::IsPathRooted($RelativePath)) {
        throw 'KIS_DEV_RECOVERY_READ_PATH_INVALID: path must be repository-relative.'
    }
    $Segments = @($RelativePath -split '[\\/]' | Where-Object { $_ -ne '' })
    if ($Segments.Count -eq 0 -or @($Segments | Where-Object { $_ -in @('.', '..') }).Count -gt 0) {
        throw 'KIS_DEV_RECOVERY_READ_PATH_INVALID: traversal segments are not allowed.'
    }
    $Candidate = [IO.Path]::GetFullPath((Join-Path $RepositoryRoot $RelativePath))
    $Prefix = $RepositoryRoot.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if (-not $Candidate.StartsWith($Prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'KIS_DEV_RECOVERY_READ_PATH_INVALID: path escapes the repository root.'
    }
    $Current = $RepositoryRoot
    foreach ($Segment in $Segments) {
        $Current = Join-Path $Current $Segment
        if (Test-Path -LiteralPath $Current) {
            $Item = Get-Item -LiteralPath $Current -Force
            if (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "KIS_DEV_RECOVERY_READ_REPARSE_POINT: $RelativePath"
            }
        }
    }
    return $Candidate
}

function Read-KisDevRecoveryFile {
    param([Parameter(Mandatory)][string]$RelativePath)

    $Candidate = Resolve-KisDevRecoveryReadPath -RelativePath $RelativePath
    if (-not [IO.File]::Exists($Candidate)) {
        throw "KIS_DEV_RECOVERY_READ_NOT_FOUND: $RelativePath"
    }
    $Info = [IO.FileInfo]::new($Candidate)
    if (($Info.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "KIS_DEV_RECOVERY_READ_REPARSE_POINT: $RelativePath"
    }
    if ($Info.Length -gt 1048576) {
        throw "KIS_DEV_RECOVERY_READ_TOO_LARGE: $RelativePath"
    }
    $Utf8 = [Text.UTF8Encoding]::new($false, $true)
    try {
        $Content = $Utf8.GetString([IO.File]::ReadAllBytes($Candidate))
    }
    catch [Text.DecoderFallbackException] {
        throw "KIS_DEV_RECOVERY_READ_NOT_UTF8: $RelativePath"
    }
    return [ordered]@{
        schema_version = 1
        state = 'read'
        recovery_surface = 'local-shell'
        path = ($RelativePath -replace '\\', '/')
        bytes = [int64]$Info.Length
        content = $Content
    }
}

if (-not [string]::IsNullOrWhiteSpace($ReadPath)) {
    if ($Foreground) {
        throw 'KIS_DEV_RECOVERY_MODE_INVALID: ReadPath cannot be combined with Foreground.'
    }
    Read-KisDevRecoveryFile -RelativePath $ReadPath | ConvertTo-Json -Depth 8 -Compress | Write-Output
    return
}

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
