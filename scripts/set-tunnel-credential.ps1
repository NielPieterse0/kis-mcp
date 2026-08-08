[CmdletBinding()]
param(
    [ValidateSet('operation', 'development')]
    [string]$Instance = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'tunnel-state.ps1')
. (Join-Path $PSScriptRoot 'windows-credential.ps1')

$Remote = Get-KisMcpRemoteInstance -Instance $Instance
$CredentialTarget = Get-KisMcpTunnelCredentialTarget -Reference $Remote.tunnel_secret_ref
$Secret = Read-Host "Enter the tunnel authentication credential for '$($Remote.name)'" -AsSecureString
Set-KisMcpWindowsCredential -Target $CredentialTarget -Secret $Secret
$Secret = $null
Write-Host 'credential_state=stored'
Write-Host "instance=$($Remote.name)"
Write-Host "secret_reference=$($Remote.tunnel_secret_ref)"
Write-Host "credential_target=$CredentialTarget"
