[CmdletBinding()]
param(
    [ValidateSet('operation', 'development')]
    [string]$Instance = '',
    [switch]$BackupExistingProfile,
    [switch]$ValidateLiveEndpoint,
    [int]$TimeoutSeconds = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'tunnel-state.ps1')
. (Join-Path $PSScriptRoot 'windows-credential.ps1')

function Append-SetupLog {
    param(
        [string]$Path,
        [string]$Section,
        [object[]]$Content
    )

    $Lines = @("[$Section]") + @($Content | ForEach-Object { [string]$_ })
    [System.IO.File]::AppendAllLines(
        $Path,
        [string[]]$Lines,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Invoke-McpJsonRpc {
    param(
        [string]$Uri,
        [hashtable]$Payload,
        [int]$RequestTimeoutSeconds = 3
    )

    $Headers = @{
        Accept = 'application/json, text/event-stream'
        'MCP-Protocol-Version' = '2025-06-18'
    }
    $Body = $Payload | ConvertTo-Json -Depth 20 -Compress
    return Invoke-RestMethod `
        -Uri $Uri `
        -Method Post `
        -Headers $Headers `
        -ContentType 'application/json' `
        -Body $Body `
        -TimeoutSec $RequestTimeoutSeconds
}

function Wait-KisMcpEndpointReady {
    param(
        [string]$Uri,
        [datetime]$Deadline
    )

    $Initialize = @{
        jsonrpc = '2.0'
        id = 1
        method = 'initialize'
        params = @{
            protocolVersion = '2025-06-18'
            capabilities = @{}
            clientInfo = @{ name = 'kis-mcp-setup'; version = '1.0' }
        }
    }
    while ([DateTime]::UtcNow -lt $Deadline) {
        try {
            $Response = Invoke-McpJsonRpc -Uri $Uri -Payload $Initialize
            if ($null -ne $Response.result.serverInfo) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
    throw "KIS_MCP_ENDPOINT_NOT_READY: $Uri"
}

$Remote = Get-KisMcpRemoteInstance -Instance $Instance -RequireConfigured
if ($TimeoutSeconds -lt 1 -or $TimeoutSeconds -gt 300) {
    throw 'KIS_MCP_TIMEOUT_INVALID: TimeoutSeconds must be between 1 and 300.'
}
if (-not (Test-Path -LiteralPath $Remote.tunnel_client_path -PathType Leaf)) {
    throw "KIS_MCP_TUNNEL_CLIENT_MISSING: $($Remote.tunnel_client_path)"
}

[System.IO.Directory]::CreateDirectory($Remote.profile_root) | Out-Null
[System.IO.Directory]::CreateDirectory($Remote.runtime_root) | Out-Null
$RunId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$SetupLog = Join-Path $Remote.runtime_root "setup-$RunId.log"
[System.IO.File]::WriteAllText($SetupLog, '', [System.Text.UTF8Encoding]::new($false))
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
    Append-SetupLog -Path $SetupLog -Section 'profile-backup' -Content @($BackupPath)
}

$CredentialEnvironmentName = 'KIS_MCP_TUNNEL_CONTROL_PLANE_API_KEY'
$Credential = Get-KisMcpWindowsCredential -Target $Remote.tunnel_credential_target
$PreviousCredential = [Environment]::GetEnvironmentVariable(
    $CredentialEnvironmentName,
    [EnvironmentVariableTarget]::Process
)
$LiveValidation = 'skipped'
try {
    [Environment]::SetEnvironmentVariable(
        $CredentialEnvironmentName,
        $Credential,
        [EnvironmentVariableTarget]::Process
    )
    $Credential = $null
    $AuthenticationReference = "env:$CredentialEnvironmentName"

    $InitOutput = & $Remote.tunnel_client_path init `
        --sample sample_mcp_remote_no_auth `
        --profile $Remote.profile_name `
        --profile-dir $Remote.profile_root `
        --tunnel-id $Remote.tunnel_id `
        --mcp-server-url $Remote.endpoint_url `
        --control-plane-api-key-ref $AuthenticationReference `
        --health-listen-addr '127.0.0.1:0' 2>&1
    $InitExitCode = $LASTEXITCODE
    Append-SetupLog -Path $SetupLog -Section 'init' -Content @($InitOutput)
    if ($InitExitCode -ne 0) {
        throw "KIS_MCP_TUNNEL_PROFILE_INIT_FAILED: $($Remote.profile_name); setup_log=$SetupLog"
    }
    if (-not (Test-Path -LiteralPath $ProfilePath -PathType Leaf)) {
        throw "KIS_MCP_TUNNEL_PROFILE_NOT_CREATED: $ProfilePath"
    }

    if ($ValidateLiveEndpoint) {
        $Deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
        Wait-KisMcpEndpointReady -Uri $Remote.endpoint_url -Deadline $Deadline

        $DoctorOutput = & $Remote.tunnel_client_path doctor `
            --profile $Remote.profile_name `
            --profile-dir $Remote.profile_root `
            --explain 2>&1
        $DoctorExitCode = $LASTEXITCODE
        Append-SetupLog -Path $SetupLog -Section 'doctor' -Content @($DoctorOutput)
        if ($DoctorExitCode -ne 0) {
            throw "KIS_MCP_TUNNEL_PROFILE_INVALID: $($Remote.profile_name); setup_log=$SetupLog"
        }
        $LiveValidation = 'ready'
    }
}
finally {
    [Environment]::SetEnvironmentVariable(
        $CredentialEnvironmentName,
        $PreviousCredential,
        [EnvironmentVariableTarget]::Process
    )
    $Credential = $null
    $PreviousCredential = $null
    $AuthenticationReference = $null
}

Write-Host "Tunnel profile created for instance '$($Remote.name)'."
Write-Host "instance=$($Remote.name)"
Write-Host "tunnel_profile=$($Remote.profile_name)"
Write-Host "tunnel_id=$($Remote.tunnel_id)"
Write-Host "endpoint=$($Remote.endpoint_url)"
Write-Host "live_validation=$LiveValidation"
Write-Host "setup_log=$SetupLog"
