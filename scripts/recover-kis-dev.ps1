[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Foreground,
    [string]$ReadPath = '',
    [string]$ExpectedSourceRevision = '',
    [ValidateRange(0,300)][int]$WaitSeconds = 60
)
$Arguments = @{
    Instance = 'kis-dev'
    RepositoryRoot = $RepositoryRoot
    WaitSeconds = $WaitSeconds
}
if ($Foreground) { $Arguments.Foreground = $true }
if (-not [string]::IsNullOrWhiteSpace($ReadPath)) { $Arguments.ReadPath = $ReadPath }
if (-not [string]::IsNullOrWhiteSpace($ExpectedSourceRevision)) { $Arguments.ExpectedSourceRevision = $ExpectedSourceRevision }
& (Join-Path $PSScriptRoot 'recover-chatgpt.ps1') @Arguments
