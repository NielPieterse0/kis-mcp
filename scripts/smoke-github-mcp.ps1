param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$RequireLive
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:PYTEST_ADDOPTS = "-o cache_dir=$(Join-Path $StateRoot 'pytest-cache')"
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
$env:UV_OFFLINE = '1'

Push-Location $RepositoryRoot
try {
    & uv run --offline --no-sync python -m pytest tests/providers/github -q
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub provider focused tests failed with exit code $LASTEXITCODE"
    }

    $SettingsPath = Join-Path $RepositoryRoot 'settings\providers\github-mcp.provider.json'
    $Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
    if ($Settings.auth_mode -ne 'oauth') {
        throw 'GITHUB_MCP_SETTINGS_INVALID: auth_mode must be oauth.'
    }
    $ExecutablePresent = Test-Path -LiteralPath ([string]$Settings.executable) -PathType Leaf
    $PatPresent = -not [string]::IsNullOrWhiteSpace(
        [Environment]::GetEnvironmentVariable([string]$Settings.pat_env)
    )

    $LiveReport = $null
    if ($RequireLive) {
        if (-not $ExecutablePresent) {
            throw 'GITHUB_MCP_EXECUTABLE_MISSING: run scripts/install-github-mcp.ps1 first.'
        }
        if ($PatPresent) {
            throw "GITHUB_OAUTH_PAT_CONFLICT: clear $($Settings.pat_env) before interactive OAuth commissioning."
        }
        $LiveReportJson = & uv run --offline --no-sync python -m kis_mcp.providers.github.smoke
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub MCP live smoke failed with exit code $LASTEXITCODE"
        }
        $LiveReport = $LiveReportJson | ConvertFrom-Json
    }

    [pscustomobject]@{
        provider = $Settings.provider_id
        release_tag = $Settings.release_tag
        source_revision = $Settings.source_revision
        auth_mode = $Settings.auth_mode
        executable_present = $ExecutablePresent
        pat_override_present = $PatPresent
        approved_repositories = @($Settings.approved_repositories)
        focused_tests = 'passed'
        live_required = [bool]$RequireLive
        live_ready = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.ready }
        live_mounted = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.mounted }
        live_surface = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.surface }
        live_authentication = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.authentication }
        live_private_repository_read = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.private_repository_read }
        live_repository_scope = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.repository_scope }
    }
}
finally {
    Pop-Location
}
