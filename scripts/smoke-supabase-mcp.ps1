[CmdletBinding()]
param(
    [switch]$Live,
    [switch]$SharedRuntime
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
$RegistryPath = Join-Path $RepositoryRoot 'settings\projects.settings.json'

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'SUPABASE_MCP_PYTHON_NOT_FOUND: run scripts\bootstrap-python.ps1 first.'
}
if ($Live -and $SharedRuntime) {
    throw 'SUPABASE_MCP_SMOKE_MODE_INVALID: choose -Live or -SharedRuntime, not both.'
}
$Registry = Get-Content -LiteralPath $RegistryPath -Raw | ConvertFrom-Json
if ($Registry.schema_version -ne 1) {
    throw 'KIS_PROJECT_REGISTRY_INVALID: schema_version must be 1.'
}
$Project = @($Registry.projects | Where-Object { $_.project_id -eq $Registry.default_project_id })
if (($Live -or $SharedRuntime) -and (
    $Project.Count -ne 1 -or
    [string]::IsNullOrWhiteSpace([string]$Project[0].supabase.project_ref)
)) {
    throw 'KIS_PROJECT_REGISTRY_INVALID: default project requires one Supabase binding.'
}
if (($Live -or $SharedRuntime) -and -not [string]::IsNullOrWhiteSpace($env:SUPABASE_ACCESS_TOKEN)) {
    throw 'SUPABASE_LEGACY_PAT_CONFLICT: clear SUPABASE_ACCESS_TOKEN before OAuth verification.'
}

$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
    if ($SharedRuntime) {
        & $Python scripts/run-provider-live-smoke.py supabase
        $FailureCode = 'SUPABASE_MCP_SHARED_SMOKE_FAILED'
    }
    elseif ($Live) {
        & $Python -m kis_mcp.providers.supabase.commission
        $FailureCode = 'SUPABASE_MCP_LIVE_SMOKE_FAILED'
    }
    else {
        & $Python -m kis_mcp.providers.supabase --check
        $FailureCode = 'SUPABASE_MCP_CHECK_FAILED'
    }
    if ($LASTEXITCODE -ne 0) {
        throw "${FailureCode}: Supabase MCP smoke exited with $LASTEXITCODE."
    }
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
