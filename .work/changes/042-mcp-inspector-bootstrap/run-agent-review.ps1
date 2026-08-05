$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$InstallSettings = Get-Content -LiteralPath (Join-Path $RepositoryRoot 'settings\bootstrap\mcp-inspector.install.json') -Raw | ConvertFrom-Json
$KisSettings = Get-Content -LiteralPath (Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json') -Raw | ConvertFrom-Json
$InstanceSettings = $KisSettings.remote_mcp.instances.development
$InstallRoot = [string]$InstallSettings.install_root
$LauncherPath = Join-Path $InstallRoot ([string]$InstallSettings.launcher_entry_point)
$ManagedHome = Join-Path ([string]$InstallSettings.managed_home) 'development'
$StorageRoot = Join-Path $ManagedHome 'storage'
$LogRoot = Join-Path ([string]$InstallSettings.log_root) 'development'

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
$env:MCP_LOG_FILE = Join-Path $LogRoot 'agent-review.log'

$Git = (Get-Command 'git.exe' -CommandType Application | Select-Object -First 1).Source
$BaseSha = (& $Git -C $RepositoryRoot merge-base main HEAD).Trim()
$HeadSha = (& $Git -C $RepositoryRoot rev-parse HEAD).Trim()
$ReviewInstructions = @"
Review the change from base $BaseSha to head $HeadSha against .work/changes/042-mcp-inspector-bootstrap/spec.md and plan.md. Focus on correctness, security, path containment, exact dependency pinning, npm staging, smoke-before-activation ordering, quarantine and rollback behavior, PowerShell failure modes, launcher instance selection, local-only binding, runtime state containment, truthful documentation, tests, and unnecessary gateway or policy surface. Report only actionable findings, classified Critical, Important, or Minor. Explicitly state when no blocking findings remain. Do not modify the repository.
"@
$Arguments = [ordered]@{
    path = $RepositoryRoot
    instructions = $ReviewInstructions
} | ConvertTo-Json -Compress

$ServerUrl = "http://$($KisSettings.remote_mcp.host):$([int]$InstanceSettings.port)$($KisSettings.remote_mcp.path)"
$Node = Get-Command 'node.exe' -CommandType Application | Select-Object -First 1
& $Node.Source $LauncherPath --cli --server-url $ServerUrl --transport http --method tools/call --tool-name review_change_with_agent --tool-args-json $Arguments --format json --connect-timeout 10000
exit $LASTEXITCODE
