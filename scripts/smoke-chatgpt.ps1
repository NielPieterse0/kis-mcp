[CmdletBinding()]
param(
    [string]$Instance = '',
    [switch]$AllInstances,
    [int]$TimeoutSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'tunnel-state.ps1')

function Start-OwnedProcess {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [hashtable]$Environment = @{}
    )

    $Info = [System.Diagnostics.ProcessStartInfo]::new()
    $Info.FileName = $Executable
    $Info.WorkingDirectory = $WorkingDirectory
    $Info.UseShellExecute = $false
    $Info.CreateNoWindow = $false
    foreach ($Argument in $Arguments) {
        $Info.ArgumentList.Add($Argument)
    }
    foreach ($Name in $Environment.Keys) {
        $Info.Environment[$Name] = [string]$Environment[$Name]
    }
    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $Info
    if (-not $Process.Start()) {
        throw "KIS_MCP_SMOKE_PROCESS_START_FAILED: $Executable"
    }
    return $Process
}

function Invoke-McpJsonRpc {
    param(
        [string]$Uri,
        [hashtable]$Payload,
        [int]$RequestTimeoutSeconds = 5
    )

    $Headers = @{
        Accept = 'application/json, text/event-stream'
        'MCP-Protocol-Version' = '2025-06-18'
    }
    return Invoke-RestMethod `
        -Uri $Uri `
        -Method Post `
        -Headers $Headers `
        -ContentType 'application/json' `
        -Body ($Payload | ConvertTo-Json -Depth 30 -Compress) `
        -TimeoutSec $RequestTimeoutSeconds
}

function Test-McpToolCallFailed {
    param([object]$Response)

    $ErrorProperty = $Response.PSObject.Properties['error']
    if ($null -ne $ErrorProperty) {
        return $true
    }
    $ResultProperty = $Response.PSObject.Properties['result']
    if ($null -eq $ResultProperty) {
        return $true
    }
    $IsErrorProperty = $ResultProperty.Value.PSObject.Properties['isError']
    return $null -ne $IsErrorProperty -and [bool]$IsErrorProperty.Value
}

function Invoke-KisMcpInstanceSmoke {
    param([string]$Name)

    $Remote = Get-KisMcpRemoteInstance -Instance $Name
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $Python = Join-Path $Remote.python_environment_root 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "KIS_MCP_SMOKE_PYTHON_MISSING: $Python"
    }
    $Listener = Get-NetTCPConnection `
        -LocalAddress $Remote.host `
        -LocalPort $Remote.port `
        -State Listen `
        -ErrorAction SilentlyContinue
    if ($Listener) {
        throw "KIS_MCP_SMOKE_PORT_IN_USE: $($Remote.host):$($Remote.port)"
    }

    $StateRoot = $Remote.state_root
    $Environment = @{
        PYTHONPATH = (Join-Path $RepositoryRoot 'src')
        UV_PROJECT_ENVIRONMENT = $Remote.python_environment_root
        UV_CACHE_DIR = (Join-Path $StateRoot 'uv-cache')
        PYTHONPYCACHEPREFIX = (Join-Path $StateRoot 'python-cache')
        TEMP = (Join-Path $StateRoot 'temp')
        TMP = (Join-Path $StateRoot 'temp')
        NO_UPDATE_NOTIFIER = '1'
    }

    $Server = $null
    $SmokePath = $null
    try {
        $Server = Start-OwnedProcess `
            -Executable $Python `
            -Arguments @('-m', 'kis_mcp.remote_runtime', '--instance', $Remote.name) `
            -WorkingDirectory $RepositoryRoot `
            -Environment $Environment

        $Deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
        $InitializeResponse = $null
        $Initialize = @{
            jsonrpc = '2.0'
            id = 1
            method = 'initialize'
            params = @{
                protocolVersion = '2025-06-18'
                capabilities = @{}
                clientInfo = @{ name = 'kis-mcp-smoke'; version = '1.0' }
            }
        }
        while ([DateTime]::UtcNow -lt $Deadline) {
            if ($Server.HasExited) {
                throw "KIS_MCP_SMOKE_HTTP_EXITED: $($Server.ExitCode)"
            }
            try {
                $InitializeResponse = Invoke-McpJsonRpc `
                    -Uri $Remote.endpoint_url `
                    -Payload $Initialize
                if ($null -ne $InitializeResponse.result.serverInfo) {
                    break
                }
            }
            catch {
                Start-Sleep -Milliseconds 250
            }
        }
        if ($null -eq $InitializeResponse.result.serverInfo) {
            throw "KIS_MCP_SMOKE_INITIALIZE_FAILED: $($Remote.endpoint_url)"
        }

        $ToolsResponse = Invoke-McpJsonRpc `
            -Uri $Remote.endpoint_url `
            -Payload @{
                jsonrpc = '2.0'
                id = 2
                method = 'tools/list'
                params = @{}
            }
        $ToolNames = @($ToolsResponse.result.tools | ForEach-Object { [string]$_.name })
        $ExpectedTools = @(
            'kis_health',
            'inspect_project',
            'read_file',
            'write_file',
            'edit_block',
            'start_process'
        )
        $MissingTools = @($ExpectedTools | Where-Object { $_ -notin $ToolNames })
        if ($MissingTools.Count -gt 0) {
            throw "KIS_MCP_SMOKE_TOOLS_MISSING: $($MissingTools -join ', ')"
        }
        if ('give_feedback_to_desktop_commander' -in $ToolNames) {
            throw 'KIS_MCP_SMOKE_NETWORK_ONLY_TOOL_EXPOSED: give_feedback_to_desktop_commander'
        }

        $HealthResponse = Invoke-McpJsonRpc `
            -Uri $Remote.endpoint_url `
            -Payload @{
                jsonrpc = '2.0'
                id = 3
                method = 'tools/call'
                params = @{
                    name = 'kis_health'
                    arguments = @{}
                }
            }
        if (Test-McpToolCallFailed -Response $HealthResponse) {
            throw 'KIS_MCP_SMOKE_HEALTH_CALL_FAILED'
        }

        $DiscoverResponse = Invoke-McpJsonRpc `
            -Uri $Remote.endpoint_url `
            -RequestTimeoutSeconds 60 `
            -Payload @{
                jsonrpc = '2.0'
                id = 31
                method = 'tools/call'
                params = @{
                    name = 'inspect_project'
                    arguments = @{
                        path = $RepositoryRoot
                        limits = @{
                            max_files = 100
                            max_directories = 100
                            max_total_bytes = 2000000
                            max_evidence = 100
                            max_output_chars = 200000
                            max_depth = 8
                        }
                    }
                }
            }
        if (Test-McpToolCallFailed -Response $DiscoverResponse) {
            throw 'KIS_MCP_SMOKE_DISCOVER_CALL_FAILED'
        }

        $Marker = "kis-mcp-remote-http-smoke-$($Remote.name)-$([Guid]::NewGuid().ToString('N'))"
        $SmokePath = Join-Path (Join-Path $StateRoot 'temp') "$Marker.txt"
        $WriteResponse = Invoke-McpJsonRpc `
            -Uri $Remote.endpoint_url `
            -Payload @{
                jsonrpc = '2.0'
                id = 4
                method = 'tools/call'
                params = @{
                    name = 'write_file'
                    arguments = @{
                        path = $SmokePath
                        content = $Marker
                        mode = 'rewrite'
                    }
                }
            }
        if (Test-McpToolCallFailed -Response $WriteResponse) {
            throw 'KIS_MCP_SMOKE_WRITE_CALL_FAILED'
        }

        $ReadResponse = Invoke-McpJsonRpc `
            -Uri $Remote.endpoint_url `
            -Payload @{
                jsonrpc = '2.0'
                id = 5
                method = 'tools/call'
                params = @{
                    name = 'read_file'
                    arguments = @{
                        path = $SmokePath
                        offset = 0
                        length = 200
                    }
                }
            }
        if (Test-McpToolCallFailed -Response $ReadResponse) {
            throw 'KIS_MCP_SMOKE_READ_CALL_FAILED'
        }
        if (($ReadResponse | ConvertTo-Json -Depth 30) -notmatch [Regex]::Escape($Marker)) {
            throw 'KIS_MCP_SMOKE_READ_CONTENT_MISMATCH'
        }

        $QuarantineResponse = Invoke-McpJsonRpc `
            -Uri $Remote.endpoint_url `
            -Payload @{
                jsonrpc = '2.0'
                id = 6
                method = 'tools/call'
                params = @{
                    name = 'kis_quarantine_path'
                    arguments = @{ path = $SmokePath }
                }
            }
        if (Test-McpToolCallFailed -Response $QuarantineResponse) {
            throw 'KIS_MCP_SMOKE_QUARANTINE_CALL_FAILED'
        }
        if (Test-Path -LiteralPath $SmokePath) {
            throw 'KIS_MCP_SMOKE_QUARANTINE_SOURCE_REMAINS'
        }

        return [pscustomobject]@{
            instance = $Remote.name
            endpoint = $Remote.endpoint_url
            server = [string]$InitializeResponse.result.serverInfo.name
            tool_count = $ToolNames.Count
            representative_tools = $ExpectedTools
            network_only_feedback_exposed = $false
            health_call_ok = $true
            discover_call_ok = $true
            write_read_quarantine_ok = $true
        }
    }
    finally {
        if (
            -not [string]::IsNullOrWhiteSpace($SmokePath) -and
            (Test-Path -LiteralPath $SmokePath) -and
            $null -ne $Server -and
            -not $Server.HasExited
        ) {
            try {
                $CleanupResponse = Invoke-McpJsonRpc `
                    -Uri $Remote.endpoint_url `
                    -Payload @{
                        jsonrpc = '2.0'
                        id = 90
                        method = 'tools/call'
                        params = @{
                            name = 'kis_quarantine_path'
                            arguments = @{ path = $SmokePath }
                        }
                    }
                if (Test-McpToolCallFailed -Response $CleanupResponse) {
                    Write-Warning 'KIS_MCP_SMOKE_CLEANUP_QUARANTINE_FAILED'
                }
            }
            catch {
                Write-Warning "KIS_MCP_SMOKE_CLEANUP_QUARANTINE_FAILED: $($_.Exception.Message)"
            }
        }
        if ($null -ne $Server -and -not $Server.HasExited) {
            $Server.Kill()
            $null = $Server.WaitForExit(5000)
        }
    }
}

if ($TimeoutSeconds -lt 5 -or $TimeoutSeconds -gt 300) {
    throw 'KIS_MCP_SMOKE_TIMEOUT_INVALID: TimeoutSeconds must be between 5 and 300.'
}
$Targets = if ($AllInstances) {
    @('operation', 'development')
}
elseif ([string]::IsNullOrWhiteSpace($Instance)) {
    @((Get-KisMcpRemoteInstance).name)
}
else {
    @($Instance)
}

$Results = @($Targets | ForEach-Object { Invoke-KisMcpInstanceSmoke -Name $_ })
$Results | ConvertTo-Json -Depth 10
