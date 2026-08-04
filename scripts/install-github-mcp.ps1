param(
    [Parameter(Mandatory = $true)]
    [string]$SourceBinary,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9A-Fa-f]{64}$')]
    [string]$ExpectedSha256,

    [string]$Destination = 'C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$InstallRoot = [System.IO.Path]::GetFullPath('C:\Projects\.kis-mcp\github-mcp')
$ResolvedSource = (Resolve-Path -LiteralPath $SourceBinary).Path
$ResolvedDestination = [System.IO.Path]::GetFullPath($Destination)
$InstallPrefix = $InstallRoot.TrimEnd('\') + '\'
if (-not $ResolvedDestination.StartsWith($InstallPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Destination must remain beneath $InstallRoot"
}

$ActualSha256 = (Get-FileHash -LiteralPath $ResolvedSource -Algorithm SHA256).Hash
if (-not $ActualSha256.Equals($ExpectedSha256, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "SHA-256 mismatch for the supplied GitHub MCP executable."
}

$DestinationDirectory = Split-Path -Parent $ResolvedDestination
New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null

if (Test-Path -LiteralPath $ResolvedDestination -PathType Leaf) {
    $Timestamp = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
    $Backup = Join-Path $DestinationDirectory "github-mcp-server.$Timestamp.backup.exe"
    Move-Item -LiteralPath $ResolvedDestination -Destination $Backup
}

Copy-Item -LiteralPath $ResolvedSource -Destination $ResolvedDestination
$InstalledSha256 = (Get-FileHash -LiteralPath $ResolvedDestination -Algorithm SHA256).Hash
if (-not $InstalledSha256.Equals($ExpectedSha256, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Installed GitHub MCP executable failed post-copy SHA-256 verification."
}

[pscustomobject]@{
    installed = $true
    destination = $ResolvedDestination
    sha256 = $InstalledSha256
}
