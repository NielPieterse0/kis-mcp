[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'secret-vault.ps1')

$Payload = Get-KisMcpUnlockPayload -Prompt 'Create kis-mcp secrets unlock'
$Result = Invoke-KisMcpSecretCommand `
    -CommandArguments @('initialize') `
    -SecurePayload $Payload
Write-Output $Result
