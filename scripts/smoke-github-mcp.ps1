param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$RequireLive
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$StateRoot = 'C:\Projects\.kis-mcp'
$ExpectedTokenEnv = 'GITHUB_PERSONAL_ACCESS_TOKEN'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:PYTEST_ADDOPTS = "-o cache_dir=$(Join-Path $StateRoot 'pytest-cache')"
$env:UV_OFFLINE = '1'

Push-Location $RepositoryRoot
try {
    & uv run --offline --no-sync python -m pytest tests/providers/github -q
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub provider focused tests failed with exit code $LASTEXITCODE"
    }

    $SettingsPath = Join-Path $RepositoryRoot 'settings\providers\github-mcp.provider.json'
    $Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
    if ($Settings.token_env -ne $ExpectedTokenEnv) {
        throw "GitHub provider token environment does not match the approved name."
    }
    $ExecutablePresent = Test-Path -LiteralPath $Settings.executable -PathType Leaf
    $TokenPresent = -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Settings.token_env))

    $LiveReport = $null
    if ($RequireLive) {
        if (-not $ExecutablePresent) {
            throw "GitHub MCP executable is not installed at the configured path."
        }
        if (-not $TokenPresent) {
            throw "The configured GitHub token environment variable is not present."
        }
        $LiveReportJson = & uv run --offline --no-sync python -m kis_mcp.providers.github.smoke
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub MCP live smoke failed with exit code $LASTEXITCODE"
        }
        $LiveReport = $LiveReportJson | ConvertFrom-Json
    }

    [pscustomobject]@{
        provider = $Settings.provider_id
        source_revision = $Settings.source_revision
        executable_present = $ExecutablePresent
        token_present = $TokenPresent
        approved_repositories = @($Settings.approved_repositories)
        focused_tests = 'passed'
        live_required = [bool]$RequireLive
        live_ready = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.ready }
        live_surface = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.surface }
        live_authentication = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.authentication }
        live_private_repository_read = if ($null -eq $LiveReport) { $false } else { [bool]$LiveReport.private_repository_read }
    }
}
finally {
    Pop-Location
}
