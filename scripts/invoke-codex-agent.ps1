[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$CodexExecutable = 'codex',

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$CodexHome
)

$ErrorActionPreference = 'Stop'

function Get-RepositoryStateFingerprint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepositoryPath,

        [Parameter(Mandatory = $true)]
        [string]$GitExecutable
    )

    $Head = @(& $GitExecutable -C $RepositoryPath rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0) {
        throw 'CODEX_CLI_GIT_HEAD_FAILED'
    }
    $Status = @(& $GitExecutable -C $RepositoryPath status --porcelain=v1 --untracked-files=all 2>$null)
    if ($LASTEXITCODE -ne 0) {
        throw 'CODEX_CLI_GIT_STATUS_FAILED'
    }
    $Diff = @(& $GitExecutable -C $RepositoryPath diff --no-ext-diff --binary HEAD -- 2>$null)
    if ($LASTEXITCODE -ne 0) {
        throw 'CODEX_CLI_GIT_DIFF_FAILED'
    }
    $Untracked = @(& $GitExecutable -C $RepositoryPath ls-files --others --exclude-standard 2>$null)
    if ($LASTEXITCODE -ne 0) {
        throw 'CODEX_CLI_GIT_UNTRACKED_FAILED'
    }

    $UntrackedHashes = foreach ($RelativePath in ($Untracked | Sort-Object)) {
        $FullPath = Join-Path $RepositoryPath $RelativePath
        if (Test-Path -LiteralPath $FullPath -PathType Leaf) {
            "${RelativePath}:$((Get-FileHash -LiteralPath $FullPath -Algorithm SHA256).Hash)"
        }
    }
    $Document = [ordered]@{
        head = @($Head)
        status = @($Status)
        diff = @($Diff)
        untracked = @($UntrackedHashes)
    } | ConvertTo-Json -Depth 4 -Compress
    $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Document)
    $Hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        return [Convert]::ToHexString($Hasher.ComputeHash($Bytes))
    }
    finally {
        $Hasher.Dispose()
    }
}

$ResolvedProject = (Resolve-Path -LiteralPath $ProjectPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $ResolvedProject '.git'))) {
    throw "CODEX_CLI_PROJECT_NOT_GIT_REPOSITORY: $ResolvedProject"
}
$ResolvedCodexHome = [System.IO.Path]::GetFullPath($CodexHome)
if (-not $ResolvedCodexHome.StartsWith('C:\Projects\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'CODEX_CLI_HOME_OUTSIDE_PROJECTS'
}
$Probe = $ResolvedCodexHome
while (-not [string]::IsNullOrWhiteSpace($Probe)) {
    if (Test-Path -LiteralPath $Probe) {
        $Item = Get-Item -LiteralPath $Probe -Force
        if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "CODEX_CLI_HOME_REPARSE_POINT: $Probe"
        }
    }
    if ($Probe -eq 'C:\Projects') { break }
    $Parent = Split-Path -Parent $Probe
    if ([string]::IsNullOrWhiteSpace($Parent) -or $Parent -eq $Probe) { break }
    $Probe = $Parent
}
[System.IO.Directory]::CreateDirectory($ResolvedCodexHome) | Out-Null

$Prompt = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($Prompt)) {
    throw 'CODEX_CLI_PROMPT_REQUIRED'
}

$ResolvedCodex = (Get-Command $CodexExecutable -ErrorAction Stop).Source
$Arguments = @(
    'exec',
    '--ephemeral',
    '--json',
    '--sandbox',
    'read-only',
    '--color',
    'never',
    '-C',
    $ProjectPath,
    '-'
)

$ResolvedGit = (Get-Command git -ErrorAction Stop).Source
$BeforeFingerprint = Get-RepositoryStateFingerprint `
    -RepositoryPath $ResolvedProject `
    -GitExecutable $ResolvedGit

$PreviousCodexHome = $env:CODEX_HOME
$PreviousApiKey = $env:OPENAI_API_KEY
$PreviousBaseUrl = $env:OPENAI_BASE_URL
$PreviousAccessToken = $env:CODEX_ACCESS_TOKEN
try {
    $env:CODEX_HOME = $ResolvedCodexHome
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:OPENAI_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:CODEX_ACCESS_TOKEN -ErrorAction SilentlyContinue
    $Output = @($Prompt | & $ResolvedCodex @Arguments)
    $CodexExitCode = $LASTEXITCODE
}
finally {
    $env:CODEX_HOME = $PreviousCodexHome
    $env:OPENAI_API_KEY = $PreviousApiKey
    $env:OPENAI_BASE_URL = $PreviousBaseUrl
    $env:CODEX_ACCESS_TOKEN = $PreviousAccessToken
}

$AfterFingerprint = Get-RepositoryStateFingerprint `
    -RepositoryPath $ResolvedProject `
    -GitExecutable $ResolvedGit
if ($AfterFingerprint -ne $BeforeFingerprint) {
    [Console]::Error.WriteLine('CODEX_CLI_MUTATION_DETECTED')
    exit 86
}

foreach ($Line in $Output) {
    [Console]::Out.WriteLine($Line)
}
exit $CodexExitCode
