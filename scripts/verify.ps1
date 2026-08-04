$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$PolicyPath = Join-Path $RepositoryRoot 'policy\kis-mcp.policy.json'
$LockPath = Join-Path $RepositoryRoot 'uv.lock'

$CanonicalStateRoot = 'C:\Projects\.kis-mcp'
$CanonicalPaths = [ordered]@{
    state_root = $CanonicalStateRoot
    python_environment_root = Join-Path $CanonicalStateRoot 'python-env'
    uv_cache_root = Join-Path $CanonicalStateRoot 'uv-cache'
    python_cache_root = Join-Path $CanonicalStateRoot 'python-cache'
    pytest_cache_root = Join-Path $CanonicalStateRoot 'pytest-cache'
    temp_root = Join-Path $CanonicalStateRoot 'temp'
}

$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$Policy = Get-Content -LiteralPath $PolicyPath -Raw | ConvertFrom-Json
$RuleIds = @($Policy.rules | ForEach-Object { [string]$_.id })
if ($RuleIds.Count -ne 3 -or ($RuleIds -join ',') -ne 'HR-001,HR-002,HR-003') {
    throw 'POLICY_RULE_SET_INVALID: policy must contain exactly HR-001, HR-002, and HR-003.'
}

if ([string]$Settings.paths.project_boundary -ne [string]$Policy.project_boundary) {
    throw 'Settings and policy project boundaries differ.'
}
if ([string]$Settings.paths.quarantine_root -ne [string]$Policy.quarantine_root) {
    throw 'Settings and policy quarantine roots differ.'
}
foreach ($Key in $CanonicalPaths.Keys) {
    if ([string]$Settings.paths.$Key -ne [string]$CanonicalPaths[$Key]) {
        throw "Canonical generated-state path differs for $Key."
    }
}

$RuntimeSkillRoots = @(
    (Join-Path $RepositoryRoot 'src\skills'),
    (Join-Path $RepositoryRoot 'src\kis_mcp\skills')
)
if ($RuntimeSkillRoots | Where-Object { Test-Path -LiteralPath $_ }) {
    throw 'Greenfield boundary violation: active runtime skills catalogue is present.'
}

$RuntimeAndConfigFiles = @(
    Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot 'src') -Recurse -File
    Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot 'settings') -Recurse -File
    Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot 'policy') -Recurse -File
)
$RuntimeSkillReferences = $RuntimeAndConfigFiles | Select-String -SimpleMatch '.agents'
if ($RuntimeSkillReferences) {
    $Details = ($RuntimeSkillReferences | ForEach-Object { "$($_.Path):$($_.LineNumber)" }) -join ', '
    throw "Greenfield boundary violation: runtime or configuration references repository skills: $Details"
}
if (Test-Path -LiteralPath (Join-Path $RepositoryRoot 'node_modules')) {
    throw 'Greenfield boundary violation: Desktop Commander must not be vendored in the repository.'
}

$StaleScanPaths = @(
    'AGENTS.md',
    'README.md',
    'SPEC.md',
    'pyproject.toml',
    'docs',
    'policy',
    'scripts',
    'settings',
    'src'
)
$ApprovedDonorTraceabilityFiles = @(
    (Join-Path $RepositoryRoot 'docs\development\discover-foundation\source-harvest.md')
)
$CurrentFiles = @(
    foreach ($RelativePath in $StaleScanPaths) {
        $Candidate = Join-Path $RepositoryRoot $RelativePath
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
            Get-Item -LiteralPath $Candidate
        }
        elseif (Test-Path -LiteralPath $Candidate -PathType Container) {
            Get-ChildItem -LiteralPath $Candidate -Recurse -File
        }
    }
) | Where-Object {
    $_.FullName -ne $PSCommandPath -and
    $_.FullName -notin $ApprovedDonorTraceabilityFiles
}
$StaleMatches = $CurrentFiles | Select-String -Pattern 'sdk_tool|ki\$_mcp|C:\\Projects\\ast-tool' -CaseSensitive:$false
if ($StaleMatches) {
    $Details = ($StaleMatches | ForEach-Object { "$($_.Path):$($_.LineNumber)" }) -join ', '
    throw "Stale predecessor identity found: $Details"
}

$PowerShellFiles = Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot 'scripts') -Filter '*.ps1' -File
foreach ($PowerShellFile in $PowerShellFiles) {
    $Tokens = $null
    $Errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $PowerShellFile.FullName,
        [ref]$Tokens,
        [ref]$Errors
    )
    if ($Errors.Count -gt 0) {
        $Details = ($Errors | ForEach-Object { $_.Message }) -join '; '
        throw "PowerShell syntax validation failed for $($PowerShellFile.Name): $Details"
    }
}

if (-not (Test-Path -LiteralPath $LockPath -PathType Leaf)) {
    throw 'DEPENDENCY_LOCK_MISSING: generate uv.lock through an operator-supervised dependency update.'
}

foreach ($Path in $CanonicalPaths.Values) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}
$env:UV_PROJECT_ENVIRONMENT = [string]$CanonicalPaths.python_environment_root
$env:UV_CACHE_DIR = [string]$CanonicalPaths.uv_cache_root
$env:PYTHONPYCACHEPREFIX = [string]$CanonicalPaths.python_cache_root
$env:TEMP = [string]$CanonicalPaths.temp_root
$env:TMP = [string]$CanonicalPaths.temp_root
$env:NO_UPDATE_NOTIFIER = '1'
$env:UV_OFFLINE = '1'

Push-Location $RepositoryRoot
try {
    & uv sync --offline --dev --frozen
    if ($LASTEXITCODE -ne 0) {
        throw "Offline dependency synchronization failed with exit code $LASTEXITCODE"
    }

    & uv run --offline --no-sync python scripts\verify.py
    if ($LASTEXITCODE -ne 0) {
        throw "Repository verification failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host 'Verification passed: locked environment, greenfield boundary, and exact three-rule implementation are consistent.'
