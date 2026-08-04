$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$python = "C:\Projects\.kis-mcp\python-env\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $repositoryRoot "src"

& $python -m pytest `
    (Join-Path $repositoryRoot "tests\discover\test_change_tool_registration.py") `
    (Join-Path $repositoryRoot "tests\discover\test_tool_registration.py") `
    -q `
    --no-header
exit $LASTEXITCODE
