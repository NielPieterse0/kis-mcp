[CmdletBinding()]
param([string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot))

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$SettingsPath = Join-Path $RepositoryRoot 'settings\bootstrap\codex.install.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$ProjectsRoot = [System.IO.Path]::GetFullPath('C:\Projects')

function Assert-InProjects([string]$Path, [string]$Name) {
    $Full = [System.IO.Path]::GetFullPath($Path)
    $Prefix = $ProjectsRoot.TrimEnd('\') + '\'
    if ($Full -ne $ProjectsRoot -and -not $Full.StartsWith($Prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "CODEX_PATH_OUTSIDE_PROJECTS: $Name=$Full"
    }
    $Probe = $Full
    while (-not [string]::IsNullOrWhiteSpace($Probe)) {
        if (Test-Path -LiteralPath $Probe) {
            $Item = Get-Item -LiteralPath $Probe -Force
            if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "CODEX_PATH_REPARSE_POINT: $Name traverses $Probe"
            }
        }
        if ($Probe -eq $ProjectsRoot) { break }
        $Parent = Split-Path -Parent $Probe
        if ([string]::IsNullOrWhiteSpace($Parent) -or $Parent -eq $Probe) { break }
        $Probe = $Parent
    }
    return $Full
}

if ([string]$Settings.auth_mode -ne 'chatgpt') { throw 'CODEX_AUTH_MODE_INVALID' }
if ([string]$Settings.login_mode -ne 'device-auth') { throw 'CODEX_LOGIN_MODE_INVALID' }
$Executable = Assert-InProjects ([string]$Settings.executable) 'executable'
$ManagedHome = Assert-InProjects ([string]$Settings.managed_home) 'managed_home'
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw 'CODEX_EXECUTABLE_MISSING: run scripts\install-codex.ps1 first.'
}
New-Item -ItemType Directory -Path $ManagedHome -Force | Out-Null
$PreviousCodexHome = $env:CODEX_HOME
$PreviousApiKey = $env:OPENAI_API_KEY
$PreviousBaseUrl = $env:OPENAI_BASE_URL
$PreviousAccessToken = $env:CODEX_ACCESS_TOKEN
try {
    $env:CODEX_HOME = $ManagedHome
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:OPENAI_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:CODEX_ACCESS_TOKEN -ErrorAction SilentlyContinue
    & $Executable login --device-auth
    if ($LASTEXITCODE -ne 0) { throw "CODEX_CHATGPT_LOGIN_FAILED: exit $LASTEXITCODE" }
    $Status = (& $Executable login status 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $Status -notmatch 'Logged in using ChatGPT') {
        throw 'CODEX_CHATGPT_LOGIN_NOT_VERIFIED'
    }
    Write-Output 'codex_authentication=chatgpt'
}
finally {
    $env:CODEX_HOME = $PreviousCodexHome
    $env:OPENAI_API_KEY = $PreviousApiKey
    $env:OPENAI_BASE_URL = $PreviousBaseUrl
    $env:CODEX_ACCESS_TOKEN = $PreviousAccessToken
}
