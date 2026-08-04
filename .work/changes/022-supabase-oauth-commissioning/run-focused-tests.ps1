param(
    [Parameter(Mandatory = $true)]
    [string[]]$Tests
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:PYTEST_ADDOPTS = "-o cache_dir=$(Join-Path $StateRoot 'pytest-cache')"
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
$env:UV_OFFLINE = '1'

Push-Location $RepositoryRoot
try {
    & uv run --offline --no-sync python -m pytest @Tests -q
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
