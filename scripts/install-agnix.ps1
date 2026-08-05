param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$SettingsPath = Join-Path $RepositoryRoot 'settings\bootstrap\agnix.install.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$ProjectsRoot = [System.IO.Path]::GetFullPath('C:\Projects')

function Assert-InProjects([string]$Path, [string]$Name) {
    $Full = [System.IO.Path]::GetFullPath($Path)
    $Prefix = $ProjectsRoot.TrimEnd('\') + '\'
    if ($Full -ne $ProjectsRoot -and -not $Full.StartsWith($Prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "AGNIX_PATH_OUTSIDE_PROJECTS: $Name=$Full"
    }

    $Probe = $Full
    while (-not [string]::IsNullOrWhiteSpace($Probe)) {
        if (Test-Path -LiteralPath $Probe) {
            $Item = Get-Item -LiteralPath $Probe -Force
            if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "AGNIX_PATH_REPARSE_POINT: $Name traverses $Probe"
            }
        }
        if ($Probe -eq $ProjectsRoot) {
            break
        }
        $Parent = Split-Path -Parent $Probe
        if ([string]::IsNullOrWhiteSpace($Parent) -or $Parent -eq $Probe) {
            break
        }
        $Probe = $Parent
    }
    return $Full
}

if ([string]$Settings.package -ne 'agnix' -or [string]$Settings.version -ne '0.45.0') {
    throw 'AGNIX_SETTINGS_INVALID: package and exact version must be agnix@0.45.0.'
}

$InstallRoot = Assert-InProjects ([string]$Settings.install_root) 'install_root'
$CacheRoot = Assert-InProjects ([string]$Settings.npm_cache_root) 'npm_cache_root'
$TempRoot = Assert-InProjects ([string]$Settings.temp_root) 'temp_root'
$QuarantineRoot = Assert-InProjects ([string]$Settings.quarantine_root) 'quarantine_root'

$Node = Get-Command 'node.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
$Npm = Get-Command 'npm.cmd' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $Node -or $null -eq $Npm) {
    throw 'AGNIX_PREREQUISITE_MISSING: node.exe and npm.cmd are required.'
}
$NodeVersion = (& $Node.Source --version).Trim()
if ($LASTEXITCODE -ne 0 -or $NodeVersion -notmatch '^v(?<major>\d+)\.' -or [int]$Matches.major -lt 18) {
    throw "AGNIX_NODE_UNSUPPORTED: found $NodeVersion; Node.js 18 or newer is required."
}

foreach ($Path in @($CacheRoot, $TempRoot, $QuarantineRoot, (Split-Path -Parent $InstallRoot))) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}
$StageId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$StagingInstallRoot = Assert-InProjects (Join-Path $TempRoot "agnix-package-$StageId") 'staging_install_root'
New-Item -ItemType Directory -Path $StagingInstallRoot -Force | Out-Null

$env:NPM_CONFIG_CACHE = $CacheRoot
$env:NPM_CONFIG_AUDIT = 'false'
$env:NPM_CONFIG_FUND = 'false'
$env:NPM_CONFIG_UPDATE_NOTIFIER = 'false'
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:HOME = 'C:\Projects\.kis-mcp'
$env:USERPROFILE = 'C:\Projects\.kis-mcp'

$PackageSpec = "$($Settings.package)@$($Settings.version)"
Write-Host "Staging $PackageSpec at $StagingInstallRoot..."
& $Npm.Source install --prefix $StagingInstallRoot $PackageSpec --save-exact --no-audit --no-fund
if ($LASTEXITCODE -ne 0) {
    throw "AGNIX_PACKAGE_INSTALL_FAILED: npm exited with code $LASTEXITCODE."
}

$PackageJsonPath = Join-Path $StagingInstallRoot 'node_modules\agnix\package.json'
$CommandPath = Join-Path $StagingInstallRoot 'node_modules\.bin\agnix.cmd'
if (-not (Test-Path -LiteralPath $PackageJsonPath -PathType Leaf) -or -not (Test-Path -LiteralPath $CommandPath -PathType Leaf)) {
    throw 'AGNIX_PACKAGE_INVALID: package metadata or command entrypoint is missing.'
}
$PackageJson = Get-Content -LiteralPath $PackageJsonPath -Raw | ConvertFrom-Json
if ([string]$PackageJson.name -ne 'agnix' -or [string]$PackageJson.version -ne '0.45.0') {
    throw "AGNIX_IDENTITY_MISMATCH: installed $($PackageJson.name)@$($PackageJson.version)."
}

$VersionOutput = (& $CommandPath --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $VersionOutput -notmatch '0\.45\.0') {
    throw "AGNIX_SMOKE_FAILED: unexpected version output '$VersionOutput'."
}

$OperationId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$OperationQuarantine = Join-Path $QuarantineRoot $OperationId
New-Item -ItemType Directory -Path $OperationQuarantine -Force | Out-Null
$FinalCommandPath = Join-Path $InstallRoot 'node_modules\.bin\agnix.cmd'

$Status = [ordered]@{
    schema_version = 1
    tool_id = 'agnix'
    version = [string]$PackageJson.version
    installed_at = [DateTimeOffset]::UtcNow.ToString('o')
    install_root = $InstallRoot
    command = $FinalCommandPath
    version_output = $VersionOutput
    mcp_entrypoint = $null
    mcp_status = 'not_in_npm_distribution'
    kis_mcp_exposure = $Settings.kis_mcp_exposure
    previous_state_quarantine = $OperationQuarantine
}
$StatusPath = Join-Path $StagingInstallRoot 'installation.json'
$StatusJson = ($Status | ConvertTo-Json -Depth 6) + [Environment]::NewLine
[System.IO.File]::WriteAllText($StatusPath, $StatusJson, (New-Object System.Text.UTF8Encoding($false)))

$PreviousInstall = $null
$InstallActivated = $false
try {
    if (Test-Path -LiteralPath $InstallRoot) {
        $PreviousInstallDestination = Join-Path $OperationQuarantine 'previous-package'
        Move-Item -LiteralPath $InstallRoot -Destination $PreviousInstallDestination
        $PreviousInstall = $PreviousInstallDestination
    }
    Move-Item -LiteralPath $StagingInstallRoot -Destination $InstallRoot
    $InstallActivated = $true
}
catch {
    $ActivationMessage = $_.Exception.Message
    $RollbackErrors = @()
    if ($InstallActivated -and (Test-Path -LiteralPath $InstallRoot)) {
        try { Move-Item -LiteralPath $InstallRoot -Destination (Join-Path $OperationQuarantine 'failed-new-package') }
        catch { $RollbackErrors += "new package: $($_.Exception.Message)" }
    }
    if ($null -ne $PreviousInstall -and -not (Test-Path -LiteralPath $InstallRoot)) {
        try { Move-Item -LiteralPath $PreviousInstall -Destination $InstallRoot }
        catch { $RollbackErrors += "previous package: $($_.Exception.Message)" }
    }
    $RollbackDetail = if ($RollbackErrors.Count -gt 0) { '; rollback errors: ' + ($RollbackErrors -join ' | ') } else { '' }
    throw "AGNIX_ACTIVATION_FAILED: $ActivationMessage$RollbackDetail"
}

$Status | ConvertTo-Json -Depth 6
