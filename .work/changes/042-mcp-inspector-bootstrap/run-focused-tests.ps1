$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:TEMP = Join-Path $StateRoot 'temp'
$env:TMP = Join-Path $StateRoot 'temp'
$env:UV_OFFLINE = '1'

Push-Location $RepositoryRoot
try {
    & uv run --offline --no-sync pytest tests\bootstrap\test_mcp_inspector_install.py -q
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
