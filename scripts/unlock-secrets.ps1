[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'secret-vault.ps1')

$Payload = Get-KisMcpUnlockPayload
$Result = Invoke-KisMcpSecretCommand `
    -CommandArguments @('verify-unlock') `
    -SecurePayload $Payload
Write-Output $Result
