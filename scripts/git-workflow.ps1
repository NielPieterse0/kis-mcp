param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$managedPython = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
$python = if (Test-Path -LiteralPath $managedPython) {
    $managedPython
} else {
    (Get-Command python -ErrorAction Stop).Source
}

& $python (Join-Path $PSScriptRoot 'git-workflow.py') --repository $repositoryRoot @Arguments
exit $LASTEXITCODE
