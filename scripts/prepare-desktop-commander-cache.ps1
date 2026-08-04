$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json

$CanonicalStateRoot = 'C:\Projects\.kis-mcp'
$ExpectedCacheRoot = Join-Path $CanonicalStateRoot 'npm-cache'
$ExpectedTempRoot = Join-Path $CanonicalStateRoot 'temp'

$StateRoot = [string]$Settings.paths.state_root
$CacheRoot = [string]$Settings.paths.npm_cache_root
$TempRoot = [string]$Settings.paths.temp_root
$Package = [string]$Settings.desktop_commander.package
$Version = [string]$Settings.desktop_commander.version
$ArchiveFileName = [string]$Settings.desktop_commander.archive.file_name
$ExpectedArchiveSha256 = ([string]$Settings.desktop_commander.archive.sha256).ToUpperInvariant()

if ($StateRoot -ne $CanonicalStateRoot) {
    throw 'Canonical state root differs from C:\Projects\.kis-mcp.'
}
if ($CacheRoot -ne $ExpectedCacheRoot) {
    throw 'Canonical npm cache root differs from C:\Projects\.kis-mcp\npm-cache.'
}
if ($TempRoot -ne $ExpectedTempRoot) {
    throw 'Canonical temporary root differs from C:\Projects\.kis-mcp\temp.'
}
if ($Package -ne '@wonderwhy-er/desktop-commander') {
    throw 'Desktop Commander package must use the authoritative distribution.'
}
if ($Version -notmatch '^\d+\.\d+\.\d+([-.][0-9A-Za-z.-]+)?$') {
    throw 'Desktop Commander version must be an exact pinned version.'
}
if ($ArchiveFileName -ne "wonderwhy-er-desktop-commander-$Version.tgz") {
    throw 'DESKTOP_COMMANDER_ARCHIVE_NAME_INVALID: archive name does not match the pinned version.'
}
if ($ExpectedArchiveSha256 -notmatch '^[0-9A-F]{64}$') {
    throw 'DESKTOP_COMMANDER_ARCHIVE_HASH_INVALID: settings must contain an exact SHA-256 digest.'
}

$UserProfileRoot = [Environment]::GetFolderPath('UserProfile')
if ([string]::IsNullOrWhiteSpace($UserProfileRoot)) {
    throw 'USER_PROFILE_NOT_FOUND: cannot resolve the Downloads directory.'
}
$ArchivePath = Join-Path (Join-Path $UserProfileRoot 'Downloads') $ArchiveFileName
if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
    throw "DESKTOP_COMMANDER_ARCHIVE_NOT_FOUND: $ArchivePath"
}
$ActualArchiveSha256 = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToUpperInvariant()
if ($ActualArchiveSha256 -ne $ExpectedArchiveSha256) {
    throw "DESKTOP_COMMANDER_ARCHIVE_HASH_MISMATCH: expected $ExpectedArchiveSha256; found $ActualArchiveSha256."
}

$NodeCommand = Get-Command 'node.exe' -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($null -eq $NodeCommand) {
    throw 'NODE_NOT_INSTALLED: Node.js 18 or newer is required.'
}
$NodeVersion = (& $NodeCommand.Source --version).Trim()
if ($LASTEXITCODE -ne 0 -or $NodeVersion -notmatch '^v(?<major>\d+)\.') {
    throw "NODE_VERSION_INVALID: unable to determine the installed Node.js version from '$NodeVersion'."
}
if ([int]$Matches.major -lt 18) {
    throw "NODE_VERSION_UNSUPPORTED: Node.js 18 or newer is required; found $NodeVersion."
}

$NpmCommand = Get-Command 'npm.cmd' -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($null -eq $NpmCommand) {
    throw 'NPM_NOT_INSTALLED: npm.cmd was not found.'
}
$NpmVersion = (& $NpmCommand.Source --version).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'NPM_VERSION_INVALID: unable to determine the npm version.'
}

$DefenderCandidates = @(
    (Join-Path $env:ProgramFiles 'Windows Defender\MpCmdRun.exe'),
    (Join-Path $env:ProgramData 'Microsoft\Windows Defender\Platform')
)
$DefenderCommand = $null
if (Test-Path -LiteralPath $DefenderCandidates[0] -PathType Leaf) {
    $DefenderCommand = $DefenderCandidates[0]
}
elseif (Test-Path -LiteralPath $DefenderCandidates[1] -PathType Container) {
    $DefenderCommand = Get-ChildItem -LiteralPath $DefenderCandidates[1] -Directory |
        Sort-Object Name -Descending |
        ForEach-Object { Join-Path $_.FullName 'MpCmdRun.exe' } |
        Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
        Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace([string]$DefenderCommand)) {
    throw 'WINDOWS_DEFENDER_NOT_FOUND: MpCmdRun.exe could not be resolved.'
}

New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
$AcquisitionId = [guid]::NewGuid().ToString('N')
$AcquisitionRoot = Join-Path $TempRoot "desktop-commander-dependency-acquisition-$AcquisitionId"
$AcquisitionCache = Join-Path $AcquisitionRoot 'npm-cache'
$AcquisitionInstall = Join-Path $AcquisitionRoot 'install-check'
$ManifestPath = Join-Path $AcquisitionRoot 'scan-manifest.json'
New-Item -ItemType Directory -Path $AcquisitionCache -Force | Out-Null
New-Item -ItemType Directory -Path $AcquisitionInstall -Force | Out-Null

$env:NPM_CONFIG_CACHE = $AcquisitionCache
$env:NPM_CONFIG_OFFLINE = 'false'
$env:NPM_CONFIG_AUDIT = 'false'
$env:NPM_CONFIG_FUND = 'false'
$env:NPM_CONFIG_UPDATE_NOTIFIER = 'false'
$env:TEMP = $AcquisitionRoot
$env:TMP = $AcquisitionRoot
$env:NO_UPDATE_NOTIFIER = '1'

Write-Host "Acquiring the dependency closure for $Package@$Version."
Write-Host "The root package is the verified local archive: $ArchivePath"
Write-Host 'External registry access is permitted only in this supervised preparation script.'

& $NpmCommand.Source install $ArchivePath `
    --prefix $AcquisitionInstall `
    --cache $AcquisitionCache `
    --save-exact `
    --ignore-scripts `
    --no-audit `
    --no-fund
if ($LASTEXITCODE -ne 0) {
    throw "DESKTOP_COMMANDER_DEPENDENCY_ACQUISITION_FAILED: npm exited with code $LASTEXITCODE. Acquisition remains at $AcquisitionRoot."
}

$InstalledMetadataPath = Join-Path $AcquisitionInstall 'node_modules\@wonderwhy-er\desktop-commander\package.json'
if (-not (Test-Path -LiteralPath $InstalledMetadataPath -PathType Leaf)) {
    throw "DESKTOP_COMMANDER_METADATA_MISSING: $InstalledMetadataPath"
}
$InstalledMetadata = Get-Content -LiteralPath $InstalledMetadataPath -Raw | ConvertFrom-Json
if ([string]$InstalledMetadata.name -ne $Package -or [string]$InstalledMetadata.version -ne $Version) {
    throw "DESKTOP_COMMANDER_IDENTITY_MISMATCH: expected $Package@$Version; found $($InstalledMetadata.name)@$($InstalledMetadata.version)."
}

Write-Host "Scanning acquired package contents with Microsoft Defender: $AcquisitionRoot"
& $DefenderCommand -Scan -ScanType 3 -File $AcquisitionRoot
$DefenderExitCode = $LASTEXITCODE
if ($DefenderExitCode -ne 0) {
    throw "DESKTOP_COMMANDER_DEPENDENCY_SCAN_FAILED: Defender exited with code $DefenderExitCode. Nothing was promoted."
}

$Manifest = [ordered]@{
    schema_version = 1
    package = $Package
    version = $Version
    archive = [ordered]@{
        path = $ArchivePath
        sha256 = $ActualArchiveSha256
    }
    acquisition = [ordered]@{
        completed_utc = (Get-Date).ToUniversalTime().ToString('o')
        node_version = $NodeVersion
        npm_version = $NpmVersion
        package_scripts_disabled = $true
        audit_disabled = $true
        root_package_source = 'verified_local_archive'
        dependency_registry_access = 'operator_supervised'
    }
    defender = [ordered]@{
        executable = [string]$DefenderCommand
        exit_code = $DefenderExitCode
        result = 'clean'
    }
}
$ManifestJson = ($Manifest | ConvertTo-Json -Depth 8) + [Environment]::NewLine
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ManifestPath, $ManifestJson, $Utf8NoBom)

$PreviousCacheBackup = $null
if (Test-Path -LiteralPath $CacheRoot) {
    $PreviousCacheBackup = Join-Path $TempRoot (
        'npm-cache-backup-' +
        (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') +
        '-' + [guid]::NewGuid().ToString('N')
    )
    Move-Item -LiteralPath $CacheRoot -Destination $PreviousCacheBackup
}
try {
    Move-Item -LiteralPath $AcquisitionCache -Destination $CacheRoot
}
catch {
    if ($null -ne $PreviousCacheBackup -and -not (Test-Path -LiteralPath $CacheRoot)) {
        Move-Item -LiteralPath $PreviousCacheBackup -Destination $CacheRoot
    }
    throw "DESKTOP_COMMANDER_CACHE_PROMOTION_FAILED: $($_.Exception.Message)"
}

Write-Host "Scanned dependency cache promoted to $CacheRoot"
Write-Host "Scan manifest retained at $ManifestPath"
if ($null -ne $PreviousCacheBackup) {
    Write-Host "Previous cache retained at $PreviousCacheBackup"
}
Write-Host 'Next: rerun scripts\install-desktop-commander.ps1. That installer remains strictly offline.'
