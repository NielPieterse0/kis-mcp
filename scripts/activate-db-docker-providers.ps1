param(
    [string]$DBHubSourceRoot = '',
    [string]$DockerHubSourceRoot = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$StateRoot = 'C:\Projects\.kis-mcp'
$ProviderRoot = Join-Path $StateRoot 'providers'
$QuarantineRoot = Join-Path $StateRoot 'quarantine'
$DBHubRevision = '1bed0b8bd8e6e3e625c83f571d12f748f2d7a0b0'
$DBHubRelease = 'v1.2.0'
$DockerHubRevision = 'ad806e2cab0489a296aec0f32f3d3eea807d65c2'

function Assert-KisProviderSource {
    param([Parameter(Mandatory)][string]$SourceRoot, [Parameter(Mandatory)][string]$Revision)
    $Resolved = (Resolve-Path -LiteralPath $SourceRoot).Path
    if (-not $Resolved.StartsWith('C:\Projects\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "KIS_MCP_PROVIDER_SOURCE_OUTSIDE_PROJECT_BOUNDARY: $Resolved"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Resolved 'dist\index.js') -PathType Leaf)) {
        throw "KIS_MCP_PROVIDER_DIST_MISSING: $Resolved"
    }
    $Actual = (& git -C $Resolved rev-parse HEAD 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or $Actual -ne $Revision) {
        throw "KIS_MCP_PROVIDER_SOURCE_REVISION_MISMATCH: expected=$Revision actual=$Actual"
    }
    return $Resolved
}

function Install-KisProviderTree {
    param(
        [Parameter(Mandatory)][string]$ProviderId,
        [Parameter(Mandatory)][string]$SourceRoot,
        [Parameter(Mandatory)][string]$TargetRoot,
        [Parameter(Mandatory)][string]$Revision,
        [string]$ReleaseTag = ''
    )
    $VerifiedSource = Assert-KisProviderSource -SourceRoot $SourceRoot -Revision $Revision
    New-Item -ItemType Directory -Path $ProviderRoot -Force | Out-Null
    if (Test-Path -LiteralPath $TargetRoot) {
        $Stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmssfff')
        $Recovery = Join-Path $QuarantineRoot "provider-bootstrap-$Stamp\$ProviderId"
        New-Item -ItemType Directory -Path (Split-Path -Parent $Recovery) -Force | Out-Null
        Move-Item -LiteralPath $TargetRoot -Destination $Recovery
    }
    Copy-Item -LiteralPath $VerifiedSource -Destination $TargetRoot -Recurse
    $EntryPoint = Join-Path $TargetRoot 'dist\index.js'
    $Manifest = [ordered]@{
        provider_id = $ProviderId
        source_revision = $Revision
        entry_point_sha256 = (Get-FileHash -LiteralPath $EntryPoint -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    if ($ReleaseTag) {
        $WithRelease = [ordered]@{
            provider_id = $ProviderId
            release_tag = $ReleaseTag
            source_revision = $Revision
            entry_point_sha256 = $Manifest.entry_point_sha256
        }
        $Manifest = $WithRelease
    }
    $ManifestPath = Join-Path $TargetRoot 'installation.json'
    $Manifest | ConvertTo-Json | Set-Content -LiteralPath $ManifestPath -Encoding utf8NoBOM
    Write-Host "Activated $ProviderId at $TargetRoot from exact revision $Revision"
}

if (-not [string]::IsNullOrWhiteSpace($DBHubSourceRoot)) {
    Install-KisProviderTree `
        -ProviderId 'dbhub' `
        -SourceRoot $DBHubSourceRoot `
        -TargetRoot (Join-Path $ProviderRoot "dbhub\$DBHubRelease") `
        -Revision $DBHubRevision `
        -ReleaseTag $DBHubRelease
}

if (-not [string]::IsNullOrWhiteSpace($DockerHubSourceRoot)) {
    Install-KisProviderTree `
        -ProviderId 'dockerhub-mcp' `
        -SourceRoot $DockerHubSourceRoot `
        -TargetRoot (Join-Path $ProviderRoot "dockerhub\$DockerHubRevision") `
        -Revision $DockerHubRevision
}

if ([string]::IsNullOrWhiteSpace($DBHubSourceRoot) -and [string]::IsNullOrWhiteSpace($DockerHubSourceRoot)) {
    throw 'KIS_MCP_PROVIDER_SOURCE_REQUIRED: pass -DBHubSourceRoot and/or -DockerHubSourceRoot for an already provisioned exact local source checkout.'
}
