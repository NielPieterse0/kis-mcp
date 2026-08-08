param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProviderSettingsPath = Join-Path $RepositoryRoot 'settings\providers\github-mcp.provider.json'
$ProviderSettings = Get-Content -LiteralPath $ProviderSettingsPath -Raw | ConvertFrom-Json
if ($ProviderSettings.auth_mode -ne 'oauth') {
    throw 'GITHUB_MCP_SETTINGS_INVALID: auth_mode must be oauth.'
}
$PatValue = [Environment]::GetEnvironmentVariable([string]$ProviderSettings.pat_env)
if (-not [string]::IsNullOrWhiteSpace($PatValue)) {
    throw "GITHUB_OAUTH_PAT_CONFLICT: clear $($ProviderSettings.pat_env) before interactive OAuth startup."
}
if (-not (Test-Path -LiteralPath ([string]$ProviderSettings.executable) -PathType Leaf)) {
    throw 'GITHUB_MCP_EXECUTABLE_MISSING: run scripts/install-github-mcp.ps1 first.'
}

$RegistryPath = Join-Path $RepositoryRoot 'settings\projects.settings.json'
$Registry = Get-Content -LiteralPath $RegistryPath -Raw | ConvertFrom-Json
if ($Registry.schema_version -ne 1 -or @($Registry.projects).Count -lt 1) {
    throw 'KIS_PROJECT_REGISTRY_INVALID: project registry must be schema version 1 and non-empty.'
}
$GitHubProjects = @($Registry.projects | Where-Object { $null -ne $_.github })
if ($GitHubProjects.Count -lt 1) {
    throw 'KIS_PROJECT_REGISTRY_INVALID: at least one registered GitHub repository is required.'
}

Write-Host 'GitHub OAuth is owned by the kis-op runtime.'
Write-Host 'Starting kis-op; complete the browser sign-in once and keep that runtime running to reuse the authenticated GitHub MCP process.'
Write-Host 'Stopping or restarting kis-op requires one new GitHub OAuth sign-in.'

& pwsh -NoProfile -File (Join-Path $PSScriptRoot 'start-chatgpt.ps1') -Instance operation
if ($LASTEXITCODE -ne 0) {
    throw "GITHUB_MCP_RUNTIME_START_FAILED: process exited with $LASTEXITCODE."
}
