$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'runtime-authority.ps1')
$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$RuntimeAuthority = Get-KisMcpRuntimeAuthority
$PythonRuntime = Resolve-KisMcpSystemPython -Authority $RuntimeAuthority
$UvRuntime = Resolve-KisMcpUvRuntime -Authority $RuntimeAuthority

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
$ExistingPython = Join-Path $PythonEnvironmentRoot 'Scripts\python.exe'
if (Test-Path -LiteralPath $ExistingPython -PathType Leaf) {
    $ExistingBase = (& $ExistingPython -c 'import sys; print(sys.base_prefix)').Trim()
    $RequiredBase = (& $PythonRuntime.executable -c 'import sys; print(sys.base_prefix)').Trim()
    if ($LASTEXITCODE -ne 0 -or $ExistingBase -ne $RequiredBase) {
        $OperationId = 'bootstrap-python-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
        $QuarantineRoot = Join-Path $CanonicalStateRoot "quarantine\$OperationId"
        New-Item -ItemType Directory -Path $QuarantineRoot -Force | Out-Null
        Move-Item -LiteralPath $PythonEnvironmentRoot -Destination (Join-Path $QuarantineRoot 'python-env')
        New-Item -ItemType Directory -Path $PythonEnvironmentRoot -Force | Out-Null
        Write-Host "Quarantined incompatible Python environment: $ExistingBase"
    }
}
$env:UV_PROJECT_ENVIRONMENT = $PythonEnvironmentRoot
$env:UV_CACHE_DIR = $UvCacheRoot
$env:PYTHONPYCACHEPREFIX = $PythonCacheRoot
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:NO_UPDATE_NOTIFIER = '1'
$env:UV_NO_MANAGED_PYTHON = '1'

Push-Location $RepositoryRoot
try {
    Write-Host "Using verified shared-system Python: $($PythonRuntime.executable)"
    Write-Host "Using supervised uv bootstrap tool: $($UvRuntime.executable)"
    Write-Host 'Resolving and locking the pinned Python dependency graph...'
    & $UvRuntime.executable lock --python $PythonRuntime.executable --no-managed-python
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency lock generation failed with exit code $LASTEXITCODE"
    }

    Write-Host 'Synchronizing the external project environment from uv.lock...'
    & $UvRuntime.executable sync --dev --frozen --python $PythonRuntime.executable --no-managed-python
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency synchronization failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "Python environment prepared at $PythonEnvironmentRoot"
Write-Host 'Run scripts\verify.ps1 before startup.'
