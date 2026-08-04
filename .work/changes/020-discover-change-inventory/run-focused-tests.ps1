$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:PYTEST_ADDOPTS = '--cache-clear -p no:cacheprovider'
$env:TEMP = Join-Path $StateRoot 'temp'
$env:TMP = Join-Path $StateRoot 'temp'
$env:UV_OFFLINE = '1'

Push-Location $RepositoryRoot
try {
    & uv run --offline --no-sync python -m pytest @args
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
