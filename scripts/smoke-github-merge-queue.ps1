param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:PYTEST_ADDOPTS = "-o cache_dir=$(Join-Path $StateRoot 'pytest-cache')"
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
$env:UV_OFFLINE = '1'

Push-Location $RepositoryRoot
try {
    & uv run --offline --no-sync python -m pytest `
        tests/projects/test_github_merge_queue.py `
        tests/capabilities/test_github_merge_queue_capability.py `
        tests/workflows/test_github_merge_queue_workflow.py `
        tests/workflows/test_merge_queue_governance.py `
        tests/workflows/project_management/test_descriptors.py `
        -q
    if ($LASTEXITCODE -ne 0) {
        throw "KIS merge queue focused tests failed with exit code $LASTEXITCODE"
    }

    $SettingsPath = Join-Path $RepositoryRoot 'settings\github-merge-queue.settings.json'
    $Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
    if (
        [int]$Settings.schema_version -ne 1 -or
        [string]$Settings.merge_method -ne 'merge' -or
        [string]$Settings.grouping_strategy -ne 'allgreen' -or
        [int]$Settings.build_concurrency -ne 3 -or
        [int]$Settings.min_entries_to_merge -ne 1 -or
        [int]$Settings.max_entries_to_merge -ne 3 -or
        [int]$Settings.min_entries_to_merge_wait_minutes -ne 0 -or
        [bool]$Settings.allow_jump
    ) {
        throw 'KIS_MERGE_QUEUE_SETTINGS_INVALID: v1 bounded defaults do not match the commissioned contract.'
    }

    $WorkflowPath = Join-Path $RepositoryRoot '.github\workflows\work-management.yml'
    $Workflow = Get-Content -LiteralPath $WorkflowPath -Raw
    if (-not $Workflow.Contains("'kis-readonly-queue/main/**'")) {
        throw 'KIS_MERGE_QUEUE_WORKFLOW_INVALID: canonical verification does not observe queue candidate pushes.'
    }

    [pscustomobject]@{
        component = 'kis-speculative-landing-queue'
        focused_tests = 'passed'
        merge_method = $Settings.merge_method
        grouping_strategy = $Settings.grouping_strategy
        build_concurrency = $Settings.build_concurrency
        merge_group = "$($Settings.min_entries_to_merge)-$($Settings.max_entries_to_merge)"
        candidate_ref_prefix = $Settings.candidate_ref_prefix
        verification_workflow = $Settings.verification_workflow
        local_commissioning = 'passed'
        live_commissioning = 'requires commissioned KIS runtime and registered GitHub operations'
    }
}
finally {
    Pop-Location
}
