[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('operation','development')][string]$Instance,
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepositoryRoot = [IO.Path]::GetFullPath($RepositoryRoot)
$SettingsPath = Join-Path $RepositoryRoot 'settings\task-runtime.settings.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
if (-not [bool]$Settings.enabled) { throw 'KIS_MCP_TASK_RUNTIME_DISABLED' }
if ([string]$Settings.backend_url -notmatch '^redis://127\.0\.0\.1:\d+(/\d+)?$') {
    throw 'KIS_MCP_TASK_RUNTIME_BACKEND_INVALID'
}
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
if (-not [IO.File]::Exists($Python)) { throw "KIS_MCP_TASK_RUNTIME_PYTHON_MISSING: $Python" }
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
$env:KIS_MCP_RUNTIME_INSTANCE = $Instance
$env:KIS_MCP_TASK_ROLE = 'worker'
Set-Location $RepositoryRoot
& $Python -m kis_mcp.task_runtime --instance $Instance
if ($LASTEXITCODE -ne 0) { throw "KIS_MCP_TASK_WORKER_FAILED: exit=$LASTEXITCODE" }
