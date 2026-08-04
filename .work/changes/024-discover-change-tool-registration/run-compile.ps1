$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$python = "C:\Projects\.kis-mcp\python-env\Scripts\python.exe"

& $python -m py_compile `
    (Join-Path $repositoryRoot "src\kis_mcp\discover\tools.py") `
    (Join-Path $repositoryRoot "src\kis_mcp\server.py") `
    (Join-Path $repositoryRoot "tests\discover\test_change_tool_registration.py")
exit $LASTEXITCODE
