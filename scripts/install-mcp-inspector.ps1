param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$SettingsPath = Join-Path $RepositoryRoot 'settings\bootstrap\mcp-inspector.install.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$ProjectsRoot = [System.IO.Path]::GetFullPath('C:\Projects')

function Assert-InProjects([string]$Path, [string]$Name) {
    $Full = [System.IO.Path]::GetFullPath($Path)
    $Prefix = $ProjectsRoot.TrimEnd('\') + '\'
    if ($Full -ne $ProjectsRoot -and -not $Full.StartsWith($Prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "MCP_INSPECTOR_PATH_OUTSIDE_PROJECTS: $Name=$Full"
    }

    $Probe = $Full
    while (-not [string]::IsNullOrWhiteSpace($Probe)) {
        if (Test-Path -LiteralPath $Probe) {
            $Item = Get-Item -LiteralPath $Probe -Force
            if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "MCP_INSPECTOR_PATH_REPARSE_POINT: $Name traverses $Probe"
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

function Convert-SemanticVersion([string]$Value, [string]$Name) {
    $Normalized = $Value.Trim().TrimStart('v')
    if ($Normalized -notmatch '^(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)(?:[-+].*)?$') {
        throw "MCP_INSPECTOR_VERSION_INVALID: $Name=$Value"
    }
    return [Version]::new([int]$Matches.major, [int]$Matches.minor, [int]$Matches.patch)
}

if ([int]$Settings.schema_version -ne 1 -or [string]$Settings.tool_id -ne 'mcp-inspector') {
    throw 'MCP_INSPECTOR_SETTINGS_INVALID: schema_version and tool_id are invalid.'
}
if ([string]$Settings.package -ne '@modelcontextprotocol/inspector' -or [string]$Settings.version -ne '2.0.0') {
    throw 'MCP_INSPECTOR_SETTINGS_INVALID: package and exact version must be @modelcontextprotocol/inspector@2.0.0.'
}
if ([string]$Settings.minimum_node_version -ne '22.19.0') {
    throw 'MCP_INSPECTOR_SETTINGS_INVALID: minimum_node_version must be 22.19.0.'
}
if ([string]$Settings.launcher_entry_point -ne 'node_modules\@modelcontextprotocol\inspector\clients\launcher\build\index.js') {
    throw 'MCP_INSPECTOR_SETTINGS_INVALID: launcher_entry_point must target clients\launcher\build\index.js.'
}
if ([bool]$Settings.kis_mcp_exposure.enabled) {
    throw 'MCP_INSPECTOR_EXPOSURE_INVALID: kis_mcp_exposure.enabled must remain false.'
}
$OperationWebPort = [int]$Settings.web_ports.operation
$DevelopmentWebPort = [int]$Settings.web_ports.development
if ($OperationWebPort -lt 1 -or $OperationWebPort -gt 65535 -or
    $DevelopmentWebPort -lt 1 -or $DevelopmentWebPort -gt 65535 -or
    $OperationWebPort -eq $DevelopmentWebPort) {
    throw 'MCP_INSPECTOR_WEB_PORTS_INVALID: operation and development ports must be distinct values in 1-65535.'
}

$InstallRoot = Assert-InProjects ([string]$Settings.install_root) 'install_root'
$ManagedHome = Assert-InProjects ([string]$Settings.managed_home) 'managed_home'
$CacheRoot = Assert-InProjects ([string]$Settings.npm_cache_root) 'npm_cache_root'
$TempRoot = Assert-InProjects ([string]$Settings.temp_root) 'temp_root'
$LogRoot = Assert-InProjects ([string]$Settings.log_root) 'log_root'
$QuarantineRoot = Assert-InProjects ([string]$Settings.quarantine_root) 'quarantine_root'

$Node = Get-Command 'node.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
$Npm = Get-Command 'npm.cmd' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $Node -or $null -eq $Npm) {
    throw 'MCP_INSPECTOR_PREREQUISITE_MISSING: node.exe and npm.cmd are required.'
}
$NodeVersionText = (& $Node.Source --version).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'MCP_INSPECTOR_NODE_VERSION_FAILED: node.exe --version failed.'
}
$NodeVersion = Convert-SemanticVersion $NodeVersionText 'node'
$MinimumNodeVersion = Convert-SemanticVersion ([string]$Settings.minimum_node_version) 'minimum_node_version'
if ($NodeVersion -lt $MinimumNodeVersion) {
    throw "MCP_INSPECTOR_NODE_UNSUPPORTED: found $NodeVersionText; Node.js $($Settings.minimum_node_version) or newer is required."
}

foreach ($Path in @(
    $ManagedHome,
    $CacheRoot,
    $TempRoot,
    $LogRoot,
    $QuarantineRoot,
    (Split-Path -Parent $InstallRoot)
)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$StageId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$StagingInstallRoot = Assert-InProjects (Join-Path $TempRoot "package-$StageId") 'staging_install_root'
$StagingHome = Assert-InProjects (Join-Path $TempRoot "home-$StageId") 'staging_home'
New-Item -ItemType Directory -Path $StagingInstallRoot, $StagingHome -Force | Out-Null

$env:HOME = $StagingHome
$env:USERPROFILE = $StagingHome
$env:APPDATA = Join-Path $StagingHome 'AppData\Roaming'
$env:LOCALAPPDATA = Join-Path $StagingHome 'AppData\Local'
$env:XDG_CONFIG_HOME = Join-Path $StagingHome '.config'
$env:NPM_CONFIG_CACHE = $CacheRoot
$env:NPM_CONFIG_AUDIT = 'false'
$env:NPM_CONFIG_FUND = 'false'
$env:NPM_CONFIG_UPDATE_NOTIFIER = 'false'
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
foreach ($Path in @($env:APPDATA, $env:LOCALAPPDATA, $env:XDG_CONFIG_HOME)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$PackageSpec = "$($Settings.package)@$($Settings.version)"
Write-Host "Staging $PackageSpec at $StagingInstallRoot..."
& $Npm.Source install --prefix $StagingInstallRoot $PackageSpec --save-exact --ignore-scripts --no-audit --no-fund
if ($LASTEXITCODE -ne 0) {
    throw "MCP_INSPECTOR_PACKAGE_INSTALL_FAILED: npm exited with code $LASTEXITCODE."
}

$PackageJsonPath = Join-Path $StagingInstallRoot 'node_modules\@modelcontextprotocol\inspector\package.json'
$StagingLauncher = Join-Path $StagingInstallRoot ([string]$Settings.launcher_entry_point)
if (-not (Test-Path -LiteralPath $PackageJsonPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $StagingLauncher -PathType Leaf)) {
    throw 'MCP_INSPECTOR_PACKAGE_INVALID: package metadata or clients\launcher\build\index.js is missing.'
}
$PackageJson = Get-Content -LiteralPath $PackageJsonPath -Raw | ConvertFrom-Json
if ([string]$PackageJson.name -ne '@modelcontextprotocol/inspector' -or [string]$PackageJson.version -ne '2.0.0') {
    throw "MCP_INSPECTOR_IDENTITY_MISMATCH: installed $($PackageJson.name)@$($PackageJson.version)."
}

& $Node.Source $StagingLauncher --cli --help
if ($LASTEXITCODE -ne 0) {
    throw "MCP_INSPECTOR_SMOKE_FAILED: CLI help exited with code $LASTEXITCODE."
}

$OperationId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$OperationQuarantine = Assert-InProjects (Join-Path $QuarantineRoot $OperationId) 'operation_quarantine'
New-Item -ItemType Directory -Path $OperationQuarantine -Force | Out-Null
$StagingHomeQuarantine = Join-Path $OperationQuarantine 'bootstrap-home'
Move-Item -LiteralPath $StagingHome -Destination $StagingHomeQuarantine

$Status = [ordered]@{
    schema_version = 1
    tool_id = 'mcp-inspector'
    package = [string]$PackageJson.name
    version = [string]$PackageJson.version
    installed_at = [DateTimeOffset]::UtcNow.ToString('o')
    install_root = $InstallRoot
    managed_home = $ManagedHome
    launcher_entry_point = [string]$Settings.launcher_entry_point
    node_version = $NodeVersionText
    smoke = 'cli_help_passed'
    kis_mcp_exposure = [ordered]@{
        enabled = $false
        namespace = [string]$Settings.kis_mcp_exposure.namespace
    }
    previous_state_quarantine = $OperationQuarantine
    bootstrap_home_quarantine = $StagingHomeQuarantine
}
$StatusPath = Join-Path $StagingInstallRoot 'installation.json'
$StatusJson = ($Status | ConvertTo-Json -Depth 8) + [Environment]::NewLine
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
        try {
            Move-Item -LiteralPath $InstallRoot -Destination (Join-Path $OperationQuarantine 'failed-new-package')
        }
        catch {
            $RollbackErrors += "new package: $($_.Exception.Message)"
        }
    }
    if ($null -ne $PreviousInstall -and -not (Test-Path -LiteralPath $InstallRoot)) {
        try {
            Move-Item -LiteralPath $PreviousInstall -Destination $InstallRoot
        }
        catch {
            $RollbackErrors += "previous package: $($_.Exception.Message)"
        }
    }
    $RollbackDetail = if ($RollbackErrors.Count -gt 0) { '; rollback errors: ' + ($RollbackErrors -join ' | ') } else { '' }
    throw "MCP_INSPECTOR_ACTIVATION_FAILED: $ActivationMessage$RollbackDetail"
}

$Status | ConvertTo-Json -Depth 8
