$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json

$PythonEnvironmentRoot = [string]$Settings.paths.python_environment_root
$Python = Join-Path $PythonEnvironmentRoot 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'PYTHON_ENVIRONMENT_MISSING: run scripts\bootstrap-python.ps1 first.'
}

$env:PYTHONPYCACHEPREFIX = [string]$Settings.paths.python_cache_root
$env:TEMP = [string]$Settings.paths.temp_root
$env:TMP = [string]$Settings.paths.temp_root
$env:NO_UPDATE_NOTIFIER = '1'

Push-Location $RepositoryRoot
try {
    & $Python scripts\capture-provider-contract.py
    if ($LASTEXITCODE -ne 0) {
        throw "Provider contract capture failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
