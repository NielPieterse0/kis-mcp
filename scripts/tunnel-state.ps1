Set-StrictMode -Version Latest

function Get-KisMcpSettingsPath {
    [CmdletBinding()]
    param()

    return Join-Path (Split-Path -Parent $PSScriptRoot) 'settings\kis-mcp.settings.json'
}

function Get-KisMcpSettings {
    [CmdletBinding()]
    param()

    $Path = Get-KisMcpSettingsPath
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "KIS_MCP_SETTINGS_MISSING: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Get-KisMcpRemoteInstance {
    [CmdletBinding()]
    param(
        [string]$Instance = '',
        [switch]$RequireConfigured
    )

    $Settings = Get-KisMcpSettings
    $Remote = $Settings.remote_mcp
    if ($null -eq $Remote) {
        throw 'KIS_MCP_REMOTE_SETTINGS_MISSING: settings.remote_mcp is required.'
    }
    if ([string]::IsNullOrWhiteSpace($Instance)) {
        $Instance = [string]$Remote.active_instance
    }
    $Instance = $Instance.Trim().ToLowerInvariant()
    if ($Instance -notin @('operation', 'development')) {
        throw "KIS_MCP_REMOTE_INSTANCE_INVALID: $Instance"
    }

    $Property = $Remote.instances.PSObject.Properties[$Instance]
    if ($null -eq $Property) {
        throw "KIS_MCP_REMOTE_INSTANCE_MISSING: $Instance"
    }
    $Configured = [bool]$Property.Value.configured
    $TunnelId = [string]$Property.Value.tunnel_id
    $ControlPlaneScopeId = [string]$Property.Value.control_plane_scope_id
    if ($RequireConfigured -and -not $Configured) {
        throw (
            "KIS_MCP_REMOTE_INSTANCE_NOT_CONFIGURED: set settings.remote_mcp.instances.$Instance" +
            '.tunnel_id and .control_plane_scope_id, then set .configured to true.'
        )
    }
    if ($Configured) {
        if ($TunnelId -notmatch '^tunnel_[0-9a-f]{32}$') {
            throw "KIS_MCP_TUNNEL_ID_INVALID: $Instance"
        }
        if ([string]::IsNullOrWhiteSpace($ControlPlaneScopeId)) {
            throw "KIS_MCP_CONTROL_PLANE_SCOPE_ID_MISSING: $Instance"
        }
    }

    $StateRoot = [string]$Settings.paths.state_root
    $ProfileRoot = Join-Path $StateRoot 'tunnel-client\profiles'
    $RuntimeRoot = Join-Path $StateRoot ("tunnel-client\runtime\$Instance")
    $Endpoint = "http://$([string]$Remote.host):$([int]$Property.Value.port)$([string]$Remote.path)"

    return [pscustomobject]@{
        name = $Instance
        host = [string]$Remote.host
        port = [int]$Property.Value.port
        path = [string]$Remote.path
        endpoint_url = $Endpoint
        profile_name = [string]$Property.Value.profile_name
        profile_root = $ProfileRoot
        runtime_root = $RuntimeRoot
        configured = $Configured
        tunnel_id = $TunnelId
        control_plane_scope_id = $ControlPlaneScopeId
        control_plane_api_key_env = [string]$Property.Value.control_plane_api_key_env
        tunnel_client_path = [string]$Remote.tunnel_client_path
        python_environment_root = [string]$Settings.paths.python_environment_root
        state_root = $StateRoot
    }
}
