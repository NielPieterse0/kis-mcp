$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = 'C:\Projects\kis-mcp\.work\worktrees\046-modularity-hardening'
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'

Push-Location $RepositoryRoot
try {
    & $Python -m pytest `
        tests/providers/nvidia/test_nvidia.py `
        tests/providers/test_platform_composition.py `
        tests/tools/codex_cli/test_adapter.py `
        tests/workflows/code_review `
        'tests/architecture/test_modularity_boundaries.py::test_infrastructure_settings_do_not_depend_on_code_review_workflow' `
        -q
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
