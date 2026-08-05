param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$SettingsPath = Join-Path $RepositoryRoot 'settings\bootstrap\agentsys.install.json'
$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
$ProjectsRoot = [System.IO.Path]::GetFullPath('C:\Projects')

function Assert-InProjects([string]$Path, [string]$Name) {
    $Full = [System.IO.Path]::GetFullPath($Path)
    $Prefix = $ProjectsRoot.TrimEnd('\') + '\'
    if ($Full -ne $ProjectsRoot -and -not $Full.StartsWith($Prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "AGENTSYS_PATH_OUTSIDE_PROJECTS: $Name=$Full"
    }

    $Probe = $Full
    while (-not [string]::IsNullOrWhiteSpace($Probe)) {
        if (Test-Path -LiteralPath $Probe) {
            $Item = Get-Item -LiteralPath $Probe -Force
            if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "AGENTSYS_PATH_REPARSE_POINT: $Name traverses $Probe"
            }
        }
        if ($Probe -eq $ProjectsRoot) {
            break
        }
        $Parent = Split-Path -Parent $Probe
        if ([string]::IsNullOrWhiteSpace($Parent) -or $Parent -eq $Probe) {
            break
        }
        $Probe = $Parent
    }
    return $Full
}

if ([string]$Settings.package -ne 'agentsys' -or [string]$Settings.version -ne '6.0.1') {
    throw 'AGENTSYS_SETTINGS_INVALID: package and exact version must be agentsys@6.0.1.'
}
$Hosts = @($Settings.hosts | ForEach-Object { [string]$_ })
if (($Hosts -join ',') -ne 'claude,opencode,codex') {
    throw 'AGENTSYS_HOSTS_INVALID: expected claude, opencode, codex.'
}

$InstallRoot = Assert-InProjects ([string]$Settings.install_root) 'install_root'
$ManagedHome = Assert-InProjects ([string]$Settings.managed_home) 'managed_home'
$CacheRoot = Assert-InProjects ([string]$Settings.npm_cache_root) 'npm_cache_root'
$TempRoot = Assert-InProjects ([string]$Settings.temp_root) 'temp_root'
$QuarantineRoot = Assert-InProjects ([string]$Settings.quarantine_root) 'quarantine_root'

$Node = Get-Command 'node.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
$Npm = Get-Command 'npm.cmd' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
$Git = Get-Command 'git.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $Node -or $null -eq $Npm -or $null -eq $Git) {
    throw 'AGENTSYS_PREREQUISITE_MISSING: node.exe, npm.cmd, and git.exe are required.'
}
$NodeVersion = (& $Node.Source --version).Trim()
if ($LASTEXITCODE -ne 0 -or $NodeVersion -notmatch '^v(?<major>\d+)\.' -or [int]$Matches.major -lt 18) {
    throw "AGENTSYS_NODE_UNSUPPORTED: found $NodeVersion; Node.js 18 or newer is required."
}

foreach ($Path in @($CacheRoot, $TempRoot, $QuarantineRoot, (Split-Path -Parent $InstallRoot), (Split-Path -Parent $ManagedHome))) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$StageId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$StagingInstallRoot = Assert-InProjects (Join-Path $TempRoot "agentsys-package-$StageId") 'staging_install_root'
$StagingManagedHome = Assert-InProjects (Join-Path $TempRoot "agentsys-home-$StageId") 'staging_managed_home'
New-Item -ItemType Directory -Path $StagingInstallRoot, $StagingManagedHome -Force | Out-Null

$env:HOME = $StagingManagedHome
$env:USERPROFILE = $StagingManagedHome
$env:APPDATA = Join-Path $StagingManagedHome 'AppData\Roaming'
$env:LOCALAPPDATA = Join-Path $StagingManagedHome 'AppData\Local'
$env:XDG_CONFIG_HOME = Join-Path $StagingManagedHome '.config'
$env:OPENCODE_CONFIG_DIR = Join-Path $StagingManagedHome '.config\opencode'
$env:CODEX_HOME = Join-Path $StagingManagedHome '.codex'
$env:CLAUDE_CONFIG_DIR = Join-Path $StagingManagedHome '.claude'
$env:AGENTSYS_STRIP_MODELS = if ([bool]$Settings.opencode_strip_models) { 'true' } else { 'false' }
$env:NPM_CONFIG_CACHE = $CacheRoot
$env:NPM_CONFIG_AUDIT = 'false'
$env:NPM_CONFIG_FUND = 'false'
$env:NPM_CONFIG_UPDATE_NOTIFIER = 'false'
$env:TEMP = $TempRoot
$env:TMP = $TempRoot

foreach ($Path in @($env:APPDATA, $env:LOCALAPPDATA, $env:XDG_CONFIG_HOME, $env:OPENCODE_CONFIG_DIR, $env:CODEX_HOME, $env:CLAUDE_CONFIG_DIR)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$PackageSpec = "$($Settings.package)@$($Settings.version)"
Write-Host "Staging $PackageSpec at $StagingInstallRoot..."
& $Npm.Source install --prefix $StagingInstallRoot $PackageSpec --save-exact --ignore-scripts --no-audit --no-fund
if ($LASTEXITCODE -ne 0) {
    throw "AGENTSYS_PACKAGE_INSTALL_FAILED: npm exited with code $LASTEXITCODE."
}

$PackageJsonPath = Join-Path $StagingInstallRoot 'node_modules\agentsys\package.json'
$CliPath = Join-Path $StagingInstallRoot 'node_modules\agentsys\bin\cli.js'
if (-not (Test-Path -LiteralPath $PackageJsonPath -PathType Leaf) -or -not (Test-Path -LiteralPath $CliPath -PathType Leaf)) {
    throw 'AGENTSYS_PACKAGE_INVALID: package metadata or CLI entrypoint is missing.'
}
$PackageJson = Get-Content -LiteralPath $PackageJsonPath -Raw | ConvertFrom-Json
if ([string]$PackageJson.name -ne 'agentsys' -or [string]$PackageJson.version -ne '6.0.1') {
    throw "AGENTSYS_IDENTITY_MISMATCH: installed $($PackageJson.name)@$($PackageJson.version)."
}

Write-Host 'Fetching the complete plugin catalogue and configuring OpenCode and Codex...'
& $Node.Source $CliPath --tools opencode,codex
if ($LASTEXITCODE -ne 0) {
    throw "AGENTSYS_PROFILE_INSTALL_FAILED: CLI exited with code $LASTEXITCODE."
}

$PluginCache = Join-Path $StagingManagedHome '.agentsys\plugins'
$ClaudePlugins = Join-Path $StagingManagedHome '.claude\plugins'
New-Item -ItemType Directory -Path $ClaudePlugins -Force | Out-Null
$PluginDirectories = @(Get-ChildItem -LiteralPath $PluginCache -Directory | Where-Object {
    Test-Path -LiteralPath (Join-Path $_.FullName '.claude-plugin\plugin.json')
})
if ($PluginDirectories.Count -eq 0) {
    throw 'AGENTSYS_PLUGIN_CACHE_EMPTY: no complete plugin directories were fetched.'
}
foreach ($Plugin in $PluginDirectories) {
    $Destination = Join-Path $ClaudePlugins ($Plugin.Name + '@agentsys')
    if (Test-Path -LiteralPath $Destination) {
        throw "AGENTSYS_CLAUDE_DESTINATION_EXISTS: $Destination"
    }
    Copy-Item -LiteralPath $Plugin.FullName -Destination $Destination -Recurse
}

$ReferencePairs = @(
    @($StagingManagedHome, $ManagedHome),
    @($StagingInstallRoot, $InstallRoot)
)
$Utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$RemainingStagingReferences = 0
foreach ($File in Get-ChildItem -LiteralPath $StagingManagedHome -Recurse -File) {
    $Bytes = [System.IO.File]::ReadAllBytes($File.FullName)
    if ([Array]::IndexOf($Bytes, [byte]0) -ge 0) {
        continue
    }
    try { $Text = $Utf8Strict.GetString($Bytes) }
    catch { continue }
    $Updated = $Text
    foreach ($Pair in $ReferencePairs) {
        $Source = [string]$Pair[0]
        $Target = [string]$Pair[1]
        $Updated = $Updated.Replace($Source.Replace('\', '\\'), $Target.Replace('\', '\\'))
        $Updated = $Updated.Replace($Source, $Target)
    }
    if ($Updated -ne $Text) {
        [System.IO.File]::WriteAllText($File.FullName, $Updated, $Utf8NoBom)
    }
    foreach ($Pair in $ReferencePairs) {
        $Source = [string]$Pair[0]
        if ($Updated.Contains($Source) -or $Updated.Contains($Source.Replace('\', '\\'))) {
            $RemainingStagingReferences++
        }
    }
}
if ($RemainingStagingReferences -gt 0) {
    throw "AGENTSYS_PROFILE_RELOCATION_FAILED: $RemainingStagingReferences staged path references remain."
}

$OpenCodeCommands = @(Get-ChildItem -LiteralPath (Join-Path $StagingManagedHome '.config\opencode\commands') -File -Filter '*.md' -ErrorAction SilentlyContinue)
$OpenCodeAgents = @(Get-ChildItem -LiteralPath (Join-Path $StagingManagedHome '.config\opencode\agents') -File -Filter '*.md' -ErrorAction SilentlyContinue)
$OpenCodeSkills = @(Get-ChildItem -LiteralPath (Join-Path $StagingManagedHome '.config\opencode\skills') -Directory -ErrorAction SilentlyContinue)
$CodexSkills = @(Get-ChildItem -LiteralPath (Join-Path $StagingManagedHome '.codex\skills') -Directory -ErrorAction SilentlyContinue)
$ClaudeInstalled = @(Get-ChildItem -LiteralPath $ClaudePlugins -Directory -ErrorAction SilentlyContinue)
if ($OpenCodeCommands.Count -eq 0 -or $CodexSkills.Count -eq 0 -or $ClaudeInstalled.Count -eq 0) {
    throw 'AGENTSYS_HOST_PROFILE_INCOMPLETE: one or more managed host profiles are empty.'
}

$ConfiguredCommands = @($Settings.kis_mcp_command_policy.available_commands | ForEach-Object { [string]$_ })
$ExpectedCommands = @($ConfiguredCommands | Sort-Object)
$OpenCodeCommandNames = @($OpenCodeCommands | ForEach-Object { $_.BaseName } | Sort-Object)
$CodexSkillNames = @($CodexSkills | ForEach-Object { $_.Name } | Sort-Object)
if (@($ConfiguredCommands | Sort-Object -Unique).Count -ne $ConfiguredCommands.Count -or
    ($OpenCodeCommandNames -join "`n") -ne ($ExpectedCommands -join "`n") -or
    ($CodexSkillNames -join "`n") -ne ($ExpectedCommands -join "`n")) {
    throw 'AGENTSYS_COMMAND_CATALOGUE_MISMATCH: generated OpenCode commands and Codex skills must exactly match the configured command catalogue.'
}

$OperationId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$OperationQuarantine = Join-Path $QuarantineRoot $OperationId
New-Item -ItemType Directory -Path $OperationQuarantine -Force | Out-Null

$Status = [ordered]@{
    schema_version = 1
    tool_id = 'agentsys'
    version = [string]$PackageJson.version
    installed_at = [DateTimeOffset]::UtcNow.ToString('o')
    install_root = $InstallRoot
    managed_home = $ManagedHome
    hosts = [ordered]@{
        claude = [ordered]@{ configured = $true; plugins = $ClaudeInstalled.Count }
        opencode = [ordered]@{ configured = $true; commands = $OpenCodeCommands.Count; agents = $OpenCodeAgents.Count; skills = $OpenCodeSkills.Count }
        codex = [ordered]@{ configured = $true; skills = $CodexSkills.Count }
    }
    kis_mcp_command_policy = $Settings.kis_mcp_command_policy
    previous_state_quarantine = $OperationQuarantine
}
$StatusPath = Join-Path $StagingManagedHome 'installation.json'
$StatusJson = ($Status | ConvertTo-Json -Depth 8) + [Environment]::NewLine
[System.IO.File]::WriteAllText($StatusPath, $StatusJson, (New-Object System.Text.UTF8Encoding($false)))

$PreviousInstall = $null
$PreviousHome = $null
$InstallActivated = $false
$HomeActivated = $false
try {
    if (Test-Path -LiteralPath $InstallRoot) {
        $PreviousInstallDestination = Join-Path $OperationQuarantine 'previous-package'
        Move-Item -LiteralPath $InstallRoot -Destination $PreviousInstallDestination
        $PreviousInstall = $PreviousInstallDestination
    }
    if (Test-Path -LiteralPath $ManagedHome) {
        $PreviousHomeDestination = Join-Path $OperationQuarantine 'previous-home'
        Move-Item -LiteralPath $ManagedHome -Destination $PreviousHomeDestination
        $PreviousHome = $PreviousHomeDestination
    }
    Move-Item -LiteralPath $StagingInstallRoot -Destination $InstallRoot
    $InstallActivated = $true
    Move-Item -LiteralPath $StagingManagedHome -Destination $ManagedHome
    $HomeActivated = $true
}
catch {
    $ActivationMessage = $_.Exception.Message
    $RollbackErrors = @()
    if ($HomeActivated -and (Test-Path -LiteralPath $ManagedHome)) {
        try { Move-Item -LiteralPath $ManagedHome -Destination (Join-Path $OperationQuarantine 'failed-new-home') }
        catch { $RollbackErrors += "new home: $($_.Exception.Message)" }
    }
    if ($InstallActivated -and (Test-Path -LiteralPath $InstallRoot)) {
        try { Move-Item -LiteralPath $InstallRoot -Destination (Join-Path $OperationQuarantine 'failed-new-package') }
        catch { $RollbackErrors += "new package: $($_.Exception.Message)" }
    }
    if ($null -ne $PreviousHome -and -not (Test-Path -LiteralPath $ManagedHome)) {
        try { Move-Item -LiteralPath $PreviousHome -Destination $ManagedHome }
        catch { $RollbackErrors += "previous home: $($_.Exception.Message)" }
    }
    if ($null -ne $PreviousInstall -and -not (Test-Path -LiteralPath $InstallRoot)) {
        try { Move-Item -LiteralPath $PreviousInstall -Destination $InstallRoot }
        catch { $RollbackErrors += "previous package: $($_.Exception.Message)" }
    }
    $RollbackDetail = if ($RollbackErrors.Count -gt 0) { '; rollback errors: ' + ($RollbackErrors -join ' | ') } else { '' }
    throw "AGENTSYS_ACTIVATION_FAILED: $ActivationMessage$RollbackDetail"
}

$Status | ConvertTo-Json -Depth 8
