$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$PolicyPath = Join-Path $RepositoryRoot 'policy\kis-mcp.policy.json'

$CanonicalStateRoot = 'C:\Projects\.kis-mcp'
$PythonEnvironmentRoot = Join-Path $CanonicalStateRoot 'python-env'
$PythonExecutable = Join-Path $PythonEnvironmentRoot 'Scripts\python.exe'
$UvCacheRoot = Join-Path $CanonicalStateRoot 'uv-cache'
$PythonCacheRoot = Join-Path $CanonicalStateRoot 'python-cache'
$TempRoot = Join-Path $CanonicalStateRoot 'temp'

$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$Policy = Get-Content -LiteralPath $PolicyPath -Raw | ConvertFrom-Json
$RuleIds = @($Policy.rules | ForEach-Object { [string]$_.id })
if ($RuleIds.Count -ne 3 -or ($RuleIds -join ',') -ne 'HR-001,HR-002,HR-003') {
    throw 'POLICY_RULE_SET_INVALID: policy must contain exactly HR-001, HR-002, and HR-003.'
}
if ([string]$Settings.paths.project_boundary -ne 'C:\Projects') {
    throw 'PROJECT_BOUNDARY_INVALID: the approved boundary is C:\Projects.'
}
if ([string]$Settings.paths.state_root -ne $CanonicalStateRoot) {
    throw "STATE_ROOT_INVALID: expected $CanonicalStateRoot"
}
if ([string]$Settings.paths.python_environment_root -ne $PythonEnvironmentRoot) {
    throw "PYTHON_ENVIRONMENT_INVALID: expected $PythonEnvironmentRoot"
}

$EntryPoint = [string]$Settings.desktop_commander.launch.args[0]
if (-not (Test-Path -LiteralPath $EntryPoint -PathType Leaf)) {
    throw "DESKTOP_COMMANDER_NOT_INSTALLED: $EntryPoint"
}
if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw "PYTHON_ENVIRONMENT_NOT_READY: run the supervised dependency bootstrap and scripts\verify.ps1. Expected $PythonExecutable"
}

foreach ($Path in @($UvCacheRoot, $PythonCacheRoot, $TempRoot)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}
$env:UV_PROJECT_ENVIRONMENT = $PythonEnvironmentRoot
$env:UV_CACHE_DIR = $UvCacheRoot
$env:PYTHONPYCACHEPREFIX = $PythonCacheRoot
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
$env:NO_UPDATE_NOTIFIER = '1'

Push-Location $RepositoryRoot
try {
    & $PythonExecutable -c "from pathlib import Path; from kis_mcp.config import load_runtime_config; load_runtime_config(Path.cwd())"
    if ($LASTEXITCODE -ne 0) {
        throw "kis-mcp configuration validation failed with exit code $LASTEXITCODE"
    }

    & $PythonExecutable -m kis_mcp
    if ($LASTEXITCODE -ne 0) {
        throw "kis-mcp exited with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
