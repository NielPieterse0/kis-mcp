[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'SUPABASE_MCP_PYTHON_NOT_FOUND: run scripts\bootstrap-python.ps1 first.'
}
if ([string]::IsNullOrWhiteSpace($env:SUPABASE_PROJECT_REF)) {
    throw 'SUPABASE_PROJECT_SCOPE_REQUIRED: set SUPABASE_PROJECT_REF to one development or test project.'
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
