param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$Destination
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$SettingsPath = Join-Path $RepositoryRoot 'settings\providers\github-mcp.provider.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
if ($Settings.auth_mode -ne 'oauth') {
    throw 'GITHUB_MCP_SETTINGS_INVALID: auth_mode must be oauth.'
}

$InstallRoot = [System.IO.Path]::GetFullPath('C:\Projects\.kis-mcp\github-mcp')
$ResolvedDestination = if ([string]::IsNullOrWhiteSpace($Destination)) {
    [System.IO.Path]::GetFullPath([string]$Settings.executable)
}
else {
    [System.IO.Path]::GetFullPath($Destination)
}
$InstallPrefix = $InstallRoot.TrimEnd('\') + '\'
if (-not $ResolvedDestination.StartsWith($InstallPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "GITHUB_MCP_DESTINATION_OUTSIDE_INSTALL_ROOT: $ResolvedDestination"
}

$ReleaseTag = [string]$Settings.release_tag
$ExpectedRevision = ([string]$Settings.source_revision).ToLowerInvariant()
$Headers = @{
    'Accept' = 'application/vnd.github+json'
    'User-Agent' = 'kis-mcp-github-installer'
    'X-GitHub-Api-Version' = '2022-11-28'
}
$ReleaseApi = "https://api.github.com/repos/github/github-mcp-server/releases/tags/$ReleaseTag"
$TagApi = "https://api.github.com/repos/github/github-mcp-server/git/ref/tags/$ReleaseTag"

$StateRoot = 'C:\Projects\.kis-mcp'
$Workspace = Join-Path $StateRoot ("temp\github-mcp-install\" + [Guid]::NewGuid().ToString('N'))
$ArchivePath = Join-Path $Workspace 'github-mcp-server.zip'
$ExtractRoot = Join-Path $Workspace 'extracted'
$QuarantineRoot = Join-Path $StateRoot 'quarantine\github-mcp-install'
New-Item -ItemType Directory -Path $Workspace, $ExtractRoot, $InstallRoot, $QuarantineRoot -Force | Out-Null

$Backup = $null
$Installed = $false
try {
    $Release = Invoke-RestMethod -Uri $ReleaseApi -Headers $Headers -Method Get
    if ([string]$Release.tag_name -ne $ReleaseTag -or [bool]$Release.draft -or [bool]$Release.prerelease) {
        throw 'GITHUB_MCP_RELEASE_INVALID: release metadata does not match the pinned stable tag.'
    }
    if (-not [bool]$Release.immutable) {
        throw 'GITHUB_MCP_RELEASE_MUTABLE: the pinned GitHub release is not immutable.'
    }

    $TagReference = Invoke-RestMethod -Uri $TagApi -Headers $Headers -Method Get
    $TargetType = [string]$TagReference.object.type
    $TargetSha = ([string]$TagReference.object.sha).ToLowerInvariant()
    if ($TargetType -eq 'tag') {
        $AnnotatedTag = Invoke-RestMethod -Uri ([string]$TagReference.object.url) -Headers $Headers -Method Get
        $TargetType = [string]$AnnotatedTag.object.type
        $TargetSha = ([string]$AnnotatedTag.object.sha).ToLowerInvariant()
    }
    if ($TargetType -ne 'commit' -or $TargetSha -ne $ExpectedRevision) {
        throw "GITHUB_MCP_REVISION_MISMATCH: expected $ExpectedRevision but release tag resolves to $TargetType $TargetSha."
    }

    $Assets = @($Release.assets | Where-Object {
        ([string]$_.name) -match '(?i)windows.*(x86_64|amd64).*\.zip$'
    })
    if ($Assets.Count -ne 1) {
        throw "GITHUB_MCP_ASSET_SELECTION_FAILED: expected one Windows x86-64 ZIP asset, found $($Assets.Count)."
    }
    $Asset = $Assets[0]
    $PublishedDigest = [string]$Asset.digest
    if ($PublishedDigest -notmatch '^sha256:([0-9a-fA-F]{64})$') {
        throw 'GITHUB_MCP_ASSET_DIGEST_MISSING: release asset does not publish a SHA-256 digest.'
    }
    $ExpectedArchiveSha256 = $Matches[1].ToUpperInvariant()

    Invoke-WebRequest -Uri ([string]$Asset.browser_download_url) -Headers $Headers -OutFile $ArchivePath
    $ActualArchiveSha256 = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash
    if (-not $ActualArchiveSha256.Equals($ExpectedArchiveSha256, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'GITHUB_MCP_ARCHIVE_HASH_MISMATCH: downloaded release asset did not match its published digest.'
    }

    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $ExtractRoot
    $Executables = @(Get-ChildItem -LiteralPath $ExtractRoot -Recurse -File | Where-Object {
        $_.Name.Equals('github-mcp-server.exe', [System.StringComparison]::OrdinalIgnoreCase)
    })
    if ($Executables.Count -ne 1) {
        throw "GITHUB_MCP_ARCHIVE_INVALID: expected one github-mcp-server.exe, found $($Executables.Count)."
    }

    $DestinationDirectory = Split-Path -Parent $ResolvedDestination
    New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
    $Staging = Join-Path $DestinationDirectory ("github-mcp-server." + [Guid]::NewGuid().ToString('N') + '.staging.exe')
    Copy-Item -LiteralPath $Executables[0].FullName -Destination $Staging
    $BinarySha256 = (Get-FileHash -LiteralPath $Staging -Algorithm SHA256).Hash

    if (Test-Path -LiteralPath $ResolvedDestination -PathType Leaf) {
        $Timestamp = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
        $Backup = Join-Path $DestinationDirectory "github-mcp-server.$Timestamp.backup.exe"
        Move-Item -LiteralPath $ResolvedDestination -Destination $Backup
    }
    try {
        Move-Item -LiteralPath $Staging -Destination $ResolvedDestination
    }
    catch {
        if ($null -ne $Backup -and -not (Test-Path -LiteralPath $ResolvedDestination)) {
            Move-Item -LiteralPath $Backup -Destination $ResolvedDestination
            $Backup = $null
        }
        throw
    }

    $Installed = $true
    [pscustomobject]@{
        installed = $true
        provider = [string]$Settings.provider_id
        release_tag = $ReleaseTag
        source_revision = $ExpectedRevision
        asset = [string]$Asset.name
        published_digest = "sha256:$ExpectedArchiveSha256"
        archive_sha256 = $ActualArchiveSha256
        binary_sha256 = $BinarySha256
        destination = $ResolvedDestination
        backup = $Backup
    }
}
finally {
    if (Test-Path -LiteralPath $Workspace) {
        $Disposition = if ($Installed) { 'completed' } else { 'failed' }
        $QuarantineDestination = Join-Path $QuarantineRoot (
            [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + "-$Disposition-" + [Guid]::NewGuid().ToString('N')
        )
        try {
            Move-Item -LiteralPath $Workspace -Destination $QuarantineDestination
        }
        catch {
            Write-Warning "GITHUB_MCP_INSTALL_WORKSPACE_NOT_QUARANTINED: $Workspace"
        }
    }
}
