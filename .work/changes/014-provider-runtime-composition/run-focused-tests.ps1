param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArguments
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "LOCKED_INTERPRETER_MISSING: $Python"
}

& $Python -m pytest @PytestArguments
exit $LASTEXITCODE
