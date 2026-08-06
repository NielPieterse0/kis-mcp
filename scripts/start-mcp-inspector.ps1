param(
    [ValidateSet('operation', 'development')]
    [string]$Instance = 'development',
    [switch]$NoBrowser,
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$InstallSettingsPath = Join-Path $RepositoryRoot 'settings\bootstrap\mcp-inspector.install.json'
$KisSettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$InstallSettings = Get-Content -LiteralPath $InstallSettingsPath -Raw | ConvertFrom-Json
$KisSettings = Get-Content -LiteralPath $KisSettingsPath -Raw | ConvertFrom-Json
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

if ([string]$InstallSettings.package -ne '@modelcontextprotocol/inspector' -or
    [string]$InstallSettings.version -ne '2.0.0' -or
    [bool]$InstallSettings.kis_mcp_exposure.enabled) {
    throw 'MCP_INSPECTOR_SETTINGS_INVALID: expected a disabled @modelcontextprotocol/inspector@2.0.0 installation.'
}

$InstallRoot = Assert-InProjects ([string]$InstallSettings.install_root) 'install_root'
$ManagedHome = Assert-InProjects ([string]$InstallSettings.managed_home) 'managed_home'
$CacheRoot = Assert-InProjects ([string]$InstallSettings.npm_cache_root) 'npm_cache_root'
$TempRoot = Assert-InProjects ([string]$InstallSettings.temp_root) 'temp_root'
$LogRoot = Assert-InProjects ([string]$InstallSettings.log_root) 'log_root'
$LauncherPath = Assert-InProjects (Join-Path $InstallRoot ([string]$InstallSettings.launcher_entry_point)) 'launcher_path'
$PackageJsonPath = Assert-InProjects (Join-Path $InstallRoot 'node_modules\@modelcontextprotocol\inspector\package.json') 'package_json'
$InstallationStatusPath = Assert-InProjects (Join-Path $InstallRoot 'installation.json') 'installation_status'

foreach ($RequiredFile in @($LauncherPath, $PackageJsonPath, $InstallationStatusPath)) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) {
        throw "MCP_INSPECTOR_NOT_INSTALLED: missing $RequiredFile. Run scripts\install-mcp-inspector.ps1 first."
    }
}

$PackageJson = Get-Content -LiteralPath $PackageJsonPath -Raw | ConvertFrom-Json
$InstallationStatus = Get-Content -LiteralPath $InstallationStatusPath -Raw | ConvertFrom-Json
if ([string]$PackageJson.name -ne '@modelcontextprotocol/inspector' -or
    [string]$PackageJson.version -ne '2.0.0' -or
    [string]$InstallationStatus.package -ne '@modelcontextprotocol/inspector' -or
    [string]$InstallationStatus.version -ne '2.0.0') {
    throw 'MCP_INSPECTOR_IDENTITY_MISMATCH: managed package or installation status is not @modelcontextprotocol/inspector@2.0.0.'
}

$InstanceProperty = $KisSettings.remote_mcp.instances.PSObject.Properties[$Instance]
if ($null -eq $InstanceProperty) {
    throw "MCP_INSPECTOR_INSTANCE_UNKNOWN: $Instance"
}
$InstanceSettings = $InstanceProperty.Value
if (-not [bool]$InstanceSettings.configured) {
    throw "MCP_INSPECTOR_INSTANCE_NOT_CONFIGURED: kis-mcp instance '$Instance' is not configured."
}

$HostValue = [string]$KisSettings.remote_mcp.host
if ($HostValue -ne '127.0.0.1') {
    throw "MCP_INSPECTOR_HOST_INVALID: expected kis-mcp remote_mcp.host 127.0.0.1, received '$HostValue'."
}
$McpPath = [string]$KisSettings.remote_mcp.path
if ([string]::IsNullOrWhiteSpace($McpPath) -or -not $McpPath.StartsWith('/')) {
    throw "MCP_INSPECTOR_PATH_INVALID: remote_mcp.path must begin with '/'."
}
$TargetPort = [int]$InstanceSettings.port
if ($TargetPort -lt 1 -or $TargetPort -gt 65535) {
    throw "MCP_INSPECTOR_TARGET_PORT_INVALID: $TargetPort"
}
$WebPortProperty = $InstallSettings.web_ports.PSObject.Properties[$Instance]
if ($null -eq $WebPortProperty) {
    throw "MCP_INSPECTOR_WEB_PORT_MISSING: $Instance"
}
$WebPort = [int]$WebPortProperty.Value
if ($WebPort -lt 1 -or $WebPort -gt 65535 -or $WebPort -eq $TargetPort) {
    throw "MCP_INSPECTOR_WEB_PORT_INVALID: $WebPort"
}

$Node = Get-Command 'node.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $Node) {
    throw 'MCP_INSPECTOR_PREREQUISITE_MISSING: node.exe is required.'
}

$InstanceHome = Assert-InProjects (Join-Path $ManagedHome $Instance) 'instance_home'
$StorageRoot = Assert-InProjects (Join-Path $InstanceHome 'storage') 'storage_root'
$InstanceLogRoot = Assert-InProjects (Join-Path $LogRoot $Instance) 'instance_log_root'
foreach ($Path in @($InstanceHome, $StorageRoot, $InstanceLogRoot, $CacheRoot, $TempRoot)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$env:HOME = $InstanceHome
$env:USERPROFILE = $InstanceHome
$env:APPDATA = Join-Path $InstanceHome 'AppData\Roaming'
$env:LOCALAPPDATA = Join-Path $InstanceHome 'AppData\Local'
$env:XDG_CONFIG_HOME = Join-Path $InstanceHome '.config'
$env:NPM_CONFIG_CACHE = $CacheRoot
$env:NPM_CONFIG_AUDIT = 'false'
$env:NPM_CONFIG_FUND = 'false'
$env:NPM_CONFIG_UPDATE_NOTIFIER = 'false'
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:HOST = '127.0.0.1'
$env:CLIENT_PORT = [string]$WebPort
$env:MCP_STORAGE_DIR = $StorageRoot
$env:MCP_LOG_FILE = Join-Path $InstanceLogRoot 'inspector.log'
$env:MCP_AUTO_OPEN_ENABLED = if ($NoBrowser) { 'false' } else { 'true' }
foreach ($Path in @($env:APPDATA, $env:LOCALAPPDATA, $env:XDG_CONFIG_HOME)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$ServerUrl = "http://${HostValue}:$TargetPort$McpPath"
Write-Host "Starting MCP Inspector for kis-mcp '$Instance'."
Write-Host "Inspector UI: http://127.0.0.1:$WebPort"
Write-Host "MCP target: $ServerUrl"

& $Node.Source $LauncherPath --web --server-url $ServerUrl --transport 'http'
exit $LASTEXITCODE
