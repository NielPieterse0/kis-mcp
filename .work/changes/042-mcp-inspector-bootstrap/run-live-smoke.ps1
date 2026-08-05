param(
    [ValidateSet('operation', 'development')]
    [string]$Instance = 'development'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$InstallSettings = Get-Content -LiteralPath (Join-Path $RepositoryRoot 'settings\bootstrap\mcp-inspector.install.json') -Raw | ConvertFrom-Json
$KisSettings = Get-Content -LiteralPath (Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json') -Raw | ConvertFrom-Json
$InstanceSettings = $KisSettings.remote_mcp.instances.PSObject.Properties[$Instance].Value
$InstallRoot = [string]$InstallSettings.install_root
$LauncherPath = Join-Path $InstallRoot ([string]$InstallSettings.launcher_entry_point)
$ManagedHome = Join-Path ([string]$InstallSettings.managed_home) $Instance
$StorageRoot = Join-Path $ManagedHome 'storage'
$LogRoot = Join-Path ([string]$InstallSettings.log_root) $Instance

foreach ($Path in @($ManagedHome, $StorageRoot, $LogRoot, [string]$InstallSettings.npm_cache_root, [string]$InstallSettings.temp_root)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$env:HOME = $ManagedHome
$env:USERPROFILE = $ManagedHome
$env:APPDATA = Join-Path $ManagedHome 'AppData\Roaming'
$env:LOCALAPPDATA = Join-Path $ManagedHome 'AppData\Local'
$env:XDG_CONFIG_HOME = Join-Path $ManagedHome '.config'
$env:NPM_CONFIG_CACHE = [string]$InstallSettings.npm_cache_root
$env:TEMP = [string]$InstallSettings.temp_root
$env:TMP = [string]$InstallSettings.temp_root
$env:MCP_STORAGE_DIR = $StorageRoot
$env:MCP_LOG_FILE = Join-Path $LogRoot 'cli-smoke.log'

$ServerUrl = "http://$($KisSettings.remote_mcp.host):$([int]$InstanceSettings.port)$($KisSettings.remote_mcp.path)"
$Node = Get-Command 'node.exe' -CommandType Application | Select-Object -First 1
& $Node.Source $LauncherPath --cli --server-url $ServerUrl --transport http --method tools/list --format json --connect-timeout 10000
exit $LASTEXITCODE
