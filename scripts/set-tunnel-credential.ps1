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
$Secret = Read-Host "Enter the tunnel authentication credential for '$($Remote.name)'" -AsSecureString
Set-KisMcpWindowsCredential -Target $Remote.tunnel_credential_target -Secret $Secret
Write-Host "credential_state=stored"
Write-Host "instance=$($Remote.name)"
Write-Host "credential_target=$($Remote.tunnel_credential_target)"
