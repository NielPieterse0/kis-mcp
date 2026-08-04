$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$SkillsSettingsPath = Join-Path $RepositoryRoot 'settings\skills.settings.json'
$PolicyPath = Join-Path $RepositoryRoot 'policy\kis-mcp.policy.json'
$LockPath = Join-Path $RepositoryRoot 'uv.lock'

& (Join-Path $PSScriptRoot 'configure-repository.ps1')

$CanonicalStateRoot = 'C:\Projects\.kis-mcp'
$CanonicalSkillsRoot = 'C:\Projects\.agents\skills'
$CanonicalSkillsStagingRoot = 'C:\Projects\.kis-mcp\temp\skills'
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

if (-not (Test-Path -LiteralPath $SkillsSettingsPath -PathType Leaf)) {
    throw 'SKILLS_SETTINGS_INVALID: settings\skills.settings.json is required.'
}
$SkillsSettings = Get-Content -LiteralPath $SkillsSettingsPath -Raw | ConvertFrom-Json
if (
    [int]$SkillsSettings.schema_version -ne 1 -or
    [string]$SkillsSettings.root -ne $CanonicalSkillsRoot -or
    [string]$SkillsSettings.staging_root -ne $CanonicalSkillsStagingRoot
) {
    throw 'SKILLS_SETTINGS_INVALID: Skills settings must use schema version 1 and the approved shared roots.'
}
$RuntimeSkillsRoot = Join-Path $RepositoryRoot 'src\kis_mcp\skills'
if (-not (Test-Path -LiteralPath $RuntimeSkillsRoot -PathType Container)) {
    throw 'SKILLS_SETTINGS_INVALID: the approved runtime Skills module is missing.'
}
if (-not (Test-Path -LiteralPath (Join-Path $RepositoryRoot 'contracts\skills\settings.schema.json') -PathType Leaf)) {
    throw 'SKILLS_SETTINGS_INVALID: the Skills settings contract is missing.'
}

$RuntimeAndConfigFiles = @(
    Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot 'src') -Recurse -File
    Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot 'settings') -Recurse -File
    Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot 'policy') -Recurse -File
)
$RuntimeSkillReferences = $RuntimeAndConfigFiles | Select-String -SimpleMatch '.agents'
$AllowedSkillsRootLiterals = @(
    'C:\Projects\.agents\skills',
    'C:\\Projects\\.agents\\skills'
)
$UnexpectedRuntimeSkillReferences = @(
    foreach ($Match in $RuntimeSkillReferences) {
        $Line = [string]$Match.Line
        $Allowed = $false
        foreach ($Literal in $AllowedSkillsRootLiterals) {
            if ($Line.Contains($Literal)) {
                $Allowed = $true
                break
            }
        }
        if (-not $Allowed) {
            $Match
        }
    }
)
if ($UnexpectedRuntimeSkillReferences) {
    $Details = ($UnexpectedRuntimeSkillReferences | ForEach-Object { "$($_.Path):$($_.LineNumber)" }) -join ', '
    throw "SKILLS_SETTINGS_INVALID: unexpected runtime Skills root reference: $Details"
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

Write-Host 'Verification passed: locked environment, approved Skills root, and exact three-rule implementation are consistent.'
