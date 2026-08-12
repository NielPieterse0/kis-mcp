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

if ([string]$Settings.package -ne '@openai/codex' -or [string]$Settings.version -ne '0.147.0') {
    throw 'CODEX_SETTINGS_INVALID: exact @openai/codex@0.147.0 is required.'
}
if ([string]$Settings.auth_mode -ne 'chatgpt') {
    throw 'CODEX_AUTH_MODE_INVALID: chatgpt is required.'
}
$InstallRoot = Assert-InProjects ([string]$Settings.install_root) 'install_root'
$Executable = Assert-InProjects ([string]$Settings.executable) 'executable'
$ManagedHome = Assert-InProjects ([string]$Settings.managed_home) 'managed_home'
$CacheRoot = Assert-InProjects ([string]$Settings.npm_cache_root) 'npm_cache_root'
$TempRoot = Assert-InProjects ([string]$Settings.temp_root) 'temp_root'
$QuarantineRoot = Assert-InProjects ([string]$Settings.quarantine_root) 'quarantine_root'
$Npm = Get-Command 'npm.cmd' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $Npm) { throw 'CODEX_NPM_MISSING: npm.cmd is required.' }
foreach ($Path in @($CacheRoot, $TempRoot, $QuarantineRoot, $ManagedHome, (Split-Path -Parent $InstallRoot))) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}
$StageId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$Stage = Assert-InProjects (Join-Path $TempRoot "codex-$StageId") 'staging_root'
New-Item -ItemType Directory -Path $Stage -Force | Out-Null
$env:NPM_CONFIG_CACHE = $CacheRoot
$env:NPM_CONFIG_AUDIT = 'false'
$env:NPM_CONFIG_FUND = 'false'
$env:NPM_CONFIG_UPDATE_NOTIFIER = 'false'
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$PackageSpec = "$($Settings.package)@$($Settings.version)"
& $Npm.Source install --prefix $Stage $PackageSpec --save-exact --ignore-scripts --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw "CODEX_PACKAGE_INSTALL_FAILED: npm exit $LASTEXITCODE" }
$PackageJsonPath = Join-Path $Stage 'node_modules\@openai\codex\package.json'
$StageExecutable = Join-Path $Stage 'node_modules\.bin\codex.cmd'
if (-not (Test-Path $PackageJsonPath -PathType Leaf) -or -not (Test-Path $StageExecutable -PathType Leaf)) {
    throw 'CODEX_PACKAGE_INVALID: package metadata or executable missing.'
}
$PackageJson = Get-Content $PackageJsonPath -Raw | ConvertFrom-Json
if ([string]$PackageJson.name -ne '@openai/codex' -or [string]$PackageJson.version -ne '0.147.0') {
    throw 'CODEX_IDENTITY_MISMATCH'
}
$Quarantine = Join-Path $QuarantineRoot $StageId
New-Item -ItemType Directory -Path $Quarantine -Force | Out-Null
$PreviousPackage = Join-Path $Quarantine 'previous-package'
$FailedPackage = Join-Path $Quarantine 'failed-package'
$HadPreviousPackage = Test-Path -LiteralPath $InstallRoot
if ($HadPreviousPackage) {
    Move-Item -LiteralPath $InstallRoot -Destination $PreviousPackage
}
try {
    Move-Item -LiteralPath $Stage -Destination $InstallRoot
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw 'CODEX_ACTIVATION_FAILED: configured executable missing after activation.'
    }
    $VersionOutput = (& $Executable --version).Trim()
    if ($LASTEXITCODE -ne 0 -or $VersionOutput -notmatch '0\.147\.0') {
        throw "CODEX_VERSION_MISMATCH: $VersionOutput"
    }
}
catch {
    $ActivationError = $_
    try {
        if (Test-Path -LiteralPath $InstallRoot) {
            Move-Item -LiteralPath $InstallRoot -Destination $FailedPackage
        }
        if ($HadPreviousPackage -and (Test-Path -LiteralPath $PreviousPackage)) {
            Move-Item -LiteralPath $PreviousPackage -Destination $InstallRoot
        }
    }
    catch {
        throw 'CODEX_ACTIVATION_ROLLBACK_FAILED'
    }
    throw $ActivationError
}
[ordered]@{
    schema_version = 1
    tool_id = 'codex-cli'
    version = '0.147.0'
    executable = $Executable
    managed_home = $ManagedHome
    authentication = 'not_configured'
    previous_state_quarantine = $Quarantine
} | ConvertTo-Json -Depth 4
