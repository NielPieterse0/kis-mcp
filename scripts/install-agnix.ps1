param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$SettingsPath = Join-Path $RepositoryRoot 'settings\bootstrap\agnix.install.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$ProjectsRoot = [System.IO.Path]::GetFullPath('C:\Projects')

function Assert-InProjects([string]$Path, [string]$Name) {
    $Full = [System.IO.Path]::GetFullPath($Path)
    $Prefix = $ProjectsRoot.TrimEnd('\') + '\'
    if ($Full -ne $ProjectsRoot -and -not $Full.StartsWith($Prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "AGNIX_PATH_OUTSIDE_PROJECTS: $Name=$Full"
    }
    $Probe = $Full
    while (-not [string]::IsNullOrWhiteSpace($Probe)) {
        if (Test-Path -LiteralPath $Probe) {
            $Item = Get-Item -LiteralPath $Probe -Force
            if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "AGNIX_PATH_REPARSE_POINT: $Name traverses $Probe"
            }
        }
        if ($Probe -eq $ProjectsRoot) { break }
        $Parent = Split-Path -Parent $Probe
        if ([string]::IsNullOrWhiteSpace($Parent) -or $Parent -eq $Probe) { break }
        $Probe = $Parent
    }
    return $Full
}

function ConvertTo-WslPath([string]$Path, [string]$Name) {
    $Full = Assert-InProjects $Path $Name
    if ($Full -notmatch '^(?<drive>[A-Za-z]):\\(?<rest>.*)$') {
        throw "AGNIX_WSL_PATH_INVALID: $Name=$Full"
    }
    $Drive = $Matches.drive.ToLowerInvariant()
    $Rest = $Matches.rest -replace '\\', '/'
    return "/mnt/$Drive/$Rest"
}

if ([string]$Settings.package -ne 'agnix' -or [string]$Settings.version -ne '0.45.0') {
    throw 'AGNIX_SETTINGS_INVALID: package and exact version must be agnix@0.45.0.'
}
if (
    [string]$Settings.source.repository -ne 'agent-sh/agnix' -or
    [string]$Settings.source.release_tag -ne 'v0.45.0' -or
    [string]$Settings.source.asset -ne 'agnix-x86_64-unknown-linux-gnu.tar.gz' -or
    [string]$Settings.source.checksum_asset -ne 'agnix-x86_64-unknown-linux-gnu.tar.gz.sha256'
) {
    throw 'AGNIX_SOURCE_INVALID: authoritative source identity must exactly match agent-sh/agnix v0.45.0 Linux x86_64 release assets.'
}
if ([string]$Settings.validation.runtime_kind -ne 'wsl') {
    throw 'AGNIX_RUNTIME_INVALID: runtime_kind must be wsl.'
}

$InstallRoot = Assert-InProjects ([string]$Settings.install_root) 'install_root'
$TempRoot = Assert-InProjects ([string]$Settings.temp_root) 'temp_root'
$QuarantineRoot = Assert-InProjects ([string]$Settings.quarantine_root) 'quarantine_root'
$Distribution = [string]$Settings.validation.wsl_distribution
if ([string]::IsNullOrWhiteSpace($Distribution)) {
    throw 'AGNIX_WSL_DISTRIBUTION_INVALID: wsl_distribution is required.'
}

$Wsl = Get-Command 'wsl.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
$Tar = Get-Command 'tar.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $Wsl -or $null -eq $Tar) {
    throw 'AGNIX_PREREQUISITE_MISSING: wsl.exe and tar.exe are required.'
}
$WslProbe = (& $Wsl.Source --distribution $Distribution --exec sh -lc 'printf KIS_WSL_OK' 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $WslProbe -ne 'KIS_WSL_OK') {
    throw "AGNIX_WSL_UNAVAILABLE: distribution $Distribution did not pass the execution probe: $WslProbe"
}

foreach ($Path in @($TempRoot, $QuarantineRoot, (Split-Path -Parent $InstallRoot))) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}
$OperationId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$OperationQuarantine = Join-Path $QuarantineRoot $OperationId
New-Item -ItemType Directory -Path $OperationQuarantine -Force | Out-Null
$StageId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$StagingInstallRoot = $null
try {
$StagingInstallRoot = Assert-InProjects (Join-Path $TempRoot "agnix-package-$StageId") 'staging_install_root'
$SourceRoot = Join-Path $StagingInstallRoot 'source'
$BinRoot = Join-Path $StagingInstallRoot 'bin'
New-Item -ItemType Directory -Path $SourceRoot -Force | Out-Null
New-Item -ItemType Directory -Path $BinRoot -Force | Out-Null

$ReleaseBase = "https://github.com/$($Settings.source.repository)/releases/download/$($Settings.source.release_tag)"
$ArchiveUrl = "$ReleaseBase/$($Settings.source.asset)"
$ChecksumUrl = "$ReleaseBase/$($Settings.source.checksum_asset)"
$ArchivePath = Join-Path $SourceRoot ([string]$Settings.source.asset)
$ChecksumPath = Join-Path $SourceRoot ([string]$Settings.source.checksum_asset)

Write-Host "Downloading authoritative agnix $($Settings.version) Linux release asset..."
    Invoke-WebRequest -UseBasicParsing -Uri $ArchiveUrl -OutFile $ArchivePath
    Invoke-WebRequest -UseBasicParsing -Uri $ChecksumUrl -OutFile $ChecksumPath

    $ExpectedHash = $null
foreach ($Line in (Get-Content -LiteralPath $ChecksumPath)) {
    if ($Line -match '^\s*(?<hash>[0-9A-Fa-f]{64})\s+\*?(?<name>.+?)\s*$') {
        $CandidateName = [System.IO.Path]::GetFileName(($Matches.name -replace '/', '\'))
        if ($CandidateName -eq [string]$Settings.source.asset) {
            $ExpectedHash = $Matches.hash.ToUpperInvariant()
            break
        }
    }
}
if ([string]::IsNullOrWhiteSpace($ExpectedHash)) {
    throw 'AGNIX_CHECKSUM_INVALID: upstream checksum sidecar did not identify the configured asset.'
}
$ActualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ArchivePath).Hash.ToUpperInvariant()
if ($ActualHash -ne $ExpectedHash) {
    throw "AGNIX_CHECKSUM_MISMATCH: expected $ExpectedHash, got $ActualHash."
}

& $Tar.Source -xzf $ArchivePath -C $BinRoot
if ($LASTEXITCODE -ne 0) {
    throw "AGNIX_EXTRACT_FAILED: tar exited with code $LASTEXITCODE."
}
$BinaryPath = Join-Path $BinRoot 'agnix'
if (-not (Test-Path -LiteralPath $BinaryPath -PathType Leaf)) {
    throw 'AGNIX_PACKAGE_INVALID: extracted agnix executable is missing.'
}

$WslBinary = ConvertTo-WslPath $BinaryPath 'staged_binary'
$VersionOutput = (& $Wsl.Source --distribution $Distribution --exec $WslBinary --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $VersionOutput -notmatch '0\.45\.0') {
    throw "AGNIX_SMOKE_FAILED: unexpected version output '$VersionOutput'."
}

$FinalBinaryPath = Join-Path $InstallRoot 'bin\agnix'
$Status = [ordered]@{
    schema_version = 2
    tool_id = 'agnix'
    version = [string]$Settings.version
    installed_at = [DateTimeOffset]::UtcNow.ToString('o')
    install_root = $InstallRoot
    runtime_kind = 'wsl'
    wsl_distribution = $Distribution
    binary = $FinalBinaryPath
    wsl_binary = ConvertTo-WslPath $FinalBinaryPath 'final_binary'
    source_repository = [string]$Settings.source.repository
    release_tag = [string]$Settings.source.release_tag
    source_url = $ArchiveUrl
    checksum_url = $ChecksumUrl
    asset_sha256 = $ActualHash.ToLowerInvariant()
    publisher_signature = 'not_applicable_linux_elf'
    version_output = $VersionOutput
    previous_state_quarantine = $OperationQuarantine
}

$StatusPath = Join-Path $StagingInstallRoot 'installation.json'
$StatusJson = ($Status | ConvertTo-Json -Depth 6) + [Environment]::NewLine
[System.IO.File]::WriteAllText($StatusPath, $StatusJson, (New-Object System.Text.UTF8Encoding($false)))
}
catch {
    $AcquisitionFailure = $_
    if (-not [string]::IsNullOrWhiteSpace([string]$StagingInstallRoot) -and (Test-Path -LiteralPath $StagingInstallRoot)) {
        try { Move-Item -LiteralPath $StagingInstallRoot -Destination (Join-Path $OperationQuarantine 'failed-stage') }
        catch { Write-Warning "AGNIX_FAILED_STAGE_QUARANTINE_FAILED: $($_.Exception.Message)" }
    }
    throw $AcquisitionFailure
}

$PreviousInstall = $null
$InstallActivated = $false
try {
    if (Test-Path -LiteralPath $InstallRoot) {
        $PreviousInstallDestination = Join-Path $OperationQuarantine 'previous-package'
        Move-Item -LiteralPath $InstallRoot -Destination $PreviousInstallDestination
        $PreviousInstall = $PreviousInstallDestination
    }
    Move-Item -LiteralPath $StagingInstallRoot -Destination $InstallRoot
    $InstallActivated = $true
}
catch {
    $ActivationMessage = $_.Exception.Message
    $RollbackErrors = @()
    if ($InstallActivated -and (Test-Path -LiteralPath $InstallRoot)) {
        try { Move-Item -LiteralPath $InstallRoot -Destination (Join-Path $OperationQuarantine 'failed-new-package') }
        catch { $RollbackErrors += "new package: $($_.Exception.Message)" }
    }
    if ($null -ne $PreviousInstall -and -not (Test-Path -LiteralPath $InstallRoot)) {
        try { Move-Item -LiteralPath $PreviousInstall -Destination $InstallRoot }
        catch { $RollbackErrors += "previous package: $($_.Exception.Message)" }
    }
    $RollbackDetail = if ($RollbackErrors.Count -gt 0) { '; rollback errors: ' + ($RollbackErrors -join ' | ') } else { '' }
    throw "AGNIX_ACTIVATION_FAILED: $ActivationMessage$RollbackDetail"
}

$Status | ConvertTo-Json -Depth 6
