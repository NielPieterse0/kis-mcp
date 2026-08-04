$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Locked Python environment not found: $Python"
}

Push-Location $RepositoryRoot
try {
    & $Python -m pytest -q @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
