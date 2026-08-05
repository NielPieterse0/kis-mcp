param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('claude', 'opencode', 'codex')]
    [string]$Platform,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$HostArguments
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\bootstrap\agentsys.install.json'
$AgnixSettingsPath = Join-Path $RepositoryRoot 'settings\bootstrap\agnix.install.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$AgnixSettings = Get-Content -LiteralPath $AgnixSettingsPath -Raw | ConvertFrom-Json
$ManagedHome = [System.IO.Path]::GetFullPath([string]$Settings.managed_home)
$AgentSysInstallRoot = [System.IO.Path]::GetFullPath([string]$Settings.install_root)
$AgnixInstallRoot = [System.IO.Path]::GetFullPath([string]$AgnixSettings.install_root)
$ProjectsRoot = [System.IO.Path]::GetFullPath('C:\Projects')
$Prefix = $ProjectsRoot.TrimEnd('\') + '\'
foreach ($ManagedPath in @($ManagedHome, $AgentSysInstallRoot, $AgnixInstallRoot)) {
    if (-not $ManagedPath.StartsWith($Prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "AGENTSYS_MANAGED_PATH_OUTSIDE_PROJECTS: $ManagedPath"
    }
}

$env:HOME = $ManagedHome
$env:USERPROFILE = $ManagedHome
$env:APPDATA = Join-Path $ManagedHome 'AppData\Roaming'
$env:LOCALAPPDATA = Join-Path $ManagedHome 'AppData\Local'
$env:XDG_CONFIG_HOME = Join-Path $ManagedHome '.config'
$env:OPENCODE_CONFIG_DIR = Join-Path $ManagedHome '.config\opencode'
$env:CODEX_HOME = Join-Path $ManagedHome '.codex'
$env:CLAUDE_CONFIG_DIR = Join-Path $ManagedHome '.claude'

$ManagedBinPaths = @(
    (Join-Path $AgnixInstallRoot 'node_modules\.bin'),
    (Join-Path $AgentSysInstallRoot 'node_modules\.bin')
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
if ($ManagedBinPaths.Count -gt 0) {
    $env:PATH = (($ManagedBinPaths -join [System.IO.Path]::PathSeparator) + [System.IO.Path]::PathSeparator + $env:PATH)
}

$Command = Get-Command $Platform -CommandType Application, ExternalScript -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($null -eq $Command) {
    throw "AGENTSYS_HOST_COMMAND_UNAVAILABLE: '$Platform' is not installed or not on PATH. The managed profile is ready at $ManagedHome."
}

& $Command.Source @HostArguments
exit $LASTEXITCODE
