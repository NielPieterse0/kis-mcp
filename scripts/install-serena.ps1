param(
    [ValidateSet('Acquire', 'PrepareInstall', 'Promote')]
    [string]$Mode = 'Acquire',
    [string]$AcquisitionRoot = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\tools\serena.tool.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$TempRoot = 'C:\Projects\.kis-mcp\temp'
$BootstrapPython = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'

function Write-Utf8Json([string]$Path, [object]$Value) {
    $json = ($Value | ConvertTo-Json -Depth 10) + [Environment]::NewLine
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $json, $utf8)
}

function Require-CleanApproval(
    [string]$Path,
    [string]$ExpectedTool
) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "SERENA_OPERATOR_SCAN_APPROVAL_MISSING: $Path"
    }
    $approval = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    if ([string]$approval.tool -ne $ExpectedTool -or
        [string]$approval.result -ne 'clean') {
        throw "SERENA_OPERATOR_SCAN_APPROVAL_INVALID: expected clean approval for $ExpectedTool."
    }
}

if (-not (Test-Path -LiteralPath $BootstrapPython -PathType Leaf)) {
    throw "SERENA_BOOTSTRAP_PYTHON_MISSING: $BootstrapPython"
}

if ($Mode -eq 'Acquire') {
    $PythonLauncher = Get-Command 'py.exe' -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
    $AcquisitionRoot = Join-Path $TempRoot (
        'serena-acquisition-' + [guid]::NewGuid().ToString('N')
    )
    $Wheelhouse = Join-Path $AcquisitionRoot 'wheelhouse'
    $PipCache = Join-Path $AcquisitionRoot 'pip-cache'
    New-Item -ItemType Directory -Path $Wheelhouse -Force | Out-Null
    New-Item -ItemType Directory -Path $PipCache -Force | Out-Null
    $env:PIP_CACHE_DIR = $PipCache
    $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
    $env:TEMP = $AcquisitionRoot
    $env:TMP = $AcquisitionRoot

    $PackageSpec = "$($Settings.package_name)==$($Settings.package_version)"
    & $PythonLauncher.Source -3.11 -m pip download $PackageSpec `
        --dest $Wheelhouse `
        --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        throw "SERENA_DEPENDENCY_ACQUISITION_FAILED: pip exited with $LASTEXITCODE."
    }

    $RootWheels = @(
        Get-ChildItem -LiteralPath $Wheelhouse -Filter 'serena_agent-1.6.1-*.whl' -File
    )
    if ($RootWheels.Count -ne 1) {
        throw 'SERENA_ROOT_WHEEL_COUNT_INVALID: expected exactly one Serena wheel.'
    }
    $RootWheel = $RootWheels[0]
    $ActualSha256 = (Get-FileHash -LiteralPath $RootWheel.FullName -Algorithm SHA256).Hash
    $ExpectedSha256 = ([string]$Settings.package_sha256).ToUpperInvariant()
    if ($ActualSha256 -ne $ExpectedSha256) {
        throw "SERENA_ROOT_WHEEL_HASH_MISMATCH: expected $ExpectedSha256; found $ActualSha256."
    }

    $Files = @(
        Get-ChildItem -LiteralPath $Wheelhouse -File |
            Sort-Object Name |
            ForEach-Object {
                [ordered]@{
                    name = $_.Name
                    sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
                    length = $_.Length
                }
            }
    )
    $Manifest = [ordered]@{
        schema_version = 1
        tool = 'serena-wheelhouse'
        package = [string]$Settings.package_name
        version = [string]$Settings.package_version
        source_revision = [string]$Settings.source_revision
        acquisition_root = $AcquisitionRoot
        wheelhouse = $Wheelhouse
        root_wheel = [ordered]@{
            path = $RootWheel.FullName
            sha256 = $ActualSha256
        }
        files = $Files
        provider_executed = $false
        scan_status = 'pending_operator_scan'
        acquired_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    $ManifestPath = Join-Path $AcquisitionRoot 'acquisition-manifest.json'
    Write-Utf8Json $ManifestPath $Manifest
    $Manifest | ConvertTo-Json -Depth 10
    exit 0
}

if ([string]::IsNullOrWhiteSpace($AcquisitionRoot)) {
    throw 'SERENA_ACQUISITION_ROOT_REQUIRED: provide the scanned acquisition root.'
}
$AcquisitionManifestPath = Join-Path $AcquisitionRoot 'acquisition-manifest.json'
if (-not (Test-Path -LiteralPath $AcquisitionManifestPath -PathType Leaf)) {
    throw "SERENA_ACQUISITION_MANIFEST_MISSING: $AcquisitionManifestPath"
}
$AcquisitionManifest = Get-Content -LiteralPath $AcquisitionManifestPath -Raw |
    ConvertFrom-Json
$Wheelhouse = [string]$AcquisitionManifest.wheelhouse
if (-not (Test-Path -LiteralPath $Wheelhouse -PathType Container)) {
    throw "SERENA_WHEELHOUSE_MISSING: $Wheelhouse"
}

if ($Mode -eq 'PrepareInstall') {
    Require-CleanApproval `
        (Join-Path $AcquisitionRoot 'operator-wheelhouse-scan-approved.json') `
        'serena-wheelhouse'
    $CandidateRoot = Join-Path $AcquisitionRoot 'candidate-install'
    if (Test-Path -LiteralPath $CandidateRoot) {
        throw "SERENA_CANDIDATE_ALREADY_EXISTS: $CandidateRoot"
    }
    $CandidateVenv = Join-Path $CandidateRoot 'venv'
    & $BootstrapPython -m venv $CandidateVenv
    if ($LASTEXITCODE -ne 0) {
        throw "SERENA_VENV_CREATION_FAILED: Python exited with $LASTEXITCODE."
    }

    $CandidatePython = Join-Path $CandidateVenv 'Scripts\python.exe'
    & $CandidatePython -m pip install `
        --no-index `
        --find-links $Wheelhouse `
        "$($Settings.package_name)==$($Settings.package_version)" `
        --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        throw "SERENA_OFFLINE_INSTALL_FAILED: pip exited with $LASTEXITCODE."
    }

    foreach ($RelativePath in @(
        'home',
        'home\.serena',
        'home\.serena\memories',
        'cache',
        'logs',
        'temp',
        'language-servers'
    )) {
        New-Item -ItemType Directory `
            -Path (Join-Path $CandidateRoot $RelativePath) `
            -Force | Out-Null
    }
    $CandidateExecutable = Join-Path $CandidateVenv 'Scripts\serena.exe'
    if (-not (Test-Path -LiteralPath $CandidateExecutable -PathType Leaf)) {
        throw "SERENA_CANDIDATE_EXECUTABLE_MISSING: $CandidateExecutable"
    }
    $CandidateManifest = [ordered]@{
        schema_version = 1
        tool = 'serena-candidate'
        acquisition_root = $AcquisitionRoot
        candidate_root = $CandidateRoot
        executable = $CandidateExecutable
        source_wheelhouse = $Wheelhouse
        provider_executed = $false
        scan_status = 'pending_operator_scan'
        prepared_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    Write-Utf8Json `
        (Join-Path $AcquisitionRoot 'candidate-manifest.json') `
        $CandidateManifest
    $CandidateManifest | ConvertTo-Json -Depth 8
    exit 0
}

Require-CleanApproval `
    (Join-Path $AcquisitionRoot 'operator-candidate-scan-approved.json') `
    'serena-candidate'
$CandidateManifestPath = Join-Path $AcquisitionRoot 'candidate-manifest.json'
if (-not (Test-Path -LiteralPath $CandidateManifestPath -PathType Leaf)) {
    throw "SERENA_CANDIDATE_MANIFEST_MISSING: $CandidateManifestPath"
}
$CandidateManifest = Get-Content -LiteralPath $CandidateManifestPath -Raw |
    ConvertFrom-Json
$CandidateRoot = [string]$CandidateManifest.candidate_root
if (-not (Test-Path -LiteralPath $CandidateRoot -PathType Container)) {
    throw "SERENA_CANDIDATE_MISSING: $CandidateRoot"
}
$Destination = [string]$Settings.install_root
$Backup = $null
if (Test-Path -LiteralPath $Destination) {
    $Backup = Join-Path $TempRoot (
        'serena-backup-' +
        (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') +
        '-' + [guid]::NewGuid().ToString('N')
    )
    Move-Item -LiteralPath $Destination -Destination $Backup
}

try {
    Move-Item -LiteralPath $CandidateRoot -Destination $Destination
}
catch {
    if ($null -ne $Backup -and -not (Test-Path -LiteralPath $Destination)) {
        Move-Item -LiteralPath $Backup -Destination $Destination
    }
    throw "SERENA_PROMOTION_FAILED: $($_.Exception.Message)"
}

[ordered]@{
    schema_version = 1
    tool = 'serena'
    result = 'promoted'
    install_root = $Destination
    previous_install_backup = $Backup
    provider_executed = $false
} | ConvertTo-Json -Depth 5
