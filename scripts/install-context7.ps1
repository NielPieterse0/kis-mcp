param(
    [ValidateSet('Acquire', 'Promote')]
    [string]$Mode = 'Acquire',
    [string]$AcquisitionRoot = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\providers\context7.provider.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$TempRoot = 'C:\Projects\.kis-mcp\temp'
$ExpectedIntegrity = [string]$Settings.package_integrity

function Write-Utf8Json([string]$Path, [object]$Value) {
    $json = ($Value | ConvertTo-Json -Depth 10) + [Environment]::NewLine
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $json, $utf8)
}

function Expected-Sha512Hex([string]$Integrity) {
    if (-not $Integrity.StartsWith('sha512-')) {
        throw 'CONTEXT7_INTEGRITY_INVALID: expected a sha512 integrity value.'
    }
    $bytes = [Convert]::FromBase64String($Integrity.Substring(7))
    return [Convert]::ToHexString($bytes)
}

if ($Mode -eq 'Acquire') {
    $npm = Get-Command 'npm.cmd' -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
    $AcquisitionRoot = Join-Path $TempRoot (
        'context7-acquisition-' + [guid]::NewGuid().ToString('N')
    )
    $CacheRoot = Join-Path $AcquisitionRoot 'npm-cache'
    $InstallRoot = Join-Path $AcquisitionRoot 'install'
    New-Item -ItemType Directory -Path $CacheRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null

    $env:NPM_CONFIG_CACHE = $CacheRoot
    $env:NPM_CONFIG_AUDIT = 'false'
    $env:NPM_CONFIG_FUND = 'false'
    $env:NPM_CONFIG_UPDATE_NOTIFIER = 'false'
    $env:TEMP = $AcquisitionRoot
    $env:TMP = $AcquisitionRoot

    $PackageSpec = "$($Settings.package_name)@$($Settings.package_version)"
    & $npm.Source pack $PackageSpec --pack-destination $AcquisitionRoot
    if ($LASTEXITCODE -ne 0) {
        throw "CONTEXT7_ARCHIVE_ACQUISITION_FAILED: npm exited with $LASTEXITCODE."
    }
    $archives = @(Get-ChildItem -LiteralPath $AcquisitionRoot -Filter '*.tgz' -File)
    if ($archives.Count -ne 1) {
        throw 'CONTEXT7_ARCHIVE_COUNT_INVALID: expected exactly one package archive.'
    }
    $Archive = $archives[0]
    $ActualSha512 = (Get-FileHash -LiteralPath $Archive.FullName -Algorithm SHA512).Hash
    $ExpectedSha512 = Expected-Sha512Hex $ExpectedIntegrity
    if ($ActualSha512 -ne $ExpectedSha512) {
        throw "CONTEXT7_ARCHIVE_INTEGRITY_MISMATCH: expected $ExpectedSha512; found $ActualSha512."
    }

    & $npm.Source install $Archive.FullName `
        --prefix $InstallRoot `
        --cache $CacheRoot `
        --save-exact `
        --ignore-scripts `
        --no-audit `
        --no-fund
    if ($LASTEXITCODE -ne 0) {
        throw "CONTEXT7_DEPENDENCY_ACQUISITION_FAILED: npm exited with $LASTEXITCODE."
    }

    $MetadataPath = Join-Path $InstallRoot 'node_modules\@upstash\context7-mcp\package.json'
    if (-not (Test-Path -LiteralPath $MetadataPath -PathType Leaf)) {
        throw "CONTEXT7_METADATA_MISSING: $MetadataPath"
    }
    $Metadata = Get-Content -LiteralPath $MetadataPath -Raw | ConvertFrom-Json
    if ([string]$Metadata.name -ne [string]$Settings.package_name -or
        [string]$Metadata.version -ne [string]$Settings.package_version) {
        throw 'CONTEXT7_IDENTITY_MISMATCH: installed acquisition identity is unexpected.'
    }
    $EntryPoint = Join-Path $InstallRoot 'node_modules\@upstash\context7-mcp\dist\index.js'
    if (-not (Test-Path -LiteralPath $EntryPoint -PathType Leaf)) {
        throw "CONTEXT7_ENTRY_POINT_MISSING: $EntryPoint"
    }

    $Manifest = [ordered]@{
        schema_version = 1
        tool = 'context7'
        package = [string]$Settings.package_name
        version = [string]$Settings.package_version
        source_revision = [string]$Settings.source_revision
        acquisition_root = $AcquisitionRoot
        archive = [ordered]@{
            path = $Archive.FullName
            sha512 = $ActualSha512
            integrity = $ExpectedIntegrity
        }
        dependency_tree = $InstallRoot
        package_scripts_disabled = $true
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
    throw 'CONTEXT7_ACQUISITION_ROOT_REQUIRED: provide the scanned acquisition root.'
}
$ManifestPath = Join-Path $AcquisitionRoot 'acquisition-manifest.json'
$ApprovalPath = Join-Path $AcquisitionRoot 'operator-scan-approved.json'
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "CONTEXT7_MANIFEST_MISSING: $ManifestPath"
}
if (-not (Test-Path -LiteralPath $ApprovalPath -PathType Leaf)) {
    throw "CONTEXT7_OPERATOR_SCAN_APPROVAL_MISSING: $ApprovalPath"
}
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$Approval = Get-Content -LiteralPath $ApprovalPath -Raw | ConvertFrom-Json
if ([string]$Approval.tool -ne 'context7' -or [string]$Approval.result -ne 'clean') {
    throw 'CONTEXT7_OPERATOR_SCAN_APPROVAL_INVALID: approval must record a clean Context7 scan.'
}
$SourceInstall = [string]$Manifest.dependency_tree
$Destination = [string]$Settings.install_root
if (-not (Test-Path -LiteralPath $SourceInstall -PathType Container)) {
    throw "CONTEXT7_SCANNED_TREE_MISSING: $SourceInstall"
}

$Backup = $null
if (Test-Path -LiteralPath $Destination) {
    $Backup = Join-Path $TempRoot (
        'context7-backup-' +
        (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') +
        '-' + [guid]::NewGuid().ToString('N')
    )
    Move-Item -LiteralPath $Destination -Destination $Backup
}
try {
    Move-Item -LiteralPath $SourceInstall -Destination $Destination
}
catch {
    if ($null -ne $Backup -and -not (Test-Path -LiteralPath $Destination)) {
        Move-Item -LiteralPath $Backup -Destination $Destination
    }
    throw "CONTEXT7_PROMOTION_FAILED: $($_.Exception.Message)"
}

[ordered]@{
    schema_version = 1
    tool = 'context7'
    result = 'promoted'
    install_root = $Destination
    previous_install_backup = $Backup
    provider_executed = $false
} | ConvertTo-Json -Depth 5
