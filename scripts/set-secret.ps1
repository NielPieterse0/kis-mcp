[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Reference
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'secret-vault.ps1')

$Payload = Get-KisMcpUnlockPayload
$Value = Read-Host "Set value for $Reference" -AsSecureString
$Payload['value'] = $Value
$Result = Invoke-KisMcpSecretCommand `
    -CommandArguments @('set', '--reference', $Reference) `
    -SecurePayload $Payload
Write-Output $Result
