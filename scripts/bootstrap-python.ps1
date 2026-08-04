$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json

$CanonicalStateRoot = 'C:\Projects\.kis-mcp'
$PythonEnvironmentRoot = Join-Path $CanonicalStateRoot 'python-env'
$UvCacheRoot = Join-Path $CanonicalStateRoot 'uv-cache'
$PythonCacheRoot = Join-Path $CanonicalStateRoot 'python-cache'
$TempRoot = Join-Path $CanonicalStateRoot 'temp'

$ExpectedPaths = [ordered]@{
    state_root = $CanonicalStateRoot
    python_environment_root = $PythonEnvironmentRoot
    uv_cache_root = $UvCacheRoot
    python_cache_root = $PythonCacheRoot
    temp_root = $TempRoot
}
foreach ($Key in $ExpectedPaths.Keys) {
    if ([string]$Settings.paths.$Key -ne [string]$ExpectedPaths[$Key]) {
        throw "Canonical bootstrap path differs for $Key."
    }
}

foreach ($Path in $ExpectedPaths.Values) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}
$env:UV_PROJECT_ENVIRONMENT = $PythonEnvironmentRoot
$env:UV_CACHE_DIR = $UvCacheRoot
$env:PYTHONPYCACHEPREFIX = $PythonCacheRoot
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:NO_UPDATE_NOTIFIER = '1'

Push-Location $RepositoryRoot
try {
    Write-Host 'Resolving and locking the pinned Python dependency graph...'
    & uv lock
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency lock generation failed with exit code $LASTEXITCODE"
    }

    Write-Host 'Synchronizing the external project environment from uv.lock...'
    & uv sync --dev --frozen
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency synchronization failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "Python environment prepared at $PythonEnvironmentRoot"
Write-Host 'Run scripts\verify.ps1 before startup.'
