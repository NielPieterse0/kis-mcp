$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$CanonicalStateRoot = 'C:\Projects\.kis-mcp'
$PythonExecutable = Join-Path $CanonicalStateRoot 'python-env\Scripts\python.exe'
$TempRoot = Join-Path $CanonicalStateRoot 'temp'
$UvCacheRoot = Join-Path $CanonicalStateRoot 'uv-cache'
$PythonCacheRoot = Join-Path $CanonicalStateRoot 'python-cache'
$TestNode = 'tests/integration/test_live_proxy_commissioning.py::test_live_proxy_commissioning'

if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw "PYTHON_ENVIRONMENT_NOT_READY: expected $PythonExecutable"
}

foreach ($Path in @($TempRoot, $UvCacheRoot, $PythonCacheRoot)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$env:KIS_MCP_LIVE_COMMISSION = '1'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $CanonicalStateRoot 'python-env'
$env:UV_CACHE_DIR = $UvCacheRoot
$env:PYTHONPYCACHEPREFIX = $PythonCacheRoot
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
$env:NO_UPDATE_NOTIFIER = '1'

Push-Location $RepositoryRoot
try {
    & $PythonExecutable -m pytest $TestNode -q -s
    if ($LASTEXITCODE -ne 0) {
        throw "Live proxy commissioning failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
