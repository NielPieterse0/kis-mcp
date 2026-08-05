param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = 'Stop'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-p no:cacheprovider'
& 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe' -m pytest @PytestArgs
exit $LASTEXITCODE
