param(
    [string[]]$Tests = @('tests/providers/github')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:PYTEST_ADDOPTS = "-o cache_dir=$(Join-Path $StateRoot 'pytest-cache')"
$env:UV_OFFLINE = '1'

& uv run --offline --no-sync python -m pytest @Tests -q
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
