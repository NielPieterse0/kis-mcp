[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'secret-vault.ps1')
. (Join-Path $PSScriptRoot 'windows-credential.ps1')

$Payload = Get-KisMcpUnlockPayload -Prompt 'Create kis-mcp secrets unlock'
$Result = Invoke-KisMcpSecretCommand `
    -CommandArguments @('initialize') `
    -SecurePayload $Payload
if ($Payload.ContainsKey('unlock')) {
    Set-KisMcpWindowsCredential `
        -Target (Get-KisMcpRuntimeUnlockCredentialTarget) `
        -Secret $Payload['unlock']
}
Write-Output $Result
