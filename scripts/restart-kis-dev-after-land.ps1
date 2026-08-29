param(
    [Parameter(Mandatory)][string]$ExpectedLandedSha,
    [Parameter(Mandatory)][string]$RepositoryRoot,
    [Parameter(Mandatory)][string]$StateRoot,
    [switch]$Worker,
    [ValidateRange(0, 300)][int]$DelaySeconds = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($ExpectedLandedSha -cnotmatch '^[0-9a-f]{40}$') {
    throw 'POST_LAND_RESTART_SHA_INVALID'
}

$RepositoryRoot = [System.IO.Path]::GetFullPath($RepositoryRoot)
$SettingsPath = Join-Path $RepositoryRoot 'settings\kis-mcp.settings.json'
$StateRoot = [System.IO.Path]::GetFullPath($StateRoot)
$ReceiptRoot = Join-Path $StateRoot 'runtime\kis-dev\state\post-land-restart'
$ReceiptPath = Join-Path $ReceiptRoot 'latest.json'
$ReceiptLockPath = Join-Path $ReceiptRoot 'latest.lock'

function Invoke-KisReceiptLock {
    param(
        [Parameter(Mandatory)][scriptblock]$Action
    )
    [System.IO.Directory]::CreateDirectory($ReceiptRoot) | Out-Null
    $Deadline = [DateTime]::UtcNow.AddSeconds(5)
    $Attempts = 0
    $MaxAttempts = 100
    $Stream = $null
    while ($null -eq $Stream) {
        try {
            $Stream = [System.IO.File]::Open(
                $ReceiptLockPath,
                [System.IO.FileMode]::OpenOrCreate,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
        }
        catch [System.IO.IOException] {
            $Attempts += 1
            if ($Attempts -ge $MaxAttempts -or [DateTime]::UtcNow -ge $Deadline) {
                throw
            }
            Start-Sleep -Milliseconds 50
        }
    }
    try {
        & $Action
    }
    finally {
        $Stream.Dispose()
    }
}

function Test-KisPrimaryGovernedDirty {
    param(
        [Parameter(Mandatory)][string[]]$StatusLines
    )
    foreach ($Line in $StatusLines) {
        if ([string]::IsNullOrWhiteSpace($Line)) {
            continue
        }
        if ($Line.StartsWith('?? .work/programmes/verification-review-evidence/', [StringComparison]::Ordinal)) {
            continue
        }
        return $true
    }
    return $false
}

function Move-KisAtomicFile {
    param(
        [Parameter(Mandatory)][string]$Temporary,
        [Parameter(Mandatory)][string]$Target
    )
    $Backup = "$Target.previous"
    if ([System.IO.File]::Exists($Target)) {
        try {
            [System.IO.File]::Replace($Temporary, $Target, $Backup)
            return
        }
        catch [System.IO.FileNotFoundException] { }
    }
    try {
        [System.IO.File]::Move($Temporary, $Target)
    }
    catch [System.IO.IOException] {
        if (-not [System.IO.File]::Exists($Target)) {
            throw
        }
        [System.IO.File]::Replace($Temporary, $Target, $Backup)
    }
}

function Write-KisDevRestartFallbackReceipt {
    param(
        [Parameter(Mandatory)][string]$State,
        [string]$Detail = '',
        [string]$ReceiptError = '',
        [string]$LaunchedSha = '',
        [int]$WorkerPid = 0
    )
    $Document = [ordered]@{
        schema_version = 1
        state = $State
        landed_sha = $ExpectedLandedSha
        launched_sha = $LaunchedSha
        worker_pid = $WorkerPid
        detail = $Detail
        receipt_error = $ReceiptError
        updated_utc = [DateTime]::UtcNow.ToString('o')
    }
    $Json = $Document | ConvertTo-Json -Depth 6
    $Targets = [System.Collections.Generic.List[string]]::new()
    try {
        $Targets.Add((Join-Path $ReceiptRoot 'fallback.json'))
    }
    catch { }
    $Targets.Add((Join-Path $RepositoryRoot '.temp\kis\post-land-restart-fallback.json'))
    foreach ($Target in $Targets) {
        try {
            [System.IO.Directory]::CreateDirectory((Split-Path -Parent $Target)) | Out-Null
            $Temporary = "$Target.next-$([Guid]::NewGuid().ToString('N'))"
            [System.IO.File]::WriteAllText(
                $Temporary,
                $Json,
                [System.Text.UTF8Encoding]::new($false)
            )
            Move-KisAtomicFile -Temporary $Temporary -Target $Target
            return
        }
        catch { }
    }
    [Console]::Error.WriteLine(($Document | ConvertTo-Json -Depth 6 -Compress))
}

function Write-KisDevRestartReceipt {
    param(
        [Parameter(Mandatory)][string]$State,
        [string]$Detail = '',
        [string]$LaunchedSha = '',
        [int]$WorkerPid = 0
    )
    try {
        $AcquireOwnership = $State -ceq 'scheduled'
        $Owned = Invoke-KisReceiptLock -Action {
            if (-not $AcquireOwnership -and [System.IO.File]::Exists($ReceiptPath)) {
                try {
                    $Current = Get-Content -LiteralPath $ReceiptPath -Raw | ConvertFrom-Json
                }
                catch {
                    return $false
                }
                $LandedProperty = $Current.PSObject.Properties['landed_sha']
                if ($null -eq $LandedProperty -or [string]$LandedProperty.Value -cne $ExpectedLandedSha) {
                    return $false
                }
                $CurrentWorkerPid = 0
                $WorkerProperty = $Current.PSObject.Properties['worker_pid']
                if ($null -ne $WorkerProperty -and $null -ne $WorkerProperty.Value) {
                    try {
                        $CurrentWorkerPid = [int]$WorkerProperty.Value
                    }
                    catch {
                        return $false
                    }
                }
                if (
                    $CurrentWorkerPid -gt 0 -and
                    $WorkerPid -gt 0 -and
                    $CurrentWorkerPid -ne $WorkerPid
                ) {
                    return $false
                }
            }

            $Document = [ordered]@{
                schema_version = 1
                state = $State
                landed_sha = $ExpectedLandedSha
                launched_sha = $LaunchedSha
                worker_pid = $WorkerPid
                detail = $Detail
                updated_utc = [DateTime]::UtcNow.ToString('o')
            }
            $Temporary = "$ReceiptPath.next-$([Guid]::NewGuid().ToString('N'))"
            [System.IO.File]::WriteAllText(
                $Temporary,
                ($Document | ConvertTo-Json -Depth 6),
                [System.Text.UTF8Encoding]::new($false)
            )
            Move-KisAtomicFile -Temporary $Temporary -Target $ReceiptPath
            return $true
        }
        return [bool]$Owned
    }
    catch {
        $ReceiptFailure = $_
        Write-KisDevRestartFallbackReceipt `
            -State $State `
            -Detail $Detail `
            -ReceiptError $ReceiptFailure.Exception.Message `
            -LaunchedSha $LaunchedSha `
            -WorkerPid $WorkerPid
        throw $ReceiptFailure
    }
}

if (-not $Worker) {
    $Pwsh = (Get-Command pwsh.exe -ErrorAction Stop).Source
    $CommandLine = (
        '"{0}" -NoProfile -WindowStyle Hidden -File "{1}" -ExpectedLandedSha "{2}" -RepositoryRoot "{3}" -StateRoot "{4}" -DelaySeconds "{5}" -Worker' -f
        $Pwsh, $PSCommandPath, $ExpectedLandedSha, $RepositoryRoot, $StateRoot, $DelaySeconds
    )
    $Created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $CommandLine
    }
    if ([int]$Created.ReturnValue -ne 0 -or [int]$Created.ProcessId -le 0) {
        throw "POST_LAND_RESTART_DETACH_FAILED: return=$($Created.ReturnValue)"
    }
    $null = Write-KisDevRestartReceipt -State 'scheduled' -WorkerPid ([int]$Created.ProcessId)
    [ordered]@{ state = 'scheduled'; pid = [int]$Created.ProcessId } |
        ConvertTo-Json -Compress |
        Write-Output
    return
}

if ($DelaySeconds -gt 0) {
    Start-Sleep -Seconds $DelaySeconds
}
$LaunchedSha = ''
$OwnsReceipt = Write-KisDevRestartReceipt -State 'synchronizing' -WorkerPid $PID
if (-not $OwnsReceipt) {
    return
}

try {
    $Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
    Set-Location -LiteralPath $RepositoryRoot
    $Branch = (& git symbolic-ref --quiet --short HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $Branch -cne 'main') {
        throw "POST_LAND_RESTART_PRIMARY_BRANCH_INVALID: observed=$Branch"
    }
    $Dirty = @(& git status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) {
        throw 'POST_LAND_RESTART_STATUS_FAILED'
    }
    if (Test-KisPrimaryGovernedDirty -StatusLines $Dirty) {
        throw 'POST_LAND_RESTART_PRIMARY_DIRTY'
    }

    $env:GH_CONFIG_DIR = [string]$Settings.github_cli.config_dir
    & gh auth status --active --hostname github.com *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'POST_LAND_RESTART_GITHUB_AUTH_UNAVAILABLE'
    }
    & git -c 'credential.https://github.com.helper=' `
        -c 'credential.https://github.com.helper=!gh auth git-credential' `
        fetch --no-tags --no-recurse-submodules --no-write-fetch-head `
        origin refs/heads/main:refs/remotes/origin/main
    if ($LASTEXITCODE -ne 0) {
        throw 'POST_LAND_RESTART_FETCH_FAILED'
    }

    $LocalSha = (& git rev-parse --verify HEAD).Trim().ToLowerInvariant()
    $RemoteSha = (& git rev-parse --verify refs/remotes/origin/main).Trim().ToLowerInvariant()
    if ($LASTEXITCODE -ne 0) {
        throw 'POST_LAND_RESTART_REF_RESOLUTION_FAILED'
    }
    & git merge-base --is-ancestor $LocalSha $RemoteSha
    if ($LASTEXITCODE -ne 0) {
        throw "POST_LAND_RESTART_NON_FAST_FORWARD: local=$LocalSha remote=$RemoteSha"
    }

    & git merge --ff-only refs/remotes/origin/main
    if ($LASTEXITCODE -ne 0) {
        throw 'POST_LAND_RESTART_FAST_FORWARD_FAILED'
    }
    $Head = (& git rev-parse --verify HEAD).Trim().ToLowerInvariant()
    if ($Head -cne $RemoteSha) {
        throw "POST_LAND_RESTART_SYNC_NOT_VERIFIED: head=$Head remote=$RemoteSha"
    }
    & git merge-base --is-ancestor $ExpectedLandedSha $Head
    if ($LASTEXITCODE -ne 0) {
        throw "POST_LAND_RESTART_LANDED_SHA_MISSING: landed=$ExpectedLandedSha head=$Head"
    }
    $LaunchedSha = $Head

    $OwnsReceipt = Write-KisDevRestartReceipt -State 'launching' -LaunchedSha $LaunchedSha -WorkerPid $PID
    if (-not $OwnsReceipt) {
        return
    }
    & (Join-Path $RepositoryRoot 'scripts\start-chatgpt.ps1') -Instance 'kis-dev'
    $null = Write-KisDevRestartReceipt -State 'stopped' -Detail 'replacement launcher exited' -LaunchedSha $LaunchedSha -WorkerPid $PID
}
catch {
    $OriginalFailure = $_
    try {
        $null = Write-KisDevRestartReceipt `
            -State 'failed' `
            -Detail $OriginalFailure.Exception.Message `
            -LaunchedSha $LaunchedSha `
            -WorkerPid $PID
    }
    catch {
        # Receipt persistence already emitted bounded fallback evidence. Preserve landing failure truth.
    }
    throw $OriginalFailure
}
