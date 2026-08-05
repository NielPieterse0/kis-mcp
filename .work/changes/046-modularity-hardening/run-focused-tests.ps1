$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = 'C:\Projects\kis-mcp\.work\worktrees\046-modularity-hardening'
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'

Push-Location $RepositoryRoot
try {
    & $Python -m pytest `
        tests/control_center `
        tests/architecture/test_modularity_boundaries.py `
        -q
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
