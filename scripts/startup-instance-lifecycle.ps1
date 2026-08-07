Set-StrictMode -Version Latest

function Get-KisMcpNormalizedPath {
    param([Parameter(Mandatory)][string]$Path)

    try {
        return [System.IO.Path]::GetFullPath($Path).TrimEnd('\\')
    }
    catch {
        return $Path.Trim().Trim('"').TrimEnd('\\')
    }
}

function Test-KisMcpPathEqual {
    param(
        [Parameter(Mandatory)][string]$Left,
        [Parameter(Mandatory)][string]$Right
    )

    return [string]::Equals(
        (Get-KisMcpNormalizedPath $Left),
        (Get-KisMcpNormalizedPath $Right),
        [StringComparison]::OrdinalIgnoreCase
    )
}

function Test-KisMcpSelectedServerProcess {
    param(
        [Parameter(Mandatory)]$Process,
        [Parameter(Mandatory)][string]$PythonPath,
        [Parameter(Mandatory)][string]$Instance
    )

    $Executable = [string]$Process.ExecutablePath
    $CommandLine = [string]$Process.CommandLine
    if ([string]::IsNullOrWhiteSpace($Executable) -or [string]::IsNullOrWhiteSpace($CommandLine)) {
        return $false
    }
    if (-not (Test-KisMcpPathEqual $Executable $PythonPath)) {
        return $false
    }
    $Pattern = (
        '(?i)(^|\s)-m\s+kis_mcp\.secrets\.launcher\s+' +
        '--runtime\s+remote\s+--instance\s+' +
        [Regex]::Escape($Instance) + '(\s|$)'
    )
    return [Regex]::IsMatch($CommandLine, $Pattern)
}

function Test-KisMcpSelectedTunnelProcess {
    param(
        [Parameter(Mandatory)]$Process,
        [Parameter(Mandatory)][string]$TunnelPath,
        [Parameter(Mandatory)][string]$ProfileName,
        [Parameter(Mandatory)][string]$Endpoint
    )

    $Executable = [string]$Process.ExecutablePath
    $CommandLine = [string]$Process.CommandLine
    if ([string]::IsNullOrWhiteSpace($Executable) -or [string]::IsNullOrWhiteSpace($CommandLine)) {
        return $false
    }
    if (-not (Test-KisMcpPathEqual $Executable $TunnelPath)) {
        return $false
    }
    $ProfilePattern = '(?i)(^|\s)--profile\s+' + [Regex]::Escape($ProfileName) + '(\s|$)'
    $EndpointPattern = '(?i)(^|\s)--mcp\.server-url\s+' + [Regex]::Escape($Endpoint) + '(\s|$)'
    return (
        [Regex]::IsMatch($CommandLine, '(?i)(^|\s)run(\s|$)') -and
        [Regex]::IsMatch($CommandLine, $ProfilePattern) -and
        [Regex]::IsMatch($CommandLine, $EndpointPattern)
    )
}

function Get-KisMcpProcessSnapshot {
    return @(
        Get-CimInstance Win32_Process | Select-Object `
            ProcessId, ParentProcessId, Name, ExecutablePath, CommandLine, CreationDate
    )
}

function Get-KisMcpRootProcessIds {
    param([Parameter(Mandatory)][object[]]$Processes)

    $Ids = @{}
    foreach ($Process in $Processes) {
        $Ids[[int]$Process.ProcessId] = $true
    }
    return @(
        $Processes |
            Where-Object { -not $Ids.ContainsKey([int]$_.ParentProcessId) } |
            ForEach-Object { [int]$_.ProcessId }
    )
}

function Stop-KisMcpProcessTree {
    param(
        [Parameter(Mandatory)][int]$RootProcessId,
        [object[]]$ProcessSnapshot = $null
    )

    if ($RootProcessId -eq $PID) {
        throw 'KIS_MCP_PROCESS_OWNERSHIP_INVALID: refusing to terminate the startup process.'
    }
    $Processes = if ($null -eq $ProcessSnapshot) { Get-KisMcpProcessSnapshot } else { @($ProcessSnapshot) }
    $Children = @{}
    foreach ($Process in $Processes) {
        $Parent = [int]$Process.ParentProcessId
        if (-not $Children.ContainsKey($Parent)) {
            $Children[$Parent] = @()
        }
        $Children[$Parent] += [int]$Process.ProcessId
    }
    $Order = [System.Collections.Generic.List[int]]::new()
    function Add-Descendant([int]$ProcessId) {
        if ($Children.ContainsKey($ProcessId)) {
            foreach ($Child in @($Children[$ProcessId])) {
                Add-Descendant $Child
            }
        }
        $Order.Add($ProcessId)
    }
    Add-Descendant $RootProcessId
    foreach ($ProcessId in $Order) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Test-KisMcpDescendantOrSelf {
    param(
        [Parameter(Mandatory)][int]$ProcessId,
        [Parameter(Mandatory)][int]$RootProcessId,
        [Parameter(Mandatory)][object[]]$ProcessSnapshot
    )

    $ById = @{}
    foreach ($Process in $ProcessSnapshot) {
        $ById[[int]$Process.ProcessId] = $Process
    }
    $Current = $ProcessId
    $Seen = @{}
    while ($Current -gt 0 -and -not $Seen.ContainsKey($Current)) {
        if ($Current -eq $RootProcessId) {
            return $true
        }
        $Seen[$Current] = $true
        if (-not $ById.ContainsKey($Current)) {
            return $false
        }
        $Current = [int]$ById[$Current].ParentProcessId
    }
    return $false
}

function Assert-KisMcpCanonicalPython {
    param(
        [Parameter(Mandatory)]$Remote,
        [Parameter(Mandatory)][string]$PythonPath,
        [Parameter(Mandatory)][string]$RepositoryRoot
    )

    $Expected = Join-Path ([string]$Remote.python_environment_root) 'Scripts\python.exe'
    if (-not (Test-KisMcpPathEqual $PythonPath $Expected)) {
        throw "KIS_MCP_NONCANONICAL_PYTHON: expected=$Expected actual=$PythonPath"
    }
    $RepositoryPrefix = (Get-KisMcpNormalizedPath $RepositoryRoot) + '\\'
    if ((Get-KisMcpNormalizedPath $PythonPath).StartsWith($RepositoryPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "KIS_MCP_NONCANONICAL_PYTHON: repository-local Python is not permitted: $PythonPath"
    }
}

function Move-KisMcpRepositoryTransientsToQuarantine {
    param(
        [Parameter(Mandatory)]$Remote,
        [Parameter(Mandatory)][string]$RepositoryRoot
    )

    $Candidates = @('.venv', '.pytest_cache')
    $Existing = @($Candidates | ForEach-Object { Join-Path $RepositoryRoot $_ } | Where-Object { Test-Path -LiteralPath $_ })
    if ($Existing.Count -eq 0) {
        return @()
    }
    $OperationId = 'startup-transients-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $OperationRoot = Join-Path (Join-Path ([string]$Remote.state_root) 'quarantine') $OperationId
    [System.IO.Directory]::CreateDirectory($OperationRoot) | Out-Null
    $Records = @()
    foreach ($Source in $Existing) {
        $Name = Split-Path -Leaf $Source
        $Destination = Join-Path $OperationRoot $Name
        Move-Item -LiteralPath $Source -Destination $Destination
        $Records += [ordered]@{
            original_path = $Source
            quarantine_path = $Destination
            reason = 'noncanonical_repository_runtime_transient'
        }
    }
    $Metadata = [ordered]@{
        schema_version = 1
        operation_id = $OperationId
        instance = [string]$Remote.name
        created_utc = [DateTime]::UtcNow.ToString('o')
        items = $Records
    }
    [System.IO.File]::WriteAllText(
        (Join-Path $OperationRoot 'metadata.json'),
        ($Metadata | ConvertTo-Json -Depth 8),
        [System.Text.UTF8Encoding]::new($false)
    )
    return @($Records)
}

function Wait-KisMcpSelectedPortReleased {
    param(
        [Parameter(Mandatory)]$Remote,
        [int]$TimeoutSeconds = 10
    )

    $Deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $Deadline) {
        $Listener = Get-NetTCPConnection -LocalAddress $Remote.host -LocalPort $Remote.port -State Listen -ErrorAction SilentlyContinue
        if (-not $Listener) {
            return
        }
        Start-Sleep -Milliseconds 100
    }
    throw "KIS_MCP_STALE_PORT_NOT_RELEASED: app=$($Remote.app_name) instance=$($Remote.name) port=$($Remote.port)"
}

function Set-KisMcpCurrentInstanceRestarting {
    param([Parameter(Mandatory)]$Remote)

    $Path = Join-Path ([string]$Remote.runtime_root) 'current.json'
    $Document = [ordered]@{
        schema_version = 1
        lifecycle = 'restarting'
        instance = [string]$Remote.name
        app = [string]$Remote.app_name
        endpoint = [string]$Remote.endpoint_url
        restarting_utc = [DateTime]::UtcNow.ToString('o')
    }
    Write-KisMcpAtomicJson -Path $Path -Document $Document
}

function Set-KisMcpCurrentInstancePreflightFailed {
    param([Parameter(Mandatory)]$Remote)

    $Path = Join-Path ([string]$Remote.runtime_root) 'current.json'
    $Document = [ordered]@{
        schema_version = 1
        lifecycle = 'preflight_failed'
        instance = [string]$Remote.name
        app = [string]$Remote.app_name
        endpoint = [string]$Remote.endpoint_url
        failed_utc = [DateTime]::UtcNow.ToString('o')
    }
    Write-KisMcpAtomicJson -Path $Path -Document $Document
}

function Invoke-KisMcpSelectedInstancePreflight {
    param(
        [Parameter(Mandatory)]$Remote,
        [Parameter(Mandatory)][string]$PythonPath,
        [Parameter(Mandatory)][string]$RepositoryRoot
    )

    Assert-KisMcpCanonicalPython -Remote $Remote -PythonPath $PythonPath -RepositoryRoot $RepositoryRoot
    Set-KisMcpCurrentInstanceRestarting -Remote $Remote
    try {
        $TransientRecords = Move-KisMcpRepositoryTransientsToQuarantine `
            -Remote $Remote `
            -RepositoryRoot $RepositoryRoot
        $Processes = Get-KisMcpProcessSnapshot
        $ServerMatches = @(
            $Processes | Where-Object {
                Test-KisMcpSelectedServerProcess `
                    -Process $_ `
                    -PythonPath $PythonPath `
                    -Instance $Remote.name
            }
        )
        $TunnelMatches = @(
            $Processes | Where-Object {
                Test-KisMcpSelectedTunnelProcess `
                    -Process $_ `
                    -TunnelPath $Remote.tunnel_client_path `
                    -ProfileName $Remote.profile_name `
                    -Endpoint $Remote.endpoint_url
            }
        )
        $Listener = Get-NetTCPConnection `
            -LocalAddress $Remote.host `
            -LocalPort $Remote.port `
            -State Listen `
            -ErrorAction SilentlyContinue
        if ($Listener) {
            $ListenerPid = [int](@($Listener)[0].OwningProcess)
            $ListenerProcess = $Processes |
                Where-Object { [int]$_.ProcessId -eq $ListenerPid } |
                Select-Object -First 1
            if (
                $null -eq $ListenerProcess -or
                -not (Test-KisMcpSelectedServerProcess `
                    -Process $ListenerProcess `
                    -PythonPath $PythonPath `
                    -Instance $Remote.name)
            ) {
                $Name = if ($null -eq $ListenerProcess) { 'unknown' } else { [string]$ListenerProcess.Name }
                $Executable = if ($null -eq $ListenerProcess) { 'unknown' } else { [string]$ListenerProcess.ExecutablePath }
                throw "KIS_MCP_PORT_OWNED_BY_OTHER_PROCESS: app=$($Remote.app_name) instance=$($Remote.name) port=$($Remote.port) pid=$ListenerPid process=$Name executable=$Executable"
            }
        }
        foreach ($Root in @(Get-KisMcpRootProcessIds -Processes $TunnelMatches)) {
            Stop-KisMcpProcessTree -RootProcessId $Root -ProcessSnapshot $Processes
        }
        foreach ($Root in @(Get-KisMcpRootProcessIds -Processes $ServerMatches)) {
            Stop-KisMcpProcessTree -RootProcessId $Root -ProcessSnapshot $Processes
        }
        if ($ServerMatches.Count -gt 0 -or $Listener) {
            Wait-KisMcpSelectedPortReleased -Remote $Remote
        }
        return [pscustomobject]@{
            reclaimed_server_processes = $ServerMatches.Count
            reclaimed_tunnel_processes = $TunnelMatches.Count
            quarantined_transients = @($TransientRecords).Count
        }
    }
    catch {
        Set-KisMcpCurrentInstancePreflightFailed -Remote $Remote
        throw
    }
}

function Assert-KisMcpSelectedEndpointOwner {
    param(
        [Parameter(Mandatory)]$Remote,
        [Parameter(Mandatory)][string]$PythonPath,
        [Parameter(Mandatory)][int]$ServerProcessId,
        [Parameter(Mandatory)]$Listener
    )

    $Connections = @($Listener)
    if ($Connections.Count -ne 1) {
        throw "KIS_MCP_ENDPOINT_OWNER_INVALID: expected one listener for $($Remote.endpoint_url)."
    }
    $ListenerPid = [int]$Connections[0].OwningProcess
    $Processes = Get-KisMcpProcessSnapshot
    $ListenerProcess = $Processes | Where-Object { [int]$_.ProcessId -eq $ListenerPid } | Select-Object -First 1
    if ($null -eq $ListenerProcess -or -not (Test-KisMcpSelectedServerProcess -Process $ListenerProcess -PythonPath $PythonPath -Instance $Remote.name)) {
        throw "KIS_MCP_ENDPOINT_OWNER_INVALID: selected endpoint is not owned by $($Remote.app_name)."
    }
    if (-not (Test-KisMcpDescendantOrSelf -ProcessId $ListenerPid -RootProcessId $ServerProcessId -ProcessSnapshot $Processes)) {
        throw "KIS_MCP_ENDPOINT_OWNER_STALE: listener pid=$ListenerPid is not a descendant of server pid=$ServerProcessId."
    }
    return $ListenerPid
}

function Get-KisMcpCurrentStatePath {
    param([Parameter(Mandatory)][string]$RuntimeRoot)
    return Join-Path $RuntimeRoot 'current.json'
}

function Write-KisMcpAtomicJson {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)]$Document
    )

    [System.IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null
    $Temporary = "$Path.next-$([Guid]::NewGuid().ToString('N'))"
    [System.IO.File]::WriteAllText($Temporary, ($Document | ConvertTo-Json -Depth 10), [System.Text.UTF8Encoding]::new($false))
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        [System.IO.File]::Move($Temporary, $Path, $true)
    }
    else {
        [System.IO.File]::Move($Temporary, $Path)
    }
}

function Write-KisMcpCurrentInstanceState {
    param(
        [Parameter(Mandatory)]$Remote,
        [Parameter(Mandatory)][string]$RunId,
        [Parameter(Mandatory)][int]$LauncherPid,
        [Parameter(Mandatory)][int]$ServerPid,
        [Parameter(Mandatory)][int]$ServerListenerPid,
        [Parameter(Mandatory)][int]$TunnelPid,
        [Parameter(Mandatory)][string]$PythonPath,
        [Parameter(Mandatory)][string]$RepositoryRoot,
        [Parameter(Mandatory)][string]$StartupStatePath
    )

    $Document = [ordered]@{
        schema_version = 1
        lifecycle = 'ready'
        run_id = $RunId
        instance = [string]$Remote.name
        app = [string]$Remote.app_name
        endpoint = [string]$Remote.endpoint_url
        launcher_pid = $LauncherPid
        server_pid = $ServerPid
        server_listener_pid = $ServerListenerPid
        tunnel_pid = $TunnelPid
        python_executable = $PythonPath
        repository_root = $RepositoryRoot
        startup_state = $StartupStatePath
        started_utc = [DateTime]::UtcNow.ToString('o')
    }
    $Path = Get-KisMcpCurrentStatePath -RuntimeRoot $Remote.runtime_root
    Write-KisMcpAtomicJson -Path $Path -Document $Document
    return $Path
}

function Set-KisMcpCurrentInstanceStartupFailed {
    param(
        [Parameter(Mandatory)]$Remote,
        [Parameter(Mandatory)][string]$RunId
    )

    $Document = [ordered]@{
        schema_version = 1
        lifecycle = 'startup_failed'
        run_id = $RunId
        instance = [string]$Remote.name
        app = [string]$Remote.app_name
        endpoint = [string]$Remote.endpoint_url
        failed_utc = [DateTime]::UtcNow.ToString('o')
    }
    $Path = Get-KisMcpCurrentStatePath -RuntimeRoot $Remote.runtime_root
    Write-KisMcpAtomicJson -Path $Path -Document $Document
}

function Set-KisMcpCurrentInstanceStopped {
    param(
        [Parameter(Mandatory)]$Remote,
        [Parameter(Mandatory)][string]$RunId
    )

    $Path = Get-KisMcpCurrentStatePath -RuntimeRoot $Remote.runtime_root
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return
    }
    try {
        $Document = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable
    }
    catch {
        return
    }
    if ([string]$Document.run_id -cne $RunId) {
        return
    }
    $Document.lifecycle = 'stopped'
    $Document.stopped_utc = [DateTime]::UtcNow.ToString('o')
    Write-KisMcpAtomicJson -Path $Path -Document $Document
}
