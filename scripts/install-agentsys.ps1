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

$OperationId = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$OperationQuarantine = Join-Path $QuarantineRoot $OperationId
New-Item -ItemType Directory -Path $OperationQuarantine -Force | Out-Null

foreach ($Existing in @($InstallRoot, $ManagedHome)) {
    if (Test-Path -LiteralPath $Existing) {
        $Name = Split-Path -Leaf $Existing
        Move-Item -LiteralPath $Existing -Destination (Join-Path $OperationQuarantine $Name)
    }
}

New-Item -ItemType Directory -Path $InstallRoot, $ManagedHome -Force | Out-Null
$env:HOME = $ManagedHome
$env:USERPROFILE = $ManagedHome
$env:APPDATA = Join-Path $ManagedHome 'AppData\Roaming'
$env:LOCALAPPDATA = Join-Path $ManagedHome 'AppData\Local'
$env:XDG_CONFIG_HOME = Join-Path $ManagedHome '.config'
$env:OPENCODE_CONFIG_DIR = Join-Path $ManagedHome '.config\opencode'
$env:CODEX_HOME = Join-Path $ManagedHome '.codex'
$env:CLAUDE_CONFIG_DIR = Join-Path $ManagedHome '.claude'
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
Write-Host "Installing $PackageSpec at $InstallRoot..."
& $Npm.Source install --prefix $InstallRoot $PackageSpec --save-exact --ignore-scripts --no-audit --no-fund
if ($LASTEXITCODE -ne 0) {
    throw "AGENTSYS_PACKAGE_INSTALL_FAILED: npm exited with code $LASTEXITCODE."
}

$PackageJsonPath = Join-Path $InstallRoot 'node_modules\agentsys\package.json'
$CliPath = Join-Path $InstallRoot 'node_modules\agentsys\bin\cli.js'
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

$PluginCache = Join-Path $ManagedHome '.agentsys\plugins'
$ClaudePlugins = Join-Path $ManagedHome '.claude\plugins'
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

$OpenCodeCommands = @(Get-ChildItem -LiteralPath (Join-Path $ManagedHome '.config\opencode\commands') -File -Filter '*.md' -ErrorAction SilentlyContinue)
$OpenCodeAgents = @(Get-ChildItem -LiteralPath (Join-Path $ManagedHome '.config\opencode\agents') -File -Filter '*.md' -ErrorAction SilentlyContinue)
$OpenCodeSkills = @(Get-ChildItem -LiteralPath (Join-Path $ManagedHome '.config\opencode\skills') -Directory -ErrorAction SilentlyContinue)
$CodexSkills = @(Get-ChildItem -LiteralPath (Join-Path $ManagedHome '.codex\skills') -Directory -ErrorAction SilentlyContinue)
$ClaudeInstalled = @(Get-ChildItem -LiteralPath $ClaudePlugins -Directory -ErrorAction SilentlyContinue)
if ($OpenCodeCommands.Count -eq 0 -or $CodexSkills.Count -eq 0 -or $ClaudeInstalled.Count -eq 0) {
    throw 'AGENTSYS_HOST_PROFILE_INCOMPLETE: one or more managed host profiles are empty.'
}

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
$StatusPath = Join-Path $ManagedHome 'installation.json'
$StatusJson = ($Status | ConvertTo-Json -Depth 8) + [Environment]::NewLine
[System.IO.File]::WriteAllText($StatusPath, $StatusJson, (New-Object System.Text.UTF8Encoding($false)))

$Status | ConvertTo-Json -Depth 8
