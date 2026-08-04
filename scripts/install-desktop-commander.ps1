$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json

$CanonicalStateRoot = 'C:\Projects\.kis-mcp'
$ExpectedInstallRoot = Join-Path $CanonicalStateRoot 'desktop-commander'
$ExpectedConfigRoot = Join-Path $CanonicalStateRoot '.claude-server-commander'
$ExpectedCacheRoot = Join-Path $CanonicalStateRoot 'npm-cache'
$ExpectedTempRoot = Join-Path $CanonicalStateRoot 'temp'

$InstallRoot = [string]$Settings.paths.desktop_commander_root
$ProviderConfigRoot = [string]$Settings.paths.desktop_commander_config_root
$CacheRoot = [string]$Settings.paths.npm_cache_root
$TempRoot = [string]$Settings.paths.temp_root
$StateRoot = [string]$Settings.paths.state_root
$Package = [string]$Settings.desktop_commander.package
$Version = [string]$Settings.desktop_commander.version
$EntryPointRelative = [string]$Settings.desktop_commander.entry_point
$EntryPoint = Join-Path $InstallRoot $EntryPointRelative
$ArchiveFileName = [string]$Settings.desktop_commander.archive.file_name
$ExpectedArchiveSha256 = ([string]$Settings.desktop_commander.archive.sha256).ToUpperInvariant()

$ExpectedPaths = [ordered]@{
    state_root = $CanonicalStateRoot
    desktop_commander_root = $ExpectedInstallRoot
    desktop_commander_config_root = $ExpectedConfigRoot
    npm_cache_root = $ExpectedCacheRoot
    temp_root = $ExpectedTempRoot
}
foreach ($Key in $ExpectedPaths.Keys) {
    if ([string]$Settings.paths.$Key -ne [string]$ExpectedPaths[$Key]) {
        throw "Canonical bootstrap path differs for $Key."
    }
}
if ($Package -ne '@wonderwhy-er/desktop-commander') {
    throw 'Desktop Commander package must use the authoritative distribution.'
}
if (-not ($Version -match '^\d+\.\d+\.\d+([-.][0-9A-Za-z.-]+)?$')) {
    throw 'Desktop Commander version must be an exact pinned version.'
}
$ExpectedArchiveFileName = "wonderwhy-er-desktop-commander-$Version.tgz"
if ($ArchiveFileName -ne $ExpectedArchiveFileName) {
    throw "DESKTOP_COMMANDER_ARCHIVE_NAME_INVALID: expected $ExpectedArchiveFileName."
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
    throw (
        "DESKTOP_COMMANDER_ARCHIVE_HASH_MISMATCH: expected $ExpectedArchiveSha256; " +
        "found $ActualArchiveSha256 at $ArchivePath"
    )
}

$NodeCommand = Get-Command 'node.exe' -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($null -eq $NodeCommand) {
    throw 'NODE_NOT_INSTALLED: Node.js 18 or newer is required for Desktop Commander.'
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
    throw 'NPM_NOT_INSTALLED: npm.cmd was not found. Install Node.js 18 or newer with npm.'
}

foreach ($Path in @($ProviderConfigRoot, $CacheRoot, $TempRoot, $StateRoot)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$StagingRoot = Join-Path $TempRoot ("desktop-commander-install-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null
$StagingEntryPoint = Join-Path $StagingRoot $EntryPointRelative
$StagingPackageMetadata = Join-Path $StagingRoot 'node_modules\@wonderwhy-er\desktop-commander\package.json'

$env:NPM_CONFIG_CACHE = $CacheRoot
$env:NPM_CONFIG_OFFLINE = 'true'
$env:NPM_CONFIG_AUDIT = 'false'
$env:NPM_CONFIG_FUND = 'false'
$env:NPM_CONFIG_UPDATE_NOTIFIER = 'false'
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:HOME = $StateRoot
$env:USERPROFILE = $StateRoot
$env:NO_UPDATE_NOTIFIER = '1'

Write-Host "Installing $Package@$Version from verified local archive $ArchivePath..."
Write-Host "Verified SHA-256: $ActualArchiveSha256"
& $NpmCommand.Source install $ArchivePath `
    --prefix $StagingRoot `
    --cache $CacheRoot `
    --save-exact `
    --offline `
    --ignore-scripts `
    --no-audit `
    --no-fund
if ($LASTEXITCODE -ne 0) {
    throw (
        "DESKTOP_COMMANDER_OFFLINE_INSTALL_FAILED: npm exited with code $LASTEXITCODE. " +
        "The scanned package does not bundle its dependency closure; every dependency must already " +
        "exist in the scanned local npm cache at $CacheRoot. Partial staging remains at $StagingRoot."
    )
}

if (-not (Test-Path -LiteralPath $StagingEntryPoint -PathType Leaf)) {
    throw "DESKTOP_COMMANDER_ENTRY_MISSING: staged entry point was not installed: $StagingEntryPoint"
}
if (-not (Test-Path -LiteralPath $StagingPackageMetadata -PathType Leaf)) {
    throw "DESKTOP_COMMANDER_METADATA_MISSING: $StagingPackageMetadata"
}
$InstalledMetadata = Get-Content -LiteralPath $StagingPackageMetadata -Raw | ConvertFrom-Json
if ([string]$InstalledMetadata.name -ne $Package) {
    throw "DESKTOP_COMMANDER_IDENTITY_MISMATCH: installed package is $($InstalledMetadata.name)."
}
if ([string]$InstalledMetadata.version -ne $Version) {
    throw "DESKTOP_COMMANDER_VERSION_MISMATCH: installed version is $($InstalledMetadata.version)."
}

$BackupRoot = $null
if (Test-Path -LiteralPath $InstallRoot) {
    $BackupRoot = Join-Path $TempRoot (
        "desktop-commander-backup-" +
        (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') +
        '-' + [guid]::NewGuid().ToString('N')
    )
    Move-Item -LiteralPath $InstallRoot -Destination $BackupRoot
}
try {
    Move-Item -LiteralPath $StagingRoot -Destination $InstallRoot
}
catch {
    if ($null -ne $BackupRoot -and -not (Test-Path -LiteralPath $InstallRoot)) {
        Move-Item -LiteralPath $BackupRoot -Destination $InstallRoot
    }
    throw "DESKTOP_COMMANDER_ACTIVATION_FAILED: $($_.Exception.Message)"
}

$ProviderConfig = [ordered]@{
    blockedCommands = @()
    allowedDirectories = @()
    telemetryEnabled = $false
}
$ProviderConfigPath = Join-Path $ProviderConfigRoot 'config.json'
$ProviderConfigJson = ($ProviderConfig | ConvertTo-Json -Depth 5) + [Environment]::NewLine
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ProviderConfigPath, $ProviderConfigJson, $Utf8NoBom)

if (-not (Test-Path -LiteralPath $EntryPoint -PathType Leaf)) {
    throw "Desktop Commander entry point was not installed: $EntryPoint"
}

Write-Host "Desktop Commander $Version installed at $InstallRoot"
Write-Host "Provider configuration written to $ProviderConfigPath"
if ($null -ne $BackupRoot) {
    Write-Host "Previous installation retained at $BackupRoot"
}
Write-Host 'Installation used the verified local archive, npm offline mode, and disabled package scripts.'
Write-Host 'Provider command blocking is empty, file directories are unrestricted, and telemetry is disabled.'
