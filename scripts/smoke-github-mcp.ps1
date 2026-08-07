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
    & uv run --offline --no-sync python -m pytest tests/providers/github tests/providers/test_client_runtime.py tests/repositories -q
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub provider focused tests failed with exit code $LASTEXITCODE"
    }

    $ProviderSettingsPath = Join-Path $RepositoryRoot 'settings\providers\github-mcp.provider.json'
    $ProviderSettings = Get-Content -LiteralPath $ProviderSettingsPath -Raw | ConvertFrom-Json
    if ($ProviderSettings.auth_mode -ne 'oauth') {
        throw 'GITHUB_MCP_SETTINGS_INVALID: auth_mode must be oauth.'
    }
    if ($ProviderSettings.schema_version -ne 3) {
        throw 'GITHUB_MCP_SETTINGS_INVALID: schema_version must be 3.'
    }
    if ($null -ne $ProviderSettings.approved_repositories -or $null -ne $ProviderSettings.approved_projects) {
        throw 'GITHUB_MCP_SETTINGS_INVALID: repository and Project bindings must not be provider authentication settings.'
    }

    $RepositorySettingsPath = Join-Path $RepositoryRoot 'settings\kis-repository.settings.json'
    $RepositorySettings = Get-Content -LiteralPath $RepositorySettingsPath -Raw | ConvertFrom-Json
    if ($RepositorySettings.schema_version -ne 1) {
        throw 'KIS_REPOSITORY_SETTINGS_INVALID: schema_version must be 1.'
    }
    if ([string]::IsNullOrWhiteSpace([string]$RepositorySettings.github_repository)) {
        throw 'KIS_REPOSITORY_SETTINGS_INVALID: github_repository is required.'
    }

    $ExecutablePresent = Test-Path -LiteralPath ([string]$ProviderSettings.executable) -PathType Leaf
    $PatPresent = -not [string]::IsNullOrWhiteSpace(
        [Environment]::GetEnvironmentVariable([string]$ProviderSettings.pat_env)
    )

    $LiveReport = $null
    if ($RequireLive) {
        if (-not $ExecutablePresent) {
            throw 'GITHUB_MCP_EXECUTABLE_MISSING: run scripts/install-github-mcp.ps1 first.'
        }
        if ($PatPresent) {
            throw "GITHUB_OAUTH_PAT_CONFLICT: clear $($ProviderSettings.pat_env) before interactive OAuth commissioning."
        }
        $LiveReportJson = & uv run --offline --no-sync python scripts/run-provider-live-smoke.py github
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub MCP live smoke failed with exit code $LASTEXITCODE"
        }
        $LiveReport = $LiveReportJson | ConvertFrom-Json
    }

    [pscustomobject]@{
        provider = $ProviderSettings.provider_id
        release_tag = $ProviderSettings.release_tag
        source_revision = $ProviderSettings.source_revision
        auth_mode = $ProviderSettings.auth_mode
        client_lifetime = 'runtime'
        authentication_bootstrap = 'get_me'
        executable_present = $ExecutablePresent
        pat_override_present = $PatPresent
        selected_repository = $RepositorySettings.github_repository
        gh_projects = @($RepositorySettings.gh_projects)
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
