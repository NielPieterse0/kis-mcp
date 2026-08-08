[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
$RegistryPath = Join-Path $RepositoryRoot 'settings\projects.settings.json'

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'SUPABASE_MCP_PYTHON_NOT_FOUND: run scripts\bootstrap-python.ps1 first.'
}
$Registry = Get-Content -LiteralPath $RegistryPath -Raw | ConvertFrom-Json
if ($Registry.schema_version -ne 1) {
    throw 'KIS_PROJECT_REGISTRY_INVALID: schema_version must be 1.'
}
$Project = @($Registry.projects | Where-Object { $_.project_id -eq $Registry.default_project_id })
if ($Project.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$Project[0].supabase.project_ref)) {
    throw 'KIS_PROJECT_REGISTRY_INVALID: default project requires one Supabase binding.'
}
if (-not [string]::IsNullOrWhiteSpace($env:SUPABASE_ACCESS_TOKEN)) {
    throw 'SUPABASE_LEGACY_PAT_CONFLICT: clear SUPABASE_ACCESS_TOKEN before browser OAuth commissioning.'
}

$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
    & $Python -m kis_mcp.providers.supabase.commission
    if ($LASTEXITCODE -ne 0) {
        throw "SUPABASE_MCP_AUTH_FAILED: OAuth commissioning exited with $LASTEXITCODE."
    }
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
