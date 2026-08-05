$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'

Push-Location $RepositoryRoot
try {
    & $Python -m pytest `
        tests/providers/nvidia `
        tests/providers/test_platform_composition.py `
        tests/tools/codex_cli `
        tests/workflows/code_review `
        tests/control_center `
        tests/providers/github `
        tests/providers/supabase `
        tests/architecture `
        -q
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
