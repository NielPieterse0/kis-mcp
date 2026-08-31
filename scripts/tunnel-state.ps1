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

function Resolve-KisMcpInstanceName {
    [CmdletBinding()]
    param([string]$Instance)

    if ([string]::IsNullOrWhiteSpace($Instance)) {
        throw 'KIS_MCP_REMOTE_INSTANCE_INVALID: select kis-op or kis-dev.'
    }
    switch ($Instance.Trim().ToLowerInvariant()) {
        { $_ -in @('kis-op', 'op', 'operation') } { return 'operation' }
        { $_ -in @('kis-dev', 'dev', 'development') } { return 'development' }
        default {
            throw "KIS_MCP_REMOTE_INSTANCE_INVALID: $Instance. Use kis-op or kis-dev."
        }
    }
}

function Assert-KisMcpRemoteConfiguration {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Remote)

    if ($null -eq $Remote.instances) {
        throw 'KIS_MCP_REMOTE_INSTANCES_MISSING: settings.remote_mcp.instances is required.'
    }
    if ([string]$Remote.host -ne '127.0.0.1') {
        throw 'KIS_MCP_REMOTE_HOST_INVALID: remote MCP instances must bind 127.0.0.1.'
    }
    if ([string]$Remote.path -ne '/mcp') {
        throw 'KIS_MCP_REMOTE_PATH_INVALID: remote MCP instances must use /mcp.'
    }
    if ([string]$Remote.tunnel_client_version -notmatch '^\d+\.\d+\.\d+$') {
        throw 'KIS_MCP_TUNNEL_CLIENT_VERSION_INVALID'
    }
    if ([string]$Remote.tunnel_client_sha256 -notmatch '^[0-9a-f]{64}$') {
        throw 'KIS_MCP_TUNNEL_CLIENT_SHA256_INVALID'
    }
    if ([string]$Remote.tunnel_client_release_archive_sha256 -notmatch '^[0-9a-f]{64}$') {
        throw 'KIS_MCP_TUNNEL_CLIENT_RELEASE_ARCHIVE_SHA256_INVALID'
    }

    $Expected = [ordered]@{
        operation = [pscustomobject]@{ app_name = 'kis-op'; port = 8010 }
        development = [pscustomobject]@{ app_name = 'kis-dev'; port = 8011 }
    }
    $InstanceNames = @($Remote.instances.PSObject.Properties.Name)
    if (
        $InstanceNames.Count -ne $Expected.Count -or
        @($Expected.Keys | Where-Object { $_ -notin $InstanceNames }).Count -gt 0
    ) {
        throw 'KIS_MCP_REMOTE_INSTANCE_SET_INVALID: exactly operation and development are required.'
    }

    $PortOwners = @{}
    foreach ($Name in $Expected.Keys) {
        $Record = $Remote.instances.PSObject.Properties[$Name].Value
        $Port = [int]$Record.port
        if ($PortOwners.ContainsKey($Port)) {
            throw (
                "KIS_MCP_INSTANCE_PORT_DUPLICATE: $Name and " +
                "$($PortOwners[$Port]) both use $Port."
            )
        }
        $PortOwners[$Port] = $Name
    }

    foreach ($Name in $Expected.Keys) {
        $Record = $Remote.instances.PSObject.Properties[$Name].Value
        $Canonical = $Expected[$Name]
        if ([string]$Record.app_name -cne [string]$Canonical.app_name) {
            throw (
                "KIS_MCP_APP_IDENTITY_INVALID: $Name must map to " +
                "$($Canonical.app_name)."
            )
        }
        if ([int]$Record.port -ne [int]$Canonical.port) {
            throw (
                "KIS_MCP_INSTANCE_PORT_INVALID: $($Canonical.app_name) must use " +
                "127.0.0.1:$($Canonical.port)."
            )
        }
    }
}

function Assert-KisMcpTunnelClientExecutable {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Remote)

    if (-not (Test-Path -LiteralPath $Remote.tunnel_client_path -PathType Leaf)) {
        throw "KIS_MCP_TUNNEL_CLIENT_MISSING: $($Remote.tunnel_client_path)"
    }
    $ActualSha256 = (Get-FileHash -LiteralPath $Remote.tunnel_client_path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualSha256 -cne [string]$Remote.tunnel_client_sha256) {
        throw "KIS_MCP_TUNNEL_CLIENT_SHA256_MISMATCH: expected=$($Remote.tunnel_client_sha256); actual=$ActualSha256"
    }
    $VersionOutput = [string](& $Remote.tunnel_client_path --version 2>&1)
    if ($LASTEXITCODE -ne 0 -or $VersionOutput -notmatch '^([0-9]+\.[0-9]+\.[0-9]+)(?:\+|\s|$)') {
        throw 'KIS_MCP_TUNNEL_CLIENT_VERSION_UNREADABLE'
    }
    if ($Matches[1] -cne [string]$Remote.tunnel_client_version) {
        throw "KIS_MCP_TUNNEL_CLIENT_VERSION_MISMATCH: expected=$($Remote.tunnel_client_version); actual=$($Matches[1])"
    }
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
    Assert-KisMcpRemoteConfiguration -Remote $Remote

    if ([string]::IsNullOrWhiteSpace($Instance)) {
        $Instance = [string]$Remote.active_instance
    }
    $Instance = Resolve-KisMcpInstanceName -Instance $Instance

    $Property = $Remote.instances.PSObject.Properties[$Instance]
    if ($null -eq $Property) {
        throw "KIS_MCP_REMOTE_INSTANCE_MISSING: $Instance"
    }
    $Configured = [bool]$Property.Value.configured
    $TunnelId = [string]$Property.Value.tunnel_id
    $TunnelSecretRef = [string]$Property.Value.tunnel_secret_ref
    $ExpectedSecretRef = "secret://tunnel/$Instance/authentication-token"
    if ([string]::IsNullOrWhiteSpace($TunnelSecretRef)) {
        throw "KIS_MCP_TUNNEL_SECRET_REFERENCE_MISSING: $Instance"
    }
    if (-not [string]::Equals(
        $TunnelSecretRef,
        $ExpectedSecretRef,
        [StringComparison]::Ordinal
    )) {
        throw "KIS_MCP_TUNNEL_SECRET_REFERENCE_INVALID: $Instance"
    }
    if ($RequireConfigured -and -not $Configured) {
        throw (
            "KIS_MCP_REMOTE_INSTANCE_NOT_CONFIGURED: set settings.remote_mcp.instances.$Instance" +
            '.tunnel_id and .configured, then store the secret with ' +
            'scripts\set-tunnel-credential.ps1.'
        )
    }
    if (-not [string]::IsNullOrWhiteSpace($TunnelId) -and $TunnelId -notmatch '^tunnel_[0-9a-f]{32}$') {
        throw "KIS_MCP_TUNNEL_ID_INVALID: $Instance"
    }
    if ($Configured -and [string]::IsNullOrWhiteSpace($TunnelId)) {
        throw "KIS_MCP_TUNNEL_ID_MISSING: $Instance"
    }
    if (-not $Configured -and -not [string]::IsNullOrWhiteSpace($TunnelId)) {
        throw "KIS_MCP_REMOTE_INSTANCE_PARTIALLY_CONFIGURED: $Instance"
    }

    $StateRoot = [string]$Settings.paths.state_root
    $ProfileRoot = Join-Path $StateRoot 'tunnel-client\profiles'
    $RuntimeRoot = Join-Path $StateRoot ("tunnel-client\runtime\$Instance")
    $Endpoint = "http://$([string]$Remote.host):$([int]$Property.Value.port)$([string]$Remote.path)"

    return [pscustomobject]@{
        name = $Instance
        app_name = [string]$Property.Value.app_name
        host = [string]$Remote.host
        port = [int]$Property.Value.port
        path = [string]$Remote.path
        endpoint_url = $Endpoint
        profile_name = [string]$Property.Value.profile_name
        profile_root = $ProfileRoot
        runtime_root = $RuntimeRoot
        configured = $Configured
        tunnel_id = $TunnelId
        tunnel_secret_ref = $TunnelSecretRef
        tunnel_client_path = [string]$Remote.tunnel_client_path
        tunnel_client_version = [string]$Remote.tunnel_client_version
        tunnel_client_sha256 = [string]$Remote.tunnel_client_sha256
        python_environment_root = [string]$Settings.paths.python_environment_root
        state_root = $StateRoot
    }
}
