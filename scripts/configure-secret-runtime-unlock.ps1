[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'secret-vault.ps1')
. (Join-Path $PSScriptRoot 'windows-credential.ps1')

$Payload = Get-KisMcpUnlockPayload -Prompt 'Verify kis-mcp secrets unlock for non-interactive runtime use'
if (-not $Payload.ContainsKey('unlock')) {
    throw 'KIS_MCP_RUNTIME_UNLOCK_INTERACTIVE_VALUE_REQUIRED'
}

$Result = Invoke-KisMcpSecretCommand `
    -CommandArguments @('verify-unlock') `
    -SecurePayload $Payload
$Target = Get-KisMcpRuntimeUnlockCredentialTarget
Set-KisMcpWindowsCredential -Target $Target -Secret $Payload['unlock']
Write-Output $Result
