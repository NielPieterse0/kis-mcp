[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Foreground,
    [string]$ReadPath = '',
    [ValidateRange(0,300)][int]$WaitSeconds = 60
)
$Arguments = @{
    Instance = 'kis-op'
    RepositoryRoot = $RepositoryRoot
    WaitSeconds = $WaitSeconds
}
if ($Foreground) { $Arguments.Foreground = $true }
if (-not [string]::IsNullOrWhiteSpace($ReadPath)) { $Arguments.ReadPath = $ReadPath }
& (Join-Path $PSScriptRoot 'recover-chatgpt.ps1') @Arguments
