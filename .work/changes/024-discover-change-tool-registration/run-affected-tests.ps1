$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$python = "C:\Projects\.kis-mcp\python-env\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $repositoryRoot "src"

& $python -m pytest `
    (Join-Path $repositoryRoot "tests\discover") `
    -q `
    --no-header
exit $LASTEXITCODE
