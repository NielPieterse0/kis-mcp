$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = 'C:\Projects\kis-mcp\.work\worktrees\046-modularity-hardening'
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'

Push-Location $RepositoryRoot
try {
    & $Python -m pytest `
        tests/providers/github/test_registry.py `
        'tests/architecture/test_modularity_boundaries.py::test_root_provider_registry_alias_is_retired' `
        -q
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
