$ErrorActionPreference = 'Stop'
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "KIS_MCP_PYTHON_ENVIRONMENT_MISSING: $Python"
}
Set-Location -LiteralPath $RepositoryRoot
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
& $Python -m pytest `
    tests/workflows/code_review `
    tests/providers/nvidia `
    tests/providers/test_platform_composition.py `
    tests/tools/codex_cli `
    tests/test_llm_agent_registration.py `
    -q
exit $LASTEXITCODE
