[CmdletBinding()]
param(
    [ValidateSet('operation', 'development')]
    [string]$Instance = '',
    [switch]$BackupExistingProfile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'tunnel-state.ps1')

$Remote = Get-KisMcpRemoteInstance -Instance $Instance -RequireConfigured
$KeyValue = [Environment]::GetEnvironmentVariable($Remote.control_plane_api_key_env)
if ([string]::IsNullOrWhiteSpace($KeyValue)) {
    throw "KIS_MCP_CONTROL_PLANE_API_KEY_MISSING: set $($Remote.control_plane_api_key_env) in this PowerShell session."
}
if (-not (Test-Path -LiteralPath $Remote.tunnel_client_path -PathType Leaf)) {
    throw "KIS_MCP_TUNNEL_CLIENT_MISSING: $($Remote.tunnel_client_path)"
}

[System.IO.Directory]::CreateDirectory($Remote.profile_root) | Out-Null
$ProfilePath = Join-Path $Remote.profile_root "$($Remote.profile_name).yaml"
if (Test-Path -LiteralPath $ProfilePath -PathType Leaf) {
    if (-not $BackupExistingProfile) {
        throw "KIS_MCP_TUNNEL_PROFILE_EXISTS: use -BackupExistingProfile to preserve and replace $ProfilePath"
    }
    $BackupRoot = Join-Path $Remote.profile_root 'backups'
    [System.IO.Directory]::CreateDirectory($BackupRoot) | Out-Null
    $Timestamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
    $BackupPath = Join-Path $BackupRoot "$($Remote.profile_name)-$Timestamp.yaml"
    [System.IO.File]::Move($ProfilePath, $BackupPath)
    Write-Host "Existing tunnel profile backed up to: $BackupPath"
}

$ApiKeyReference = "env:$($Remote.control_plane_api_key_env)"
& $Remote.tunnel_client_path init `
    --sample sample_mcp_remote_no_auth `
    --profile $Remote.profile_name `
    --profile-dir $Remote.profile_root `
    --tunnel-id $Remote.tunnel_id `
    --mcp-server-url $Remote.endpoint_url `
    --control-plane-api-key-ref $ApiKeyReference `
    --health-listen-addr '127.0.0.1:0'
if ($LASTEXITCODE -ne 0) {
    throw "KIS_MCP_TUNNEL_PROFILE_INIT_FAILED: $($Remote.profile_name)"
}
if (-not (Test-Path -LiteralPath $ProfilePath -PathType Leaf)) {
    throw "KIS_MCP_TUNNEL_PROFILE_NOT_CREATED: $ProfilePath"
}

& $Remote.tunnel_client_path doctor `
    --profile $Remote.profile_name `
    --profile-dir $Remote.profile_root `
    --explain
if ($LASTEXITCODE -ne 0) {
    throw "KIS_MCP_TUNNEL_PROFILE_INVALID: $($Remote.profile_name)"
}

Write-Host "Tunnel profile created and validated for instance '$($Remote.name)'."
Write-Host "Tunnel ID: $($Remote.tunnel_id)"
Write-Host "Control-plane scope ID: $($Remote.control_plane_scope_id)"
Write-Host "Local MCP endpoint: $($Remote.endpoint_url)"
