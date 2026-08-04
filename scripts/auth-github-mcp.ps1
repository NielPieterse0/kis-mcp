param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$SettingsPath = Join-Path $RepositoryRoot 'settings\providers\github-mcp.provider.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
if ($Settings.auth_mode -ne 'oauth') {
    throw 'GITHUB_MCP_SETTINGS_INVALID: auth_mode must be oauth.'
}
$PatValue = [Environment]::GetEnvironmentVariable([string]$Settings.pat_env)
if (-not [string]::IsNullOrWhiteSpace($PatValue)) {
    throw "GITHUB_OAUTH_PAT_CONFLICT: clear $($Settings.pat_env) before interactive OAuth commissioning."
}
if (-not (Test-Path -LiteralPath ([string]$Settings.executable) -PathType Leaf)) {
    throw 'GITHUB_MCP_EXECUTABLE_MISSING: run scripts/install-github-mcp.ps1 first.'
}

$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:PYTEST_ADDOPTS = "-o cache_dir=$(Join-Path $StateRoot 'pytest-cache')"
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
$env:UV_OFFLINE = '1'

Push-Location $RepositoryRoot
try {
    & uv run --offline --no-sync python -m kis_mcp.providers.github.commission
    if ($LASTEXITCODE -ne 0) {
        throw "GITHUB_MCP_OAUTH_COMMISSIONING_FAILED: process exited with $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
