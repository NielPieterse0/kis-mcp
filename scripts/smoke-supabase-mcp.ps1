[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$Python = "C:\Projects\.kis-mcp\python-env\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "SUPABASE_MCP_PYTHON_NOT_FOUND: run scripts\bootstrap-python.ps1 first."
}

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $RepositoryRoot "src"
    & $Python -m kis_mcp.providers.supabase --check
    if ($LASTEXITCODE -ne 0) {
        throw "SUPABASE_MCP_CHECK_FAILED: provider readiness check exited with $LASTEXITCODE."
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}
