[CmdletBinding()]
param(
    [ValidateSet('operation', 'development')]
    [string]$Instance = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'tunnel-state.ps1')
. (Join-Path $PSScriptRoot 'secret-vault.ps1')

$Remote = Get-KisMcpRemoteInstance -Instance $Instance
$Payload = Get-KisMcpUnlockPayload
$Value = Read-Host "Enter the tunnel authentication credential for '$($Remote.name)'" -AsSecureString
$Payload['value'] = $Value
try {
    $null = Invoke-KisMcpSecretCommand `
        -CommandArguments @('set', '--reference', $Remote.tunnel_secret_ref) `
        -SecurePayload $Payload
    Write-Host 'credential_state=stored'
    Write-Host "instance=$($Remote.name)"
    Write-Host "secret_reference=$($Remote.tunnel_secret_ref)"
}
finally {
    foreach ($Name in @($Payload.Keys)) {
        $Payload[$Name] = $null
    }
    $Payload.Clear()
    $Value = $null
}
