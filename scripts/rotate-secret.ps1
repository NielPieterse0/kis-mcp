[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'secret-vault.ps1')

$Payload = Get-KisMcpUnlockPayload
$NewUnlock = Read-Host 'New kis-mcp secrets unlock' -AsSecureString
$Confirmation = Read-Host 'Confirm new kis-mcp secrets unlock' -AsSecureString
Assert-KisMcpSecureStringsMatch -First $NewUnlock -Second $Confirmation
$Payload['new_unlock'] = $NewUnlock
$Result = Invoke-KisMcpSecretCommand `
    -CommandArguments @('rotate') `
    -SecurePayload $Payload
Write-Output $Result
