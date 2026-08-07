$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'

Push-Location $RepositoryRoot
try {
    & $Python -m pytest -q 'tests/discover' 'tests/architecture/test_modularity_boundaries.py' 'tests/architecture/test_capability_composition_boundaries.py' -p no:cacheprovider
    $ExitCode = $LASTEXITCODE
    Write-Output "pytest_exit=$ExitCode"
    exit 0
}
finally {
    Pop-Location
}
