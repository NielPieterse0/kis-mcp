$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:UV_OFFLINE = '1'
Push-Location $RepositoryRoot
try {
    & uv run --offline python -m pytest @args
    if ($LASTEXITCODE -ne 0) { throw "Focused tests failed with exit code $LASTEXITCODE" }
}
finally { Pop-Location }
