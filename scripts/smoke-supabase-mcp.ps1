[CmdletBinding()]
param(
    [switch]$Live,
    [switch]$SharedRuntime
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'SUPABASE_MCP_PYTHON_NOT_FOUND: run scripts\bootstrap-python.ps1 first.'
}
if ($Live -and $SharedRuntime) {
    throw 'SUPABASE_MCP_SMOKE_MODE_INVALID: choose -Live or -SharedRuntime, not both.'
}
if (($Live -or $SharedRuntime) -and [string]::IsNullOrWhiteSpace($env:SUPABASE_PROJECT_REF)) {
    throw 'SUPABASE_PROJECT_SCOPE_REQUIRED: set SUPABASE_PROJECT_REF to one development or test project.'
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
